# tg-music-dl

Download music from Telegram channels from the command line. Each run fetches the newest
files you don't have yet and remembers what it downloaded, so the next run picks up where
the last one stopped.

## Install

Needs Python 3.10 or newer.

    pipx install git+https://github.com/ArefMozafari/tg-music-dl.git

Or, from a clone of this repository:

    pipx install .

## Set up

1. Get an API ID and hash at https://my.telegram.org, under *API development tools*.
2. Put them in your environment, for example in `~/.zshenv`:

       export TELEGRAM_API_ID=...
       export TELEGRAM_API_HASH=...

3. Run `tg-music-dl` once in a terminal. It asks for your phone number, the code Telegram
   sends you, and your two-step password if you have one. The login is saved in
   `~/.config/tg-music-dl/session` (or under `$XDG_CONFIG_HOME`), so it asks only once.
   That file gives full access to your account: keep it private.

## Use

    tg-music-dl some_channel
    tg-music-dl @first_channel https://t.me/second_channel --limit 50 --output ~/Music/Telegram
    tg-music-dl some_channel --types audio,voice
    tg-music-dl some_channel --proxy socks5://127.0.0.1:1080

| Option | Meaning |
|---|---|
| `CHANNEL ...` | One or more channels, as a username, `@username` or `t.me` link |
| `-n`, `--limit` | Most new files per channel per run (default 20) |
| `-o`, `--output` | Folder to save into (default `music`) |
| `-t`, `--types` | Comma-separated media types: `audio`, `voice`, `video` (default `audio`) |
| `--proxy` | `socks5://host:port`, `socks4://host:port` or `http://host:port`. Falls back to `$TG_MUSIC_DL_PROXY`, then to a direct connection |
| `--session` | Session file holding your login (default `~/.config/tg-music-dl/session`) |

Media types:

- `audio`: music files, including audio a channel posted as a plain document.
- `voice`: voice notes.
- `video`: videos. Round video messages and GIFs are left out.

## How resuming works

- `.tg-music-dl.json` in the output folder records which messages were downloaded, per
  channel. It is saved after every file, so stopping with Ctrl+C loses nothing finished.
- A file already in the output folder with the same name and size counts as downloaded
  and is not fetched again. A different file with the same name is saved beside it as
  `name (1).ext`.
- Each file is written as `name.ext.part` and renamed once complete. An interrupted file
  is downloaded again on the next run.

## Running without a terminal

From cron or launchd, `tg-music-dl` cannot ask for a login. If the session is missing or
was logged out, it exits with status 2 and says so, instead of waiting for input.

Exit status: `0` done, `1` a channel could not be found (the others are still downloaded),
`2` a setup problem (credentials, proxy or login), `130` stopped with Ctrl+C.

## Development

    python3 -m venv .venv
    .venv/bin/python -m pip install -e ".[test]"
    .venv/bin/python -m pytest

## License

MIT — see [LICENSE](LICENSE).
