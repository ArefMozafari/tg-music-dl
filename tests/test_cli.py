"""Tests for src/tg_music_dl/cli.py."""
import argparse

import pytest

from tg_music_dl import cli

CREDENTIALS = {"TELEGRAM_API_ID": "12345", "TELEGRAM_API_HASH": "not-a-real-api-hash"}


def set_environment(monkeypatch, variables):
    for name in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TG_MUSIC_DL_PROXY"):
        monkeypatch.delenv(name, raising=False)
    for name, value in variables.items():
        monkeypatch.setenv(name, value)


class TestReadCredentials:
    def test_should_return_the_id_as_a_number_and_the_hash(self):
        assert cli.read_credentials(CREDENTIALS) == (12345, "not-a-real-api-hash")

    def test_should_name_every_missing_variable(self):
        with pytest.raises(cli.ConfigError, match="TELEGRAM_API_ID and TELEGRAM_API_HASH"):
            cli.read_credentials({})

    def test_should_reject_an_id_that_is_not_a_number(self):
        environment = {**CREDENTIALS, "TELEGRAM_API_ID": "abc"}

        with pytest.raises(cli.ConfigError, match="must be a number"):
            cli.read_credentials(environment)


class TestProxySetting:
    def test_should_prefer_the_flag_over_the_environment(self):
        environment = {"TG_MUSIC_DL_PROXY": "socks5://127.0.0.1:1"}

        assert cli.proxy_setting("socks5://127.0.0.1:2", environment) == "socks5://127.0.0.1:2"

    def test_should_fall_back_to_the_environment(self):
        environment = {"TG_MUSIC_DL_PROXY": "socks5://127.0.0.1:1"}

        assert cli.proxy_setting(None, environment) == "socks5://127.0.0.1:1"

    def test_should_return_none_when_neither_is_set(self):
        assert cli.proxy_setting(None, {}) is None


class TestParseTypes:
    def test_should_split_a_comma_separated_list(self):
        assert cli.parse_types("audio, voice") == {"audio", "voice"}

    def test_should_reject_an_unknown_type(self):
        with pytest.raises(argparse.ArgumentTypeError, match="audio, voice, video"):
            cli.parse_types("audio,photo")

    def test_should_reject_an_empty_list(self):
        with pytest.raises(argparse.ArgumentTypeError):
            cli.parse_types(" , ")


class TestParseArgs:
    def test_should_use_the_defaults(self):
        args = cli.parse_args(["some_channel"])

        assert args.channels == ["some_channel"]
        assert args.limit == 20
        assert args.output == "music"
        assert args.types == {"audio"}
        assert args.proxy is None
        assert args.session == str(cli.DEFAULT_SESSION)

    def test_should_accept_media_types(self):
        args = cli.parse_args(["some_channel", "--types", "audio,video"])

        assert args.types == {"audio", "video"}

    def test_should_accept_several_channels_and_options(self):
        args = cli.parse_args([
            "first_channel", "@second_channel", "--limit", "5", "--output", "songs",
            "--proxy", "socks5://127.0.0.1:1080", "--session", "my.session",
        ])

        assert args.channels == ["first_channel", "@second_channel"]
        assert args.limit == 5
        assert args.output == "songs"
        assert args.proxy == "socks5://127.0.0.1:1080"
        assert args.session == "my.session"

    def test_should_reject_a_limit_below_one(self):
        with pytest.raises(SystemExit):
            cli.parse_args(["some_channel", "--limit", "0"])

    def test_should_require_a_channel(self):
        with pytest.raises(SystemExit):
            cli.parse_args([])


class LoggedOutClient:
    """Stands in for TelegramClient with a session that is not logged in."""

    def __init__(self, *args, **kwargs):
        self.started = False

    async def connect(self):
        pass

    async def is_user_authorized(self):
        return False

    async def start(self):
        self.started = True

    async def disconnect(self):
        pass


class TestMain:
    def test_should_ask_for_a_terminal_login_instead_of_prompting_without_one(
            self, monkeypatch, capsys, tmp_path):
        set_environment(monkeypatch, CREDENTIALS)
        monkeypatch.setattr(cli, "TelegramClient", LoggedOutClient)
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)

        status = cli.main(["some_channel", "--output", str(tmp_path / "music"),
                           "--session", str(tmp_path / "session")])

        assert status == 2
        assert "not logged in" in capsys.readouterr().err

    def test_should_exit_with_a_usage_error_when_credentials_are_missing(self, monkeypatch, capsys):
        set_environment(monkeypatch, {})

        assert cli.main(["some_channel"]) == 2
        assert "TELEGRAM_API_ID" in capsys.readouterr().err

    def test_should_exit_with_a_usage_error_for_an_unsupported_proxy(self, monkeypatch, capsys):
        set_environment(monkeypatch, CREDENTIALS)

        assert cli.main(["some_channel", "--proxy", "ftp://host:21"]) == 2
        assert "unsupported proxy" in capsys.readouterr().err
