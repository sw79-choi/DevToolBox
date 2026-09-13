# -*- coding: utf-8 -*-
"""The Settings dialog is generated, so these guard the generation rules.

Runs headless: conftest.py sets QT_QPA_PLATFORM=offscreen.
"""
import pytest

from devtoolbox.core.config import ConfigManager
from devtoolbox.core.fields import BoolField, ChoiceField, IntField, TextField
from devtoolbox.core.qt import QtWidgets
from devtoolbox.ui.settings_dialog import SchemaForm

SCHEMA = [
    BoolField("enabled", "Enabled", default=True),
    ChoiceField("mode", "Mode", default="a", choices=[("A", "a"), ("B", "b")],
                depends_on="enabled"),
    IntField("count", "Count", default=3, minimum=0, maximum=10),
    TextField("note", "Note", default="hello"),
    TextField("secret", "Secret", default="x", hidden=True),
]


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def form(app, tmp_path):
    manager = ConfigManager(tmp_path / "config.json", autosave_ms=10)
    manager.register_defaults("tools.demo", SCHEMA)
    scope = manager.scope("tools.demo")
    return SchemaForm("Demo", "A demo tool.", SCHEMA, scope), manager, scope


def test_hidden_fields_get_no_widget(form):
    page, _manager, _scope = form
    assert "secret" not in page.editors
    assert set(page.editors) == {"enabled", "mode", "count", "note"}


def test_widgets_start_from_the_schema_defaults(form):
    page, _manager, _scope = form
    assert page.editors["enabled"].widget.isChecked() is True
    assert page.editors["count"].widget.value() == 3
    assert page.editors["note"].widget.text() == "hello"


def test_editing_a_widget_writes_through_to_config(form):
    page, _manager, scope = form
    page.editors["count"].widget.setValue(7)
    assert scope.get("count") == 7


def test_external_change_updates_the_widget(form):
    """A tool's own control writes to the same scope; the form must follow."""
    page, _manager, scope = form
    scope.set("note", "changed elsewhere")
    assert page.editors["note"].widget.text() == "changed elsewhere"


def test_dependent_field_follows_its_parent_from_either_side(form):
    page, _manager, scope = form
    mode = page.editors["mode"].widget
    assert mode.isEnabled()

    scope.set("enabled", False)                     # changed outside the dialog
    assert page.editors["enabled"].widget.isChecked() is False
    assert not mode.isEnabled()

    page.editors["enabled"].widget.setChecked(True)  # toggled inside the dialog
    assert scope.get("enabled") is True
    assert mode.isEnabled()


def test_restore_defaults_clears_stored_values(form):
    page, manager, scope = form
    scope.set("count", 9)
    scope.set("note", "edited")
    page.restore_defaults()
    assert scope.get("count") == 3
    assert page.editors["note"].widget.text() == "hello"
    manager.save_now()
    import json
    stored = json.loads(manager.path.read_text(encoding="utf-8"))
    assert stored.get("tools", {}).get("demo", {}) == {}


def test_snapshot_rollback_reaches_the_widgets(form):
    page, manager, scope = form
    snapshot = manager.to_dict()
    scope.set("count", 9)
    manager.restore_snapshot(snapshot)
    assert page.editors["count"].widget.value() == 3
