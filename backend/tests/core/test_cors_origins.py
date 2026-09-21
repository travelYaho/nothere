from app.core.config import cors_origin_regex, expand_cors_origins


def test_expand_cors_origins_aliases_localhost_and_loopback():
    assert expand_cors_origins("http://localhost:5173") == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_expand_cors_origins_strips_slash_and_skips_blank():
    assert expand_cors_origins(" http://localhost:5173/ , ,http://localhost:3000") == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_cors_origin_regex_allows_lan_on_configured_ports():
    import re

    origins = expand_cors_origins("http://localhost:5173")
    pattern = cors_origin_regex(origins)
    assert pattern is not None
    regex = re.compile(pattern)
    assert regex.match("http://192.168.0.28:5173")
    assert regex.match("http://127.0.0.1:5173")
    assert regex.match("http://10.0.0.2:5173")
    assert not regex.match("http://192.168.0.28:3000")
    assert not regex.match("https://evil.example:5173")
