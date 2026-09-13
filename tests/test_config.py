# -*- coding: utf-8 -*-
"""ConfigManager behaviour that the rest of the app relies on."""
import json

import pytest

from devtoolbox.core.config import ConfigManager
from devtoolbox.core.fields import BoolField, ChoiceField


@pytest.fixture
def manager(tmp_path):
    cfg = ConfigManager(tmp_path / "config.json", autosave_ms=10)
    cfg.register_defaults("tools.demo", [
        BoolField("flag", "Flag", default=True),
        ChoiceField("mode", "Mode", default="a", choices=[("A", "a"), ("B", "b")]),
    ])
    return cfg


def test_defaults_come_from_the_schema(manager):
    assert manager.get("tools.demo.flag") is True
    assert manager.get("tools.demo.mode") == "a"
    assert manager.get("tools.demo.missing", "fallback") == "fallback"


def test_defaults_are_not_written_to_disk(manager):
    manager.save_now()
    stored = json.loads(manager.path.read_text(encoding="utf-8"))
    assert stored.get("tools", {}).get("demo", {}) == {}


def test_set_emits_once_and_persists(manager):
    seen = []
    manager.changed.connect(lambda path, value: seen.append((path, value)))
    manager.set("tools.demo.flag", False)
    manager.set("tools.demo.flag", False)          # unchanged: no second signal
    assert seen == [("tools.demo.flag", False)]
    manager.save_now()
    stored = json.loads(manager.path.read_text(encoding="utf-8"))
    assert stored["tools"]["demo"]["flag"] is False


def test_reset_restores_the_default(manager):
    manager.set("tools.demo.mode", "b")
    assert manager.get("tools.demo.mode") == "b"
    manager.reset("tools.demo.mode")
    assert manager.get("tools.demo.mode") == "a"


def test_scope_is_limited_to_its_namespace(manager):
    scope = manager.scope("tools.demo")
    scope.set("flag", False)
    assert manager.get("tools.demo.flag") is False
    relayed = []
    scope.changed.connect(lambda key, value: relayed.append(key))
    manager.set("tools.other.flag", True)          # another tool's namespace
    manager.set("tools.demo.mode", "b")
    assert relayed == ["mode"]


def test_snapshot_rollback(manager):
    snapshot = manager.to_dict()
    manager.set("tools.demo.flag", False)
    manager.restore_snapshot(snapshot)
    assert manager.get("tools.demo.flag") is True


def test_corrupt_file_is_backed_up_not_fatal(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ this is not json", encoding="utf-8")
    cfg = ConfigManager(path)
    assert cfg.get("anything", "ok") == "ok"
    assert path.with_suffix(".corrupt.json").exists()
