# -*- coding: utf-8 -*-
"""Single source of truth for every setting.

* One store: config.json
* Per-tool namespaces (tools.<id>.*) so tools cannot collide
* Only values the user actually changed are written; defaults live in schemas
* Atomic writes plus config_version based migration

See docs/CONFIG.md for the full reference.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from .fields import ActionField, Field
from .qt import QObject, QTimer, Signal

log = logging.getLogger(__name__)

CONFIG_VERSION = 1

#: {from_version: converter}. Add one step whenever a stored key changes shape.
MIGRATIONS: Dict[int, Callable[[dict], dict]] = {}

_MISSING = object()


class ConfigScope(QObject):
    """A view onto one namespace. This is all a plugin ever receives."""

    changed = Signal(str, object)   # relative key, new value

    def __init__(self, manager: "ConfigManager", namespace: str):
        super().__init__(manager)
        self._m = manager
        self._ns = namespace.rstrip(".")
        manager.changed.connect(self._on_manager_changed)

    @property
    def namespace(self) -> str:
        return self._ns

    def _full(self, key: str) -> str:
        return "%s.%s" % (self._ns, key)

    def _on_manager_changed(self, path: str, value: object) -> None:
        if path == "":                       # bulk reload (import / snapshot restore)
            self.changed.emit("", None)
            return
        prefix = self._ns + "."
        if path.startswith(prefix):
            self.changed.emit(path[len(prefix):], value)

    def get(self, key: str, default: Any = None) -> Any:
        return self._m.get(self._full(key), default)

    def set(self, key: str, value: Any) -> None:
        self._m.set(self._full(key), value)

    def reset(self, key: str) -> None:
        self._m.reset(self._full(key))

    def keys(self) -> List[str]:
        return self._m.keys_in(self._ns)


class ConfigManager(QObject):
    changed = Signal(str, object)   # dotted path, new value ("" means reload everything)

    def __init__(self, path, autosave_ms: int = 400):
        super().__init__()
        self._path = Path(path)
        self._data: dict = {}
        self._defaults: Dict[str, Any] = {}
        self._scopes: Dict[str, ConfigScope] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(autosave_ms)
        self._timer.timeout.connect(self.save_now)
        self.load()

    # -------------------------------------------------------------- load/save
    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        if not self._path.exists():
            self._data = {"config_version": CONFIG_VERSION}
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("top level of the config file is not an object")
            self._data = raw
        except Exception:
            log.exception("Could not read the config file; backing it up and "
                          "starting fresh: %s", self._path)
            try:
                shutil.copy2(self._path, self._path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            self._data = {"config_version": CONFIG_VERSION}
            return
        self._migrate()

    def _migrate(self) -> None:
        version = int(self._data.get("config_version", 0) or 0)
        while version < CONFIG_VERSION:
            converter = MIGRATIONS.get(version)
            if converter is None:
                break
            log.info("Migrating config v%d -> v%d", version, version + 1)
            try:
                shutil.copy2(self._path,
                             self._path.with_name(self._path.name + ".bak.v%d" % version))
            except OSError:
                pass
            self._data = converter(self._data)
            version += 1
        self._data["config_version"] = max(version, CONFIG_VERSION)

    def save_now(self) -> bool:
        """Write to a temp file, then swap it in atomically."""
        self._timer.stop()
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_name(self._path.name + ".tmp")
            tmp.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(str(tmp), str(self._path))
            return True
        except OSError:
            log.exception("Could not save the config file: %s", self._path)
            return False

    # --------------------------------------------------------------- defaults
    def register_defaults(self, namespace: str, schema: Iterable[Field]) -> None:
        for f in schema:
            if isinstance(f, ActionField):
                continue
            self._defaults["%s.%s" % (namespace.rstrip("."), f.key)] = f.default

    def default_of(self, path: str, fallback: Any = None) -> Any:
        return self._defaults.get(path, fallback)

    # ------------------------------------------------------------- read/write
    def get(self, path: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = _MISSING
                break
        if node is not _MISSING:
            return node
        if path in self._defaults:
            return self._defaults[path]
        return default

    def set(self, path: str, value: Any) -> None:
        parts = path.split(".")
        node = self._data
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        if node.get(parts[-1], _MISSING) == value:
            return                       # unchanged: no signal, no write
        node[parts[-1]] = value
        self._timer.start()
        self.changed.emit(path, value)

    def reset(self, path: str) -> None:
        """Drop the stored value so the schema default applies again."""
        parts = path.split(".")
        node = self._data
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                return
            node = child
        if parts[-1] in node:
            del node[parts[-1]]
            self._timer.start()
            self.changed.emit(path, self.get(path))

    def keys_in(self, namespace: str) -> List[str]:
        node: Any = self._data
        for part in namespace.split("."):
            if not isinstance(node, dict) or part not in node:
                return []
            node = node[part]
        return sorted(node) if isinstance(node, dict) else []

    # ------------------------------------------------------------------ scope
    def scope(self, namespace: str) -> ConfigScope:
        ns = namespace.rstrip(".")
        if ns not in self._scopes:
            self._scopes[ns] = ConfigScope(self, ns)
        return self._scopes[ns]

    # ------------------------------------------------------- snapshot / files
    def to_dict(self) -> dict:
        return json.loads(json.dumps(self._data))

    def restore_snapshot(self, snapshot: dict) -> None:
        """Roll back to a to_dict() snapshot. Used by Cancel in the Settings dialog."""
        self._data = json.loads(json.dumps(snapshot))
        self._timer.start()
        self.changed.emit("", None)

    def export_to(self, path) -> None:
        Path(path).write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def import_from(self, path) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("top level of the config file is not an object")
        self._data = data
        self._migrate()
        self.save_now()
        self.changed.emit("", None)
