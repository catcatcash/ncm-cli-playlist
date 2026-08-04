from cli_anything.ncm_playlist.core.official_cli import validate_scenario_manifest


def manifest():
    return {
        "name": "褪色的夜行|爵士嘻哈 梦泡 硬地 ACG",
        "description": "情绪钩子。\n\n选歌逻辑。\n\n音乐科普。",
        "tags": ["说唱", "电子", "另类/独立"],
        "tracks": [{"encrypted_id": f"song-{i:03d}"} for i in range(100)],
    }


def test_scenario_manifest_normalizes_title_and_accepts_100_unique_tracks():
    result = validate_scenario_manifest(manifest())
    assert result["name"] == "褪色的夜行｜爵士嘻哈 梦泡 硬地 ACG"
    assert len(result["tracks"]) == 100


def test_scenario_manifest_rejects_wrong_track_count():
    value = manifest()
    value["tracks"] = value["tracks"][:-1]
    try:
        validate_scenario_manifest(value)
    except ValueError as exc:
        assert "exactly 100" in str(exc)
    else:
        raise AssertionError("expected exact-count validation")


def test_scenario_manifest_rejects_duplicate_encrypted_ids():
    value = manifest()
    value["tracks"][-1]["encrypted_id"] = value["tracks"][0]["encrypted_id"]
    try:
        validate_scenario_manifest(value)
    except ValueError as exc:
        assert "unique encrypted_id" in str(exc)
    else:
        raise AssertionError("expected duplicate validation")
