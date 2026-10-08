"""Turns a proxy URL into the settings Telethon connects through."""
import re

PROXY_PATTERN = re.compile(r"^(socks5|socks4|http)://([^:/]+):(\d+)$", re.IGNORECASE)


def parse_proxy(url):
    """Returns Telethon proxy settings for a socks5, socks4 or http URL, or None for no proxy.

    Raises ValueError for anything else, so a typo fails loudly instead of
    quietly connecting without the proxy.
    """
    if not url:
        return None
    match = PROXY_PATTERN.match(url.strip())
    if not match:
        raise ValueError(
            f"unsupported proxy {url!r}; use socks5://host:port, socks4://host:port"
            " or http://host:port")
    scheme, host, port = match.groups()
    return {"proxy_type": scheme.lower(), "addr": host, "port": int(port), "rdns": True}
