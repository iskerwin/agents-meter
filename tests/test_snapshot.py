import os
import stat

from agents_meter.quota import Account, Window
from agents_meter.snapshot import Snapshots, saved_snapshot_path


def saved_snapshot(captured_at: int, resets_at: int) -> dict:
    account = Account("codex", "Codex", captured_at=captured_at, windows=[Window("5 小时", 10, resets_at)])
    return {"accounts": [account.to_dict()], "usage": {"rows": []}, "tasks": [{"pid": 1}], "generated_at": 1}


def test_restored_snapshot_is_held_to_the_freshness_rules(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    snapshots = Snapshots(False)
    snapshots.save(saved_snapshot(captured_at=1000, resets_at=2**40))
    assert stat.S_IMODE(os.stat(saved_snapshot_path()).st_mode) == 0o600

    restored = snapshots.restored()
    assert restored["accounts"][0]["stale"] is True
    assert restored["most_urgent"] is None
    assert restored["tasks"] == []
    assert restored["refreshing"] is True
    assert restored["generated_at"] > 1

    snapshots.save(saved_snapshot(captured_at=1000, resets_at=2000))
    assert snapshots.restored()["accounts"][0]["windows"] == []


def test_a_missing_or_foreign_saved_snapshot_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    snapshots = Snapshots(False)
    assert snapshots.restored() is None
    saved_snapshot_path().parent.mkdir(parents=True)
    for text in ("{not json", "[]", '{"accounts": [{"name": "x"}]}'):
        saved_snapshot_path().write_text(text)
        assert snapshots.restored() is None
