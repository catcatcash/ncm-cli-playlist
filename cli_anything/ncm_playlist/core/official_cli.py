"""Official @music163/ncm-cli adapter and scenario playlist publishing."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

import requests


class OfficialNcmCliError(RuntimeError):
    """Raised when the official ncm-cli command or readback fails."""


def _records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("records", "tracks", "songs"):
            if isinstance(data.get(key), list):
                return data[key]
    for key in ("records", "tracks", "songs"):
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def canonical_scenario_title(value: str) -> str:
    """Normalize the content-ops title shape: theme｜category category ..."""
    title = str(value or "").strip().replace("|", "｜")
    if title.count("｜") != 1:
        raise ValueError("title must contain exactly one '｜' separator")
    theme, categories = (part.strip() for part in title.split("｜", 1))
    category_items = [item for item in re.split(r"[、,，\s]+", categories) if item]
    if not theme or len(category_items) < 2:
        raise ValueError("title must be 'theme｜category category ...' with at least two categories")
    return f"{theme}｜{' '.join(category_items)}"


def validate_scenario_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one publishable scenario playlist manifest."""
    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON object")
    required = ("name", "description", "tags", "tracks")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"manifest missing: {', '.join(missing)}")

    manifest = copy.deepcopy(raw)
    manifest["name"] = canonical_scenario_title(manifest["name"])
    if not str(manifest["description"]).strip():
        raise ValueError("description must not be empty")
    if not isinstance(manifest["tags"], list) or not 1 <= len(manifest["tags"]) <= 3:
        raise ValueError("tags must contain 1 to 3 values")
    if any(not str(tag).strip() for tag in manifest["tags"]):
        raise ValueError("tags must not contain empty values")

    tracks = manifest["tracks"]
    if not isinstance(tracks, list) or len(tracks) != 100:
        raise ValueError("scenario playlist must contain exactly 100 tracks")
    encrypted_ids: list[str] = []
    for index, track in enumerate(tracks, 1):
        if not isinstance(track, dict) or not str(track.get("encrypted_id", "")).strip():
            raise ValueError(f"track {index} needs an encrypted_id")
        encrypted_ids.append(str(track["encrypted_id"]).strip())
    if len(set(encrypted_ids)) != 100:
        raise ValueError("tracks must contain 100 unique encrypted_id values")

    cover = manifest.get("cover")
    if cover:
        path = Path(cover).expanduser()
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("cover must be JPEG or PNG")
        if not path.is_file():
            raise ValueError(f"cover file not found: {path}")
        manifest["cover"] = str(path)
    manifest["tags"] = [str(tag).strip() for tag in manifest["tags"]]
    return manifest


