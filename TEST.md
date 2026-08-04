# TEST.md

## Local checks

```bash
python -m pytest -q
python -m cli_anything.ncm_playlist --json self-check
python -m cli_anything.ncm_playlist --json playlist publish \
  --manifest scenario-100.json \
  --dry-run
```

## Official CLI check

The project delegates authenticated writes to `@music163/ncm-cli@0.1.6`:

```bash
ncm-cli login --check --output json
NCM_CLI_BIN=/path/to/ncm-cli \
  python -m cli_anything.ncm_playlist --json auth status
```

## Live publish check

Use a disposable manifest only when a real write is intended. The command creates a playlist, adds and reorders all 100 encrypted song IDs, updates description/tags/cover, and verifies both the official CLI readback and the anonymous public playlist detail.

```bash
python -m cli_anything.ncm_playlist --json playlist publish \
  --manifest scenario-100.json
```

The output must contain a numeric playlist URL, `cli_track_count: 100`, and `public_track_count: 100`. Never put CLI credentials, cookies, or account data in fixtures or commits.
