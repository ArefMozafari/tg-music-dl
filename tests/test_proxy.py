"""Tests for src/tg_music_dl/proxy.py."""
import pytest

from tg_music_dl.proxy import parse_proxy


class TestParseProxy:
    def test_should_parse_a_socks5_url(self):
        assert parse_proxy("socks5://127.0.0.1:1080") == {
            "proxy_type": "socks5", "addr": "127.0.0.1", "port": 1080, "rdns": True,
        }

    def test_should_parse_socks4_and_http_urls(self):
        assert parse_proxy("socks4://proxy.local:9050")["proxy_type"] == "socks4"
        assert parse_proxy("http://proxy.local:8080")["proxy_type"] == "http"

    def test_should_accept_an_upper_case_scheme(self):
        assert parse_proxy("SOCKS5://127.0.0.1:1080")["proxy_type"] == "socks5"

    def test_should_return_none_when_no_proxy_is_set(self):
        assert parse_proxy(None) is None
        assert parse_proxy("") is None

    @pytest.mark.parametrize("url", ["ftp://host:21", "127.0.0.1:1080", "socks5://host"])
    def test_should_reject_an_unsupported_url(self, url):
        with pytest.raises(ValueError, match="unsupported proxy"):
            parse_proxy(url)
