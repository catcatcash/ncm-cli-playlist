import json
import subprocess
import sys
from pathlib import Path


def test_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "cli_anything.ncm_playlist", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "playlist" in result.stdout


def test_cli_version_runs():
    result = subprocess.run(
        [sys.executable, "-m", "cli_anything.ncm_playlist", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "0.2.0" in result.stdout


def test_cli_publish_dry_run_is_agent_safe(tmp_path: Path):
    manifest = {
        "name": "褪色的夜行｜爵士嘻哈 梦泡 硬地 ACG",
        "description": "情绪钩子。\n\n选歌逻辑。\n\n音乐科普。",
        "tags": ["说唱", "电子", "另类/独立"],
        "tracks": [{"encrypted_id": f"song-{i:03d}"} for i in range(100)],
    }
    path = tmp_path / "scenario-100.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli_anything.ncm_playlist",
            "--json",
            "playlist",
            "publish",
            "--manifest",
            str(path),
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["request"]["track_count"] == 100
