"""Command line entry point: tg-music-dl CHANNEL [CHANNEL ...]."""
import argparse
import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient, utils

from tg_music_dl import __version__
from tg_music_dl.proxy import parse_proxy

API_ID_VARIABLE = "TELEGRAM_API_ID"
API_HASH_VARIABLE = "TELEGRAM_API_HASH"
PROXY_VARIABLE = "TG_MUSIC_DL_PROXY"
DEFAULT_LIMIT = 20
DEFAULT_OUTPUT = "music"
# The session file holds the logged-in account, so it lives in the user's
# config folder rather than wherever the command happens to run.
DEFAULT_SESSION = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "tg-music-dl" / "session")
# Lists what was already downloaded into the output folder, one entry per line.
DOWNLOADED_LIST_NAME = "downloaded.txt"
AUDIO_MIME_PREFIX = "audio/"
BYTES_PER_MEGABYTE = 1024 * 1024
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
    parser.add_argument("--proxy",
                        help="socks5://host:port, socks4://host:port or http://host:port"
                             f" (default: ${PROXY_VARIABLE}, otherwise a direct connection)")
    parser.add_argument("--session", default=str(DEFAULT_SESSION),
                        help="Telegram session file, which holds your login (default: %(default)s)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def print_progress(received, total):
    """Prints download progress in place: percentage and size when the total is known."""
    received_megabytes = received / BYTES_PER_MEGABYTE
    if total:
        total_megabytes = total / BYTES_PER_MEGABYTE
        print(f"\r  {100 * received / total:.1f}% ({received_megabytes:.2f} / {total_megabytes:.2f} MB)",
              end="", flush=True)
    else:
        print(f"\r  {received_megabytes:.2f} MB", end="", flush=True)


def audio_media(message):
    """Returns the message's audio file, including audio sent as a plain document, or None."""
    if message.audio:
        return message.audio
    document = message.document
    if document is not None and (getattr(document, "mime_type", None) or "").startswith(AUDIO_MIME_PREFIX):
        return document
    return None


async def download_channel(client, entity, output, limit, downloaded_files):
    """Downloads up to `limit` new audio files from one channel, newest first.

    Adds each finished file's key to `downloaded_files` and returns how many
    files were downloaded.
    """
    downloaded_count = 0
    async for message in client.iter_messages(entity):
        if downloaded_count >= limit:
            break
        media = audio_media(message)
        # Skips anything that is not audio, such as photos, videos and other files.
        if not media:
            continue
        file_name = getattr(media, "file_name", None) or getattr(media, "name", None)
        if not file_name:
            file_name = f"{message.id}.ogg"
        if file_name in downloaded_files:
            print("Already downloaded:", file_name)
            continue
        print("Downloading:", file_name)
        await client.download_media(message, output, progress_callback=print_progress)
        # Ends the progress line.
        print()
        downloaded_files.add(file_name)
        downloaded_count += 1
    return downloaded_count


async def download_all(args, api_id, api_hash, proxy):
    """Downloads from every channel in turn and returns how many channels could not be found."""
    os.makedirs(args.output, exist_ok=True)
    session_folder = os.path.dirname(args.session)
    if session_folder:
        os.makedirs(session_folder, mode=0o700, exist_ok=True)
    downloaded_list = os.path.join(args.output, DOWNLOADED_LIST_NAME)
    downloaded_files = set()
    if os.path.exists(downloaded_list):
        with open(downloaded_list) as list_file:
            downloaded_files = set(list_file.read().splitlines())
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
        try:
            for channel in args.channels:
                try:
                    entity = await client.get_entity(channel)
                except ValueError as error:
                    print(f"Skipping {channel}: {error}", file=sys.stderr)
                    failures += 1
                    continue
                title = utils.get_display_name(entity) or channel
                print(f"== {title}")
                count = await download_channel(client, entity, args.output, args.limit, downloaded_files)
                print(f"{count} new {'file' if count == 1 else 'files'} from {title}.")
        finally:
            # Saved even when a run is interrupted, so finished files are not fetched again.
            with open(downloaded_list, "w") as list_file:
                for file_name in sorted(downloaded_files):
                    list_file.write(file_name + "\n")
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
        print("\nStopped.", file=sys.stderr)
        return INTERRUPTED
    return 1 if failures else 0
