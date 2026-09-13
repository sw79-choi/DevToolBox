# -*- coding: utf-8 -*-
"""Schema in, widgets out. Tools never draw their own settings page."""
from __future__ import annotations

from typing import Dict, List

from ..core.app_settings import APP_NS, APP_SCHEMA
from ..core.fields import (ActionField, BoolField, ChoiceField, Field, IntField,
                           MultiChoiceField, PathField, TextField)
from ..core.qt import (DBB_CANCEL, DBB_OK, DBB_RESET, DIALOG_ACCEPTED, ORIENT_H,
                       ROLE_USER, QtWidgets, exec_)


# ---------------------------------------------------------------------- editors
class _Editor:
    """One setting = one widget plus its binding to the config scope."""

    def __init__(self, field: Field, scope):
        self.field = field
        self.scope = scope
        self.widget = self._build()
        self.reload()

    def _build(self):
        raise NotImplementedError

    def reload(self):
        raise NotImplementedError

    def set_enabled(self, enabled: bool):
        self.widget.setEnabled(enabled)

    def _store(self, value):
        self.scope.set(self.field.key, value)


class _BoolEditor(_Editor):
    def _build(self):
        widget = QtWidgets.QCheckBox(self.field.label)
        widget.toggled.connect(self._store)
        return widget

    def reload(self):
        self.widget.blockSignals(True)
        self.widget.setChecked(bool(self.scope.get(self.field.key)))
        self.widget.blockSignals(False)


class _IntEditor(_Editor):
    def _build(self):
        widget = QtWidgets.QSpinBox()
        widget.setRange(self.field.minimum, self.field.maximum)
        widget.setSingleStep(self.field.step)
        if self.field.suffix:
            widget.setSuffix(" " + self.field.suffix)
        widget.valueChanged.connect(self._store)
        return widget

    def reload(self):
        self.widget.blockSignals(True)
        self.widget.setValue(int(self.scope.get(self.field.key) or 0))
        self.widget.blockSignals(False)


class _TextEditor(_Editor):
    def _build(self):
        widget = QtWidgets.QLineEdit()
        widget.setPlaceholderText(self.field.placeholder)
        widget.textChanged.connect(self._store)
        return widget

    def reload(self):
        self.widget.blockSignals(True)
        self.widget.setText(str(self.scope.get(self.field.key) or ""))
        self.widget.blockSignals(False)


class _ChoiceEditor(_Editor):
    def _build(self):
        widget = QtWidgets.QComboBox()
        for label, value in self.field.choices:
            widget.addItem(label, value)
        widget.currentIndexChanged.connect(
            lambda _index: self._store(self.widget.currentData()))
        return widget

    def reload(self):
        self.widget.blockSignals(True)
        index = self.widget.findData(self.scope.get(self.field.key))
        self.widget.setCurrentIndex(index if index >= 0 else 0)
        self.widget.blockSignals(False)


class _MultiChoiceEditor(_Editor):
    def _build(self):
        box = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self._checkboxes = []
        for label, value in self.field.choices:
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setProperty("value", value)
            checkbox.toggled.connect(self._collect)
            layout.addWidget(checkbox)
            self._checkboxes.append(checkbox)
        return box

    def _collect(self, *_):
        self._store([c.property("value") for c in self._checkboxes if c.isChecked()])

    def reload(self):
        current = self.scope.get(self.field.key) or []
        for checkbox in self._checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(checkbox.property("value") in current)
            checkbox.blockSignals(False)


class _PathEditor(_Editor):
    def _build(self):
        box = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        self._edit = QtWidgets.QLineEdit()
        self._edit.textChanged.connect(self._store)
        browse = QtWidgets.QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        layout.addWidget(self._edit, 1)
        layout.addWidget(browse)
        return box

    def _browse(self):
        start = self._edit.text()
        if self.field.mode == "dir":
            path = QtWidgets.QFileDialog.getExistingDirectory(
                self.widget, self.field.label, start)
        elif self.field.mode == "save":
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.widget, self.field.label, start, self.field.filter)
        else:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self.widget, self.field.label, start, self.field.filter)
        if path:
            self._edit.setText(path)

    def reload(self):
        self._edit.blockSignals(True)
        self._edit.setText(str(self.scope.get(self.field.key) or ""))
        self._edit.blockSignals(False)


class _ActionEditor(_Editor):
    def __init__(self, field, scope, ctx=None):
        self._ctx = ctx
        super().__init__(field, scope)

    def _build(self):
        button = QtWidgets.QPushButton(self.field.label)
        if self.field.callback:
            button.clicked.connect(lambda: self.field.callback(self._ctx))
        return button

    def reload(self):
        pass


_EDITORS = {
    BoolField: _BoolEditor,
    IntField: _IntEditor,
    TextField: _TextEditor,
    ChoiceField: _ChoiceEditor,
    MultiChoiceField: _MultiChoiceEditor,
    PathField: _PathEditor,
}


def make_editor(field: Field, scope, ctx=None) -> _Editor:
    """Add a branch here when you add a Field type."""
    if isinstance(field, ActionField):
        return _ActionEditor(field, scope, ctx)
    return _EDITORS[type(field)](field, scope)


