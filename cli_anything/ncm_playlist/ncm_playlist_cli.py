"""Agent-native CLI for NetEase playlist content operations."""
from __future__ import annotations

import json
import shlex
from functools import wraps
from typing import Callable

import click

from . import __version__
from .core.client import NeteaseAPIError, NeteaseClient, parse_cookie_header
from .core.official_cli import (
    OfficialNcmCli,
    OfficialNcmCliError,
    validate_scenario_manifest,
)


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
        except (NeteaseAPIError, OfficialNcmCliError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapped


def client_from(ctx: click.Context) -> NeteaseClient:
    obj = ctx.obj or {}
    return NeteaseClient(cookie=obj.get("cookie"), base_url=obj.get("base_url", "https://music.163.com"))


def official_from(ctx: click.Context) -> OfficialNcmCli:
    return OfficialNcmCli(executable=(ctx.obj or {}).get("ncm_cli"))


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--cookie", envvar="NETEASE_COOKIE", help="Cookie for public/read compatibility only; never commit it.")
@click.option("--base-url", envvar="NETEASE_BASE_URL", default="https://music.163.com", show_default=True)
@click.option("--ncm-cli", "ncm_cli", envvar="NCM_CLI_BIN", help="Official @music163/ncm-cli executable.")
@click.pass_context
def cli(ctx: click.Context, json_output: bool, cookie: str | None, base_url: str, ncm_cli: str | None) -> None:
    """Publish and maintain NetEase Cloud Music content through the official CLI."""
    ctx.ensure_object(dict)
    ctx.obj.update({"json": json_output, "cookie": cookie, "base_url": base_url, "ncm_cli": ncm_cli})
    if ctx.invoked_subcommand is None:
        repl_loop(ctx.obj)


@cli.group()
def auth() -> None:
    """Official ncm-cli authentication status."""


@auth.command("status")
@click.pass_context
@api_errors
def auth_status(ctx: click.Context) -> None:
    emit(ctx, official_from(ctx).auth_status())


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
    """Playlist and content-operations commands."""


@playlist.command("create")
@click.option("--name", required=True)
@click.option("--description", default="", show_default=True)
@click.option("--tag", "tags", multiple=True)
@click.option("--private", is_flag=True, help="Not supported by the official wrapper yet.")
@click.option("--dry-run", is_flag=True, help="Print the write intent without calling NetEase.")
@click.pass_context
@api_errors
def playlist_create(ctx: click.Context, name: str, description: str, tags: tuple[str, ...], private: bool, dry_run: bool) -> None:
    if private:
        raise click.UsageError("--private is not supported by the official ncm-cli write path")
    intent = {"operation": "playlist.create", "name": name, "description": description, "tags": list(tags)}
    if dry_run:
        emit(ctx, {"dry_run": True, "request": intent})
        return
    official = official_from(ctx)
    created = official.create_playlist(name)
    data = created.get("data") or {}
    playlist_id = data.get("id")
    if not playlist_id:
        raise OfficialNcmCliError("create returned no encrypted playlist ID")
    if description:
        official.update_description(playlist_id, description)
    if tags:
        official.update_tags(playlist_id, tags)
    emit(ctx, created)


@playlist.command("add")
@click.option("--playlist-id", required=True, help="Encrypted playlist ID from official ncm-cli.")
@click.option("--encrypted-track-id", "encrypted_ids", multiple=True)
@click.option("--file", type=click.File("r", encoding="utf-8"), help="JSON array or one encrypted song ID per line.")
@click.option("--dry-run", is_flag=True, help="Print the write intent without calling NetEase.")
@click.pass_context
@api_errors
def playlist_add(ctx: click.Context, playlist_id: str, encrypted_ids: tuple[str, ...], file, dry_run: bool) -> None:
    ids = list(encrypted_ids)
    if file:
        raw = file.read().strip()
        if raw:
            try:
                loaded = json.loads(raw)
                ids.extend(str(value) for value in loaded) if isinstance(loaded, list) else ids.append(str(loaded))
            except json.JSONDecodeError:
                ids.extend(line.strip() for line in raw.splitlines() if line.strip())
    if not ids:
        raise click.UsageError("provide at least one --encrypted-track-id or --file")
    if dry_run:
        emit(ctx, {"dry_run": True, "request": {"operation": "playlist.add", "playlist_id": playlist_id, "track_count": len(ids)}})
        return
    emit(ctx, {"batches": official_from(ctx).add_tracks(playlist_id, ids), "track_count": len(ids)})


@playlist.command("publish")
@click.option("--manifest", type=click.File("r", encoding="utf-8"), required=True)
@click.option("--dry-run", is_flag=True, help="Validate and preview without writing.")
@click.pass_context
@api_errors
def playlist_publish(ctx: click.Context, manifest, dry_run: bool) -> None:
    raw = json.load(manifest)
    emit(ctx, official_from(ctx).publish(raw, dry_run=dry_run))


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
    emit(ctx, {"ok": True, "checks": ["cookie parser", "official adapter import", "scenario manifest validation available"]})


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
            click.echo("auth status | search song --keyword TEXT | playlist create/add/publish/list | quit")
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
