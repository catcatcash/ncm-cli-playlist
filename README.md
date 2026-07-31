# ncm-cli-playlist

A small CLI-Anything-style harness for NetEase Cloud Music playlist management.

The installed `@music163/ncm-cli@0.1.6` binary currently exposes playback and queue commands, while its README advertises search and playlist management that are not registered by the shipped binary. This project provides the missing playlist workflow without modifying or monkey-patching the upstream package.

## First version

- Check NetEase login status
- Search songs through the public web API
- Create a playlist
- Add songs to a playlist in batches
- List the current user's playlists
- JSON output for agents
- `--dry-run` for every write command
- Minimal REPL when invoked without a subcommand

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

The CLI uses a NetEase web cookie for account operations. Do not commit it.

```bash
export NETEASE_COOKIE='MUSIC_U=...; __csrf=...'
cli-anything-ncm-playlist auth status
```

If you only need public search, no cookie is required:

```bash
cli-anything-ncm-playlist --json search song --keyword 'Nujabes' --limit 5
```

## Create and fill a playlist

```bash
# Preview the write request first
cli-anything-ncm-playlist --json playlist create \
  --name '低温网络与夜行爵士' \
  --description 'Lain / Lily Chou-Chou / EVA / Bebop / Champloo adjacent sounds' \
  --dry-run

# Create it for real
cli-anything-ncm-playlist --json playlist create \
  --name '低温网络与夜行爵士'

# Add known song IDs; repeat --track-id as needed
cli-anything-ncm-playlist --json playlist add \
  --playlist-id 123456789 \
  --track-id 123 \
  --track-id 456

# Or read one numeric ID per line
cli-anything-ncm-playlist --json playlist add \
  --playlist-id 123456789 \
  --file track_ids.txt
```

The tool returns NetEase URLs for songs and playlists. It does not guess which search result to add: resolve and review IDs first.

## Development

```bash
python -m pytest -q
python -m cli_anything.ncm_playlist --help
python -m cli_anything.ncm_playlist self-check
```

## Scope and roadmap

This first cut deliberately stops at the smallest useful write path. Possible follow-ups:

- resolve `artist - title` queries with an explicit result selector;
- update playlist metadata and tags;
- remove and reorder tracks;
- import a text/CSV/JSON playlist;
- expose a browser-cookie helper without writing secrets to disk;
- upstream a focused fix or feature request to `@music163/ncm-cli`.

## License

MIT