# ------------------------------------------------------------------- form page
class SchemaForm(QtWidgets.QWidget):
    """One page of the Settings dialog, built from one schema."""

    def __init__(self, title: str, description: str, schema: List[Field], scope,
                 ctx=None, parent=None):
        super().__init__(parent)
        self.scope = scope
        self.schema = [f for f in schema if not f.hidden]
        self.editors: Dict[str, _Editor] = {}

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        outer.addWidget(QtWidgets.QLabel("<b>%s</b>" % title))
        if description:
            subtitle = QtWidgets.QLabel(description)
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet("color: palette(mid);")
            outer.addWidget(subtitle)

        form = QtWidgets.QFormLayout()
        form.setSpacing(9)
        outer.addLayout(form)

        for field in self.schema:
            editor = make_editor(field, scope, ctx)
            self.editors[field.key] = editor
            if isinstance(field, (BoolField, ActionField)):
                form.addRow("", editor.widget)
            else:
                form.addRow(field.label, editor.widget)
            if field.help:
                hint = QtWidgets.QLabel(field.help)
                hint.setWordWrap(True)
                hint.setStyleSheet("color: palette(mid); font-size: 11px;")
                form.addRow("", hint)

        if not self.schema:
            empty = QtWidgets.QLabel("This tool has no settings.")
            empty.setStyleSheet("color: palette(mid);")
            outer.addWidget(empty)

        outer.addStretch(1)
        self._wire_dependencies()

    def _wire_dependencies(self):
        """depends_on: grey out a field while its controlling checkbox is off."""
        for field in self.schema:
            if not field.depends_on:
                continue
            parent = self.editors.get(field.depends_on)
            if parent is None:
                continue
            child = self.editors[field.key]
            update = (lambda _checked=None, c=child, key=field.depends_on:
                      c.set_enabled(bool(self.scope.get(key))))
            if isinstance(parent.widget, QtWidgets.QCheckBox):
                parent.widget.toggled.connect(update)
            update()

    def reload(self):
        for editor in self.editors.values():
            editor.reload()

    def restore_defaults(self):
        for field in self.schema:
            if isinstance(field, ActionField):
                continue
            self.scope.reset(field.key)
        self.reload()


# ----------------------------------------------------------------- the dialog
class SettingsDialog(QtWidgets.QDialog):
    """Tree of categories and tools on the left, the matching form on the right."""

    def __init__(self, manager, plugins, contexts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(760, 540)
        self._manager = manager
        self._snapshot = manager.to_dict()   # Cancel rolls back to this

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(200)
        self.stack = QtWidgets.QStackedWidget()
        self._forms: List[SchemaForm] = []

        app_form = SchemaForm("Application", "Settings shared by every tool.",
                              APP_SCHEMA, manager.scope(APP_NS))
        self._add_page(None, "Application", app_form)

        categories: Dict[str, QtWidgets.QTreeWidgetItem] = {}
        for plugin in plugins:
            category = plugin.meta.category
            if category not in categories:
                node = QtWidgets.QTreeWidgetItem([category])
                self.tree.addTopLevelItem(node)
                node.setExpanded(True)
                categories[category] = node
            form = SchemaForm(
                plugin.meta.title, plugin.meta.description,
                plugin.settings_schema(),
                manager.scope("tools.%s" % plugin.meta.id),
                contexts.get(plugin.meta.id),
            )
            self._add_page(categories[category], plugin.meta.title, form)

        splitter = QtWidgets.QSplitter(ORIENT_H)
        splitter.addWidget(self.tree)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.stack)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(1, 1)

        buttons = QtWidgets.QDialogButtonBox(DBB_OK | DBB_CANCEL | DBB_RESET)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        reset_button = buttons.button(DBB_RESET)
        reset_button.setText("Reset This Page")
        reset_button.clicked.connect(self._restore_defaults)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addWidget(buttons)

        self.tree.currentItemChanged.connect(self._on_tree_changed)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _add_page(self, parent_item, title, form: SchemaForm):
        index = self.stack.addWidget(form)
        self._forms.append(form)
        item = QtWidgets.QTreeWidgetItem([title])
        item.setData(0, ROLE_USER, index)
        if parent_item is None:
            self.tree.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
        return item

    def _on_tree_changed(self, current, _previous):
        if current is None:
            return
        index = current.data(0, ROLE_USER)
        if index is None:
            # A category row: jump to its first tool instead.
            if current.childCount():
                self.tree.setCurrentItem(current.child(0))
            return
        self.stack.setCurrentIndex(index)

    def _restore_defaults(self):
        page = self.stack.currentWidget()
        if isinstance(page, SchemaForm):
            page.restore_defaults()

    def reject(self):
        """Values apply immediately, so Cancel has to roll the snapshot back."""
        self._manager.restore_snapshot(self._snapshot)
        for form in self._forms:
            form.reload()
        super().reject()


def open_settings(manager, plugins, contexts, parent=None) -> bool:
    """Show the Settings dialog. True if the user clicked OK."""
    dialog = SettingsDialog(manager, plugins, contexts, parent)
    return exec_(dialog) == DIALOG_ACCEPTED
