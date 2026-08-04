---
name: netease-content-ops
description: >
  Publish and verify NetEase Cloud Music scenario playlists as 100-track
  content packages through the official ncm-cli. Keep scene language separate
  from music categories and preserve the existing intro-30 playlist grammar.
triggers:
  - 场景化100首歌单
  - 网易云自动化内容运营
  - 创建网易云歌单
  - 发布网易云歌单
  - NetEase playlist content operations
---

# NetEase content operations

This skill is for the project's reusable playlist publishing workflow.

## Playlist families

Keep these two families separate:

- **Intro guides**: preserve the existing `adj的N | 类型入门30专` grammar.
- **Scenario playlists**: use `主题名｜并列音乐类别`.

For scenario playlists, the text before `｜` is the emotional scene/theme. The text after it must contain at least two actual music styles or music-culture categories. Do not use scene phrases such as `城市漂流` as if they were genres; put them in the theme or description.

## Description template

Keep the description short and human, in this order:

1. **Emotional hook** — one sentence or short paragraph that makes the listening scene felt. A short, source-attributed public-domain literary/film line or a user-provided quote may open the paragraph; do not use a long copyrighted excerpt.
2. **Selection logic** — where the sequence starts, how it moves, and what boundary it uses.
3. **Music context** — a concise explanation of the actual styles in the title and tracklist, such as jazz-hop, dream pop, hard-edged indie/alternative, or ACG soundtrack practice; do not paste generic lofi history unrelated to the playlist.

Avoid generic AI openings, inflated claims, and long source disclaimers.

## Manifest contract

A scenario manifest must contain:

```json
{
  "name": "褪色的夜行｜爵士嘻哈 梦泡 硬地 ACG",
  "description": "情绪钩子。\n\n选歌逻辑。\n\n音乐科普。",
  "tags": ["说唱", "电子", "另类/独立"],
  "cover": "./cover.jpg",
  "tracks": [{"encrypted_id": "..."}]
}
```

Validation requirements:

- exactly one `｜` separator in the title;
- at least two non-empty category terms after it;
- non-empty description;
- 1–3 platform tags;
- exactly 100 tracks;
- 100 unique encrypted song IDs;
- JPEG/PNG cover when supplied.

## Publish path

Use the official dynamic `@music163/ncm-cli` commands. Do not replay browser cookies or old `/api/playlist/*` write endpoints.

```bash
cli-anything-ncm-playlist --json playlist publish \
  --manifest scenario-100.json \
  --dry-run

cli-anything-ncm-playlist --json playlist publish \
  --manifest scenario-100.json
```

The publish operation must:

1. validate the manifest;
2. create the playlist through official `ncm-cli`;
3. add all tracks in batches;
4. reorder with the complete encrypted ID list;
5. update name, description, tags, and cover;
6. read back the CLI playlist and track count;
7. cross-check the anonymous public playlist detail.

`code=200` or process exit 0 is not sufficient evidence. A publish is complete only when the resource URL and both CLI/public readbacks are valid.

## Credential boundary

Browser login and CLI login are separate. Check the exact binary used by the project:

```bash
ncm-cli login --check --output json
NCM_CLI_BIN=/path/to/ncm-cli \
  cli-anything-ncm-playlist --json auth status
```

Never store cookies, QR tokens, account tokens, or other credentials in a manifest, test, log, skill, or commit.
