"""Command line entry point: tg-music-dl CHANNEL [CHANNEL ...]."""
import argparse
import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient, utils

from tg_music_dl import __version__
from tg_music_dl.downloader import download_channel
from tg_music_dl.media import AUDIO, MEDIA_TYPES
from tg_music_dl.proxy import parse_proxy
from tg_music_dl.state import STATE_FILE_NAME, DownloadState

API_ID_VARIABLE = "TELEGRAM_API_ID"
API_HASH_VARIABLE = "TELEGRAM_API_HASH"
PROXY_VARIABLE = "TG_MUSIC_DL_PROXY"
DEFAULT_LIMIT = 20
DEFAULT_OUTPUT = "music"
# The session file holds the logged-in account, so it lives in the user's
# config folder rather than wherever the command happens to run.
DEFAULT_SESSION = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "tg-music-dl" / "session")
USAGE_ERROR = 2
INTERRUPTED = 130


class ConfigError(Exception):
    """A setting the user has to fix before anything can be downloaded."""


def read_credentials(environment):
    """Returns (api_id, api_hash) from the environment, or raises ConfigError naming what is missing."""
    api_id = environment.get(API_ID_VARIABLE, "").strip()
    api_hash = environment.get(API_HASH_VARIABLE, "").strip()
    missing = [name for name, value in ((API_ID_VARIABLE, api_id), (API_HASH_VARIABLE, api_hash))
               if not value]
    if missing:
        raise ConfigError(
            f"set {' and '.join(missing)} (get them at https://my.telegram.org, API development tools)")
    if not api_id.isdigit():
        raise ConfigError(f"{API_ID_VARIABLE} must be a number")
    return int(api_id), api_hash


def proxy_setting(flag_value, environment):
    """Returns the proxy URL to use: the --proxy flag first, then $TG_MUSIC_DL_PROXY."""
    return flag_value or environment.get(PROXY_VARIABLE) or None


def parse_types(value):
    """Parses a comma-separated list of media types for argparse."""
    types = {item.strip() for item in value.split(",") if item.strip()}
    if not types or not types <= set(MEDIA_TYPES):
        raise argparse.ArgumentTypeError(f"choose from {', '.join(MEDIA_TYPES)}")
    return types


def positive_int(value):
    """Parses a whole number of at least 1 for argparse."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="tg-music-dl",
        description="Download music from Telegram channels. Each run fetches the newest"
                    " files that were not downloaded yet.")
    parser.add_argument("channels", nargs="+", metavar="CHANNEL",
                        help="channel username, @username or t.me link")
    parser.add_argument("-n", "--limit", type=positive_int, default=DEFAULT_LIMIT,
                        help="most new files per channel per run (default: %(default)s)")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="folder to save into (default: %(default)s)")
    parser.add_argument("-t", "--types", type=parse_types, default={AUDIO},
                        help=f"comma-separated media types: {', '.join(MEDIA_TYPES)} (default: {AUDIO})")
    parser.add_argument("--proxy",
                        help="socks5://host:port, socks4://host:port or http://host:port"
                             f" (default: ${PROXY_VARIABLE}, otherwise a direct connection)")
    parser.add_argument("--session", default=str(DEFAULT_SESSION),
                        help="Telegram session file, which holds your login (default: %(default)s)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


async def download_all(args, api_id, api_hash, proxy):
    """Downloads from every channel in turn and returns how many channels could not be found."""
    os.makedirs(args.output, exist_ok=True)
    session_folder = os.path.dirname(args.session)
    if session_folder:
        os.makedirs(session_folder, mode=0o700, exist_ok=True)
    state = DownloadState(os.path.join(args.output, STATE_FILE_NAME))
    failures = 0
    client = TelegramClient(args.session, api_id, api_hash, proxy=proxy)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            # Logging in asks for a phone number and a code, which needs a person
            # at a terminal; without one (cron, launchd) Telethon would crash on
            # the prompt instead.
            if not sys.stdin.isatty():
                raise ConfigError("not logged in; run tg-music-dl once in a terminal to log in")
            await client.start()
        for channel in args.channels:
            try:
                entity = await client.get_entity(channel)
            except ValueError as error:
                print(f"Skipping {channel}: {error}", file=sys.stderr)
                failures += 1
                continue
            title = utils.get_display_name(entity) or channel
            print(f"== {title}")
            count = await download_channel(client, entity, str(utils.get_peer_id(entity)), args.output,
                                           args.limit, args.types, state)
            print(f"{count} new {'file' if count == 1 else 'files'} from {title}.")
    finally:
        await client.disconnect()
    return failures


def main(argv=None):
    """Runs the command and returns its exit status."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        api_id, api_hash = read_credentials(os.environ)
        proxy = parse_proxy(proxy_setting(args.proxy, os.environ))
    except (ConfigError, ValueError) as error:
        print(f"tg-music-dl: {error}", file=sys.stderr)
        return USAGE_ERROR
    try:
        failures = asyncio.run(download_all(args, api_id, api_hash, proxy))
    except ConfigError as error:
        print(f"tg-music-dl: {error}", file=sys.stderr)
        return USAGE_ERROR
    except KeyboardInterrupt:
        print("\nStopped. Finished files are kept; the next run picks up from here.", file=sys.stderr)
        return INTERRUPTED
    return 1 if failures else 0
