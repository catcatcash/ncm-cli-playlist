# cli-anything-ncm-playlist

A small agent-native content-operations CLI for NetEase Cloud Music.

The write path delegates to the authenticated official `@music163/ncm-cli@0.1.6` command registry. It does **not** replay browser cookies or the old `/api/playlist/*` write endpoints.

## What it does

- check the exact CLI login session;
- search public songs through the read client;
- create/add/manage playlists through official `ncm-cli` commands;
- publish a validated scenario playlist as one content package;
- support `--dry-run` before external writes;
- read back the playlist through both CLI and anonymous public API.

The current vertical slice is playlist content publishing. It deliberately does not automate comments, artificial engagement, or scheduling.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Install and authenticate the official CLI separately:

```bash
npm install -g @music163/ncm-cli@0.1.6
ncm-cli login --check --output json
```

If `ncm-cli` is not on `PATH`, set its exact executable:

```bash
export NCM_CLI_BIN="$HOME/.npm-global/bin/ncm-cli"
cli-anything-ncm-playlist --json auth status
```

The project does not store or print CLI credentials.

## Scenario playlist content package

A scenarioized 100-track playlist uses this title shape:

```text
主题名｜并列音乐类别
```

The left side is a short emotional/editorial theme. The right side contains at least two actual music categories, for example:

```text
褪色的夜行｜爵士嘻哈 梦泡 硬地 ACG
```

`城市漂流` belongs in the theme or description, not as if it were a music genre.

The description should stay short and human:

1. one emotional hook for the listening scene;
2. the selection logic and boundary;
3. concise music-history / genre context.

Manifest shape (schematic; `tracks` must contain exactly 100 unique encrypted IDs):

```json
{
  "name": "褪色的夜行｜爵士嘻哈 梦泡 硬地 ACG",
  "description": "情绪钩子。\n\n选歌逻辑。\n\n音乐科普。",
  "tags": ["说唱", "电子", "另类/独立"],
  "cover": "./cover.jpg",
  "tracks": [
    {"encrypted_id": "<official ncm-cli song id>"}
  ]
}
```

Preview first:

```bash
cli-anything-ncm-playlist --json playlist publish \
  --manifest scenario-100.json \
  --dry-run
```

Publish and verify:

```bash
cli-anything-ncm-playlist --json playlist publish \
  --manifest scenario-100.json
```

The command validates the title shape, description, 1–3 tags, 100 unique tracks, and JPEG/PNG cover. It then uses the official CLI to create, add, reorder, update metadata/cover, and read back the result. A successful output includes the numeric playlist URL and both CLI/public track counts.

## Direct commands

```bash
cli-anything-ncm-playlist --json auth status
cli-anything-ncm-playlist --json search song --keyword 'Nujabes' --limit 5
cli-anything-ncm-playlist --json playlist create --name '褪色的夜行｜爵士嘻哈 梦泡 硬地 ACG' --dry-run
cli-anything-ncm-playlist --json playlist add \
  --playlist-id '<encrypted playlist id>' \
  --encrypted-track-id '<encrypted song id>' \
  --dry-run
```

Do not pass ordinary numeric song IDs to `playlist add`; the official write command requires encrypted IDs. Resolve and review search results before adding.

## Development

```bash
python -m pytest -q
python -m cli_anything.ncm_playlist --help
python -m cli_anything.ncm_playlist self-check
```

## Scope boundary

Current scope: reliable playlist content publishing. Add scheduling, public content calendars, analytics, or other operations only when there is a concrete workflow and a real readback/rollback story. Never automate fake plays, collections, comments, or follows.

## License

MIT
