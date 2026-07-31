from cli_anything.ncm_playlist.core.client import NeteaseClient, parse_cookie_header


def test_cookie_parser_and_defaults():
    parsed = parse_cookie_header("MUSIC_U=secret; __csrf=token")
    assert parsed == {"MUSIC_U": "secret", "__csrf": "token"}
    assert NeteaseClient().base_url == "https://music.163.com"
