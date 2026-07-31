"""Small requests-based client for the NetEase web API."""
from __future__ import annotations

import json
import os
from typing import Any, Iterable

import requests


class NeteaseAPIError(RuntimeError):
    """Raised when NetEase rejects a request or the response is invalid."""


def parse_cookie_header(value: str | None) -> dict[str, str]:
    """Parse a browser Cookie header without logging or persisting its values."""
    result: dict[str, str] = {}
    for part in (value or "").split(";"):
        if "=" not in part:
            continue
        key, raw_value = part.strip().split("=", 1)
        if key:
            result[key] = raw_value
    return result


class NeteaseClient:
    def __init__(
        self,
        cookie: str | None = None,
        base_url: str = "https://music.163.com",
        timeout: float = 20.0,
    ) -> None:
        self.cookie = cookie or os.environ.get("NETEASE_COOKIE", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ncm-cli-playlist/0.1 (+https://github.com/catcatcash/ncm-cli-playlist)",
                "Referer": "https://music.163.com/",
            }
        )
        if self.cookie:
            self.session.headers["Cookie"] = self.cookie

    @property
    def csrf_token(self) -> str:
        return parse_cookie_header(self.cookie).get("__csrf", "")

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        allow_error: bool = False,
    ) -> dict[str, Any]:
        params = dict(params or {})
        data = dict(data or {})
        if self.csrf_token:
            target = params if method.upper() == "GET" else data
            target.setdefault("csrf_token", self.csrf_token)
        response = self.session.request(
            method.upper(),
            f"{self.base_url}{path}",
            params=params,
            data=data,
            timeout=self.timeout,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise NeteaseAPIError(
                f"NetEase returned non-JSON HTTP {response.status_code}"
            ) from exc
        if response.status_code >= 400:
            raise NeteaseAPIError(
                f"NetEase HTTP {response.status_code}: {payload.get('msg', payload)}"
            )
        if not allow_error and payload.get("code") not in (None, 200):
            raise NeteaseAPIError(
                f"NetEase API {payload.get('code')}: "
                f"{payload.get('msg') or payload.get('message') or 'request failed'}"
            )
        return payload

    def _require_cookie(self) -> None:
        if not self.cookie:
            raise NeteaseAPIError(
                "This operation needs a NetEase web cookie. "
                "Set NETEASE_COOKIE='MUSIC_U=...; __csrf=...' and retry."
            )

    @staticmethod
    def _song_summary(song: dict[str, Any]) -> dict[str, Any]:
        artists = song.get("ar") or song.get("artists") or []
        album = song.get("al") or song.get("album") or {}
        song_id = song.get("id")
        return {
            "id": song_id,
            "name": song.get("name", ""),
            "artists": [artist.get("name", "") for artist in artists],
            "album": album.get("name", ""),
            "url": f"https://music.163.com/#/song?id={song_id}",
        }

    def auth_status(self) -> dict[str, Any]:
        payload = self._request("/api/login/status", allow_error=True)
        data = payload.get("data") or {}
        account = data.get("account") or payload.get("account")
        profile = data.get("profile") or payload.get("profile")
        logged_in = payload.get("code") == 200 and bool(account or profile)
        return {
            "logged_in": logged_in,
            "account_id": (account or {}).get("id"),
            "nickname": (profile or {}).get("nickname"),
            "message": "logged in" if logged_in else "not logged in",
        }

    def search_songs(self, keyword: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        payload = self._request(
            "/api/search/get/web",
            params={"s": keyword, "type": 1, "limit": limit, "offset": offset},
        )
        songs = (payload.get("result") or {}).get("songs") or []
        return [self._song_summary(song) for song in songs]

    def create_playlist(
        self,
        name: str,
        description: str = "",
        tags: Iterable[str] = (),
        private: bool = False,
    ) -> dict[str, Any]:
        self._require_cookie()
        payload = self._request(
            "/api/playlist/create",
            method="POST",
            data={
                "name": name,
                "privacy": 10 if private else 0,
                "type": "NORMAL",
                "description": description,
                "tags": ",".join(tag for tag in tags if tag),
            },
        )
        playlist = payload.get("playlist") or {}
        playlist_id = playlist.get("id") or payload.get("id")
        return {
            "id": playlist_id,
            "name": playlist.get("name", name),
            "url": f"https://music.163.com/#/playlist?id={playlist_id}",
        }

    def add_tracks(self, playlist_id: int, track_ids: Iterable[int]) -> dict[str, Any]:
        self._require_cookie()
        ids = [int(track_id) for track_id in track_ids]
        if not ids:
            raise NeteaseAPIError("at least one track ID is required")
        added = 0
        for start in range(0, len(ids), 100):
            chunk = ids[start : start + 100]
            self._request(
                "/api/playlist/manipulate/tracks",
                method="POST",
                data={
                    "op": "add",
                    "pid": playlist_id,
                    "trackIds": json.dumps(chunk, separators=(",", ":")),
                    "imme": "true",
                },
            )
            added += len(chunk)
        return {
            "playlist_id": playlist_id,
            "added": added,
            "url": f"https://music.163.com/#/playlist?id={playlist_id}",
        }

    def list_playlists(self, uid: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if uid is None:
            status = self.auth_status()
            uid = status.get("account_id")
            if not uid:
                raise NeteaseAPIError("uid is required when no logged-in account is available")
        payload = self._request("/api/user/playlist", params={"uid": uid, "limit": limit})
        playlists = payload.get("playlist") or []
        return [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "track_count": item.get("trackCount", 0),
                "url": f"https://music.163.com/#/playlist?id={item.get('id')}",
            }
            for item in playlists
        ]
