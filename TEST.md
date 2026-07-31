# TEST.md

## Local checks

```bash
python -m pytest -q
python -m cli_anything.ncm_playlist self-check
python -m cli_anything.ncm_playlist --json playlist create --name demo --dry-run
```

## Live checks

Live playlist writes require a user-provided `NETEASE_COOKIE`. Never put that value in a test fixture or commit it. Run a dry-run first, then create a disposable playlist and verify it with `playlist list`.
