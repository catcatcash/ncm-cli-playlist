"""Agent-native Click CLI for NetEase playlist management."""
from __future__ import annotations

import json
import shlex
import sys
from functools import wraps
from typing import Callable

import click

from .core.client import NeteaseAPIError, NeteaseClient, parse_cookie_header


def emit(ctx: click.Context, value: object) -> None:
    if (ctx.obj or {}).get("json"):
        click.echo(json.dumps(value, ensure_ascii=False, indent=2))
    elif isinstance(value, list):
        for item in value:
            click.echo("  ".join(f"{key}={val}" for key, val in item.items()))
    elif isinstance(value, dict):
        for key, val in value.items():
            click.echo(f"{key}: {val}")
    else:
        click.echo(value)


def api_errors(func: Callable) -> Callable:
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NeteaseAPIError as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapped


def client_from(ctx: click.Context) -> NeteaseClient:
    obj = ctx.obj or {}
    return NeteaseClient(cookie=obj.get("cookie"), base_url=obj.get("base_url", "https://music.163.com"))


@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--cookie", envvar="NETEASE_COOKIE", help="NetEase web Cookie header; never commit it.")
@click.option("--base-url", envvar="NETEASE_BASE_URL", default="https://music.163.com", show_default=True)
@click.pass_context
def cli(ctx: click.Context, json_output: bool, cookie: str | None, base_url: str) -> None:
    """Create and manage NetEase Cloud Music playlists."""
    ctx.ensure_object(dict)
    ctx.obj.update({"json": json_output, "cookie": cookie, "base_url": base_url})
    if ctx.invoked_subcommand is None:
        repl_loop(ctx.obj)


@cli.group()
def auth() -> None:
    """Authentication status."""


@auth.command("status")
@click.pass_context
@api_errors
def auth_status(ctx: click.Context) -> None:
    emit(ctx, client_from(ctx).auth_status())


@cli.group()
def search() -> None:
    """Public search commands."""


@search.command("song")
@click.option("--keyword", required=True)
@click.option("--limit", type=click.IntRange(1, 100), default=20, show_default=True)
@click.option("--offset", type=click.IntRange(0), default=0, show_default=True)
@click.pass_context
@api_errors
def search_song(ctx: click.Context, keyword: str, limit: int, offset: int) -> None:
    emit(ctx, client_from(ctx).search_songs(keyword, limit, offset))


@cli.group()
def playlist() -> None:
    """Playlist management commands."""


@playlist.command("create")
@click.option("--name", required=True)
@click.option("--description", default="", show_default=True)
@click.option("--tag", "tags", multiple=True)
@click.option("--private", is_flag=True, help="Create a private playlist.")
@click.option("--dry-run", is_flag=True, help="Print the write intent without calling NetEase.")
@click.pass_context
@api_errors
def playlist_create(ctx: click.Context, name: str, description: str, tags: tuple[str, ...], private: bool, dry_run: bool) -> None:
    intent = {"operation": "playlist.create", "name": name, "description": description, "tags": list(tags), "private": private}
    if dry_run:
        emit(ctx, {"dry_run": True, "request": intent})
        return
    emit(ctx, client_from(ctx).create_playlist(name, description, tags, private))


@playlist.command("add")
@click.option("--playlist-id", type=int, required=True)
@click.option("--track-id", "track_ids", type=int, multiple=True)
@click.option("--file", type=click.File("r", encoding="utf-8"), help="One numeric track ID per line or a JSON array.")
@click.option("--dry-run", is_flag=True, help="Print the write intent without calling NetEase.")
@click.pass_context
@api_errors
def playlist_add(ctx: click.Context, playlist_id: int, track_ids: tuple[int, ...], file, dry_run: bool) -> None:
    ids = list(track_ids)
    if file:
        raw = file.read().strip()
        if raw:
            try:
                loaded = json.loads(raw)
                ids.extend(int(value) for value in loaded) if isinstance(loaded, list) else ids.append(int(loaded))
            except json.JSONDecodeError:
                ids.extend(int(line.strip()) for line in raw.splitlines() if line.strip())
    if not ids:
        raise click.UsageError("provide at least one --track-id or --file")
    if dry_run:
        emit(ctx, {"dry_run": True, "request": {"operation": "playlist.add", "playlist_id": playlist_id, "track_ids": ids}})
        return
    emit(ctx, client_from(ctx).add_tracks(playlist_id, ids))


@playlist.command("list")
@click.option("--uid", type=int, default=None, help="NetEase user ID; defaults to the logged-in account.")
@click.option("--limit", type=click.IntRange(1, 1000), default=100, show_default=True)
@click.pass_context
@api_errors
def playlist_list(ctx: click.Context, uid: int | None, limit: int) -> None:
    emit(ctx, client_from(ctx).list_playlists(uid, limit))


@cli.command("self-check")
@click.pass_context
def self_check(ctx: click.Context) -> None:
    parsed = parse_cookie_header("MUSIC_U=secret; __csrf=token")
    assert parsed["__csrf"] == "token"
    assert NeteaseClient().base_url == "https://music.163.com"
    emit(ctx, {"ok": True, "checks": ["cookie parser", "client defaults"]})


def repl_loop(obj: dict) -> None:
    click.echo("ncm-playlist REPL; type 'help' or 'quit'.")
    while True:
        try:
            line = input("ncm-playlist> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo()
            return
        if not line:
            continue
        if line in {"quit", "exit"}:
            return
        if line == "help":
            click.echo("auth status | search song --keyword TEXT | playlist create/add/list | quit")
            continue
        try:
            cli.main(args=shlex.split(line), standalone_mode=False, obj=obj)
        except SystemExit:
            pass
        except click.ClickException as exc:
            click.echo(f"Error: {exc}", err=True)


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
