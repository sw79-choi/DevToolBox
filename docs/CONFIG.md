# Settings

Every setting in the app lives in one file, in one process-wide
`ConfigManager`. Tools never touch `QSettings` or write files of their own.

## The file

```json
{
  "config_version": 1,
  "app": {
    "theme": "dark",
    "last_tab": "pdf_merger",
    "log_level": "INFO",
    "restore_last_tab": true
  },
  "window": { "geometry": "...base64..." },
  "tools": {
    "pdf_merger":     { "pad_odd": false, "pad_size": "a4" },
    "json_formatter": { "indent": 4 },
    "hash_tool":      { "algorithms": ["sha256"] }
  }
}
```

**Only values the user actually changed are stored.** Defaults live in the
schemas, so adjusting a default later reaches existing users automatically.

### Location

| Mode | Path |
| --- | --- |
| Normal (Windows) | `%APPDATA%\DevToolBox\config.json` |
| Normal (macOS) | `~/Library/Application Support/DevToolBox/config.json` |
| Normal (Linux) | `~/.config/DevToolBox/config.json` |
| Portable | `config.json` next to the app - create an empty `{}` there to switch |

Logs sit in a `logs/` folder beside the config file.

## ConfigManager API

| Method | Behaviour |
| --- | --- |
| `get(path, default=None)` | Dotted path lookup. Falls back to the schema default, then to `default`. |
| `set(path, value)` | Writes, emits `changed`, schedules a debounced save. A no-op if the value is unchanged. |
| `reset(path)` | Deletes the stored value so the schema default applies again. |
| `scope(ns)` | Returns a `ConfigScope` locked to that namespace. **This is what plugins get.** |
| `register_defaults(ns, schema)` | Collects defaults at boot. Writes nothing to disk. |
| `changed` | `Signal(str, object)` - dotted path and new value. An empty path means "reload everything". |
| `save_now()` | Writes to `config.json.tmp`, then `os.replace` - atomic, so a crash mid-save cannot corrupt the file. |
| `to_dict()` / `restore_snapshot(d)` | Snapshot and roll back. Cancel in the Settings dialog uses this. |
| `export_to(path)` / `import_from(path)` | Back up and restore the whole configuration. |

Saves are debounced by 400 ms, so dragging a spinbox does not hit the disk on
every tick. `save_now()` is called explicitly on exit.

## ConfigScope

A plugin receives `ctx.config`, a scope pinned to `tools.<id>`. It cannot read
or write another tool's keys.

```python
cfg = ctx.config                       # ConfigScope("tools.pdf_merger")
cfg.get("pad_odd")                     # schema default applied automatically
cfg.set("pad_odd", False)
cfg.reset("pad_odd")
cfg.changed.connect(self.on_setting_changed)   # emits the relative key
```

## Field types

Declared in `core/fields.py`, rendered by `ui/settings_dialog.py`.

| Field | Widget | Extra arguments |
| --- | --- | --- |
| `BoolField` | `QCheckBox` | |
| `IntField` | `QSpinBox` | `minimum`, `maximum`, `step`, `suffix` |
| `TextField` | `QLineEdit` | `placeholder` |
| `ChoiceField` | `QComboBox` | `choices=[(label, value), ...]` |
| `MultiChoiceField` | checkbox group | `choices=[(label, value), ...]` |
| `PathField` | line edit + Browse | `mode="file" \| "dir" \| "save"`, `filter` |
| `ActionField` | `QPushButton` | `callback(ctx)` - a command, not a value |

Every field also accepts:

* `help` - a grey hint line under the control
* `hidden=True` - persisted but not shown in Settings (last used folder, etc.)
* `depends_on="other_key"` - greyed out while that checkbox is off

### Adding a field type

1. Add a dataclass to `core/fields.py`.
2. Add an `_Editor` subclass in `ui/settings_dialog.py`.
3. Register it in the `_EDITORS` map.

Every tool can use it from then on.

## The Settings dialog

Left: a tree of `Application` plus each category and its tools. Right: the form
for the selected page.

Values apply **immediately** so the open tool reacts live. The dialog snapshots
the configuration when it opens, and **Cancel** rolls that snapshot back.
**Reset This Page** clears the stored values on the current page only.

## Migrations

When a stored key has to change shape, bump `CONFIG_VERSION` in
`core/config.py` and add one step:

```python
CONFIG_VERSION = 2

def _v1_to_v2(data: dict) -> dict:
    tools = data.setdefault("tools", {})
    merger = tools.setdefault("pdf_merger", {})
    if "pad" in merger:                      # renamed pad -> pad_odd
        merger["pad_odd"] = merger.pop("pad")
    return data

MIGRATIONS = {1: _v1_to_v2}
```

Steps run in order until the file reaches `CONFIG_VERSION`, and the file is
copied to `config.json.bak.v1` before each step. Without this, renaming a key
means throwing away the user's settings.