class OfficialNcmCli:
    """Thin subprocess wrapper around the authenticated official CLI."""

    def __init__(self, executable: str | None = None, timeout: float = 120.0) -> None:
        configured = executable or os.environ.get("NCM_CLI_BIN") or "ncm-cli"
        self.executable = shutil.which(configured) or configured
        self.timeout = timeout

    def _run(self, *args: str) -> dict[str, Any]:
        command = [self.executable, *args, "--output", "json"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout)
        except FileNotFoundError as exc:
            raise OfficialNcmCliError(
                "official ncm-cli not found; install @music163/ncm-cli@0.1.6 or set NCM_CLI_BIN"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise OfficialNcmCliError("ncm-cli timed out") from exc

        output = result.stdout.strip()
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as exc:
            detail = (result.stderr or output)[-800:]
            raise OfficialNcmCliError(f"ncm-cli returned non-JSON output: {detail}") from exc
        if result.returncode != 0:
            raise OfficialNcmCliError(payload.get("message") or result.stderr.strip() or "ncm-cli failed")
        if payload.get("success") is False or payload.get("code") not in (None, 200):
            raise OfficialNcmCliError(payload.get("message") or payload.get("msg") or "ncm-cli rejected request")
        return payload

    def auth_status(self) -> dict[str, Any]:
        return self._run("login", "--check")

    def create_playlist(self, name: str) -> dict[str, Any]:
        return self._run("playlist", "create", "--playlistName", name)

    def add_tracks(self, playlist_id: str, encrypted_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = [str(value) for value in encrypted_ids]
        if not ids:
            raise OfficialNcmCliError("at least one encrypted track ID is required")
        results = []
        for start in range(0, len(ids), 100):
            results.append(self._run(
                "playlist", "add", "--playlistId", str(playlist_id),
                "--songIdList", json.dumps(ids[start:start + 100], separators=(",", ":")),
            ))
        return results

    def reorder(self, playlist_id: str, encrypted_ids: Iterable[str]) -> dict[str, Any]:
        ids = [str(value) for value in encrypted_ids]
        if not ids:
            raise OfficialNcmCliError("at least one encrypted track ID is required")
        return self._run(
            "playlist", "reorder", "--playlistId", str(playlist_id),
            "--trackIds", json.dumps(ids, separators=(",", ":")),
        )

    def update_name(self, playlist_id: str, name: str) -> dict[str, Any]:
        return self._run("playlist", "updateName", "--playlistId", str(playlist_id), "--name", name)

    def update_description(self, playlist_id: str, description: str) -> dict[str, Any]:
        return self._run("playlist", "updateDesc", "--playlistId", str(playlist_id), "--desc", description)

    def update_tags(self, playlist_id: str, tags: Iterable[str]) -> dict[str, Any]:
        return self._run(
            "playlist", "updateTags", "--playlistId", str(playlist_id),
            "--tags", json.dumps(list(tags), ensure_ascii=False, separators=(",", ":")),
        )

    def update_cover(self, playlist_id: str, cover: str) -> dict[str, Any]:
        return self._run("playlist", "updateCover", "--playlistId", str(playlist_id), "--picIds", cover)

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        return self._run("playlist", "get", "--playlistId", str(playlist_id))

    def get_tracks(self, playlist_id: str) -> dict[str, Any]:
        return self._run("playlist", "tracks", "--playlistId", str(playlist_id), "--limit", "500", "--offset", "0")

    def publish(self, raw_manifest: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        manifest = validate_scenario_manifest(raw_manifest)
        encrypted_ids = [track["encrypted_id"] for track in manifest["tracks"]]
        if dry_run:
            return {
                "dry_run": True,
                "request": {
                    "operation": "playlist.publish",
                    "name": manifest["name"],
                    "tags": manifest["tags"],
                    "track_count": len(encrypted_ids),
                    "cover": manifest.get("cover"),
                },
            }

        created = self.create_playlist(manifest["name"])
        created_data = created.get("data") or {}
        playlist_id = created_data.get("id")
        if not playlist_id:
            raise OfficialNcmCliError("create returned no encrypted playlist ID")
        self.add_tracks(playlist_id, encrypted_ids)
        self.reorder(playlist_id, encrypted_ids)
        self.update_name(playlist_id, manifest["name"])
        self.update_description(playlist_id, manifest["description"])
        self.update_tags(playlist_id, manifest["tags"])
        if manifest.get("cover"):
            self.update_cover(playlist_id, manifest["cover"])

        detail = self.get_playlist(playlist_id)
        tracks = self.get_tracks(playlist_id)
        detail_data = detail.get("data") or {}
        actual_tracks = _records(tracks)
        if detail_data.get("trackCount") != 100 or len(actual_tracks) != 100:
            raise OfficialNcmCliError("publish readback did not contain exactly 100 tracks")
        original_id = detail_data.get("originalId") or created_data.get("originalId")
        public = public_playlist_detail(original_id) if original_id else {}
        if public and public.get("trackCount") != 100:
            raise OfficialNcmCliError("public readback did not contain exactly 100 tracks")
        return {
            "playlist": {
                "encrypted_id": playlist_id,
                "original_id": original_id,
                "name": detail_data.get("name", manifest["name"]),
                "url": f"https://music.163.com/#/playlist?id={original_id}",
            },
            "verification": {
                "cli_track_count": len(actual_tracks),
                "public_track_count": public.get("trackCount"),
                "public_name": public.get("name"),
                "public_tags": public.get("tags"),
                "cover_present": bool(detail_data.get("coverImgUrl")),
                "description_present": bool(detail_data.get("describe")),
            },
        }


def public_playlist_detail(original_id: int | str | None) -> dict[str, Any]:
    if not original_id:
        return {}
    response = requests.get(
        "https://music.163.com/api/v6/playlist/detail",
        params={"id": original_id, "n": 1000, "s": 8},
        headers={"User-Agent": "ncm-cli-playlist-content-ops/0.2"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("playlist") or {}
