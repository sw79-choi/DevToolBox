# Design decisions

Why things are the way they are, and what was considered instead. Each of these
is reversible; the point is to record the reasoning.

## Plugin registration: folder scan

**Chosen:** `pkgutil.iter_modules` over `devtoolbox/tools/`, each package
exposing `TOOL`.
**Alternatives:** setuptools entry points; a hand-maintained list.
**Why:** this is a single application, not a plugin marketplace. Scanning means
adding a tool never edits an existing file. Entry points can be added later
without changing the `ToolPlugin` contract.

## Settings store: one JSON file

**Chosen:** a single `config.json`.
**Alternatives:** `QSettings` (the Windows registry), one file per tool, SQLite.
**Why:** human readable, diffable, and it copies to another machine as one file.
The registry is awkward to back up and impossible to hand-edit comfortably.

## Defaults live in schemas, not on disk

**Chosen:** `register_defaults()` keeps defaults in memory; only changed values
are written.
**Alternative:** write the full default set on first run.
**Why:** changing a default later then reaches existing users. A config file
full of defaults also makes it impossible to tell what the user actually set.

## Settings UI is generated

**Chosen:** tools declare `Field` lists; `ui/settings_dialog.py` builds widgets.
**Alternative:** each tool writes its own settings page.
**Why:** every tool's settings look and behave the same, and nobody writes
load/save/restore code twice. The cost is a factory that needs one branch per
field type.

## Immediate apply with snapshot rollback

**Chosen:** changes take effect as you make them; Cancel restores a snapshot.
**Alternative:** buffer changes and commit on OK.
**Why:** the open tool reacts live, which is the useful behaviour for things
like theme. Snapshot rollback keeps Cancel honest.

## Lazy tab construction

**Chosen:** `ToolHost` builds its widget in the first `showEvent`; tool modules
import their widget module late.
**Alternative:** build everything at startup.
**Why:** startup time stays constant as tools are added, and a heavy import
(pypdf, for instance) is deferred until that tab is opened.

## Threads: one shared QThreadPool

**Chosen:** `TaskRunner.submit()` with injected `progress` / `should_cancel`.
**Alternative:** a `QThread` subclass per tool.
**Why:** progress, cancellation and error propagation get implemented correctly
once. Signature injection is what keeps `logic.py` free of Qt.

## Qt behind one module

**Chosen:** `core/qt.py` is the only place that imports PyQt; it normalises the
PyQt6/PyQt5 enum differences.
**Alternative:** import PyQt6 everywhere.
**Why:** PyQt6, PyQt5 and PySide6 differ mostly in enum paths and `exec_`.
Containing that means a binding switch (including a possible move to PySide6 for
licensing reasons) touches one file.

## Logic separated from widgets

**Chosen:** every tool has a Qt-free `logic.py`.
**Alternative:** logic inside the widget class.
**Why:** the logic gets unit tests without a display, and the same function can
be reused from a CLI or a scheduled job later.

## Error isolation over fail-fast

**Chosen:** a tool that fails to import becomes an entry in a `Problems` tab; a
tool that fails to build shows an error page in its own tab.
**Alternative:** let the exception reach the top and refuse to start.
**Why:** while developing a new tool, a typo should not stop you from using the
other tools - and the traceback is right there on screen.

## English-only user interface

**Chosen:** all buttons, labels, messages, comments and docstrings are in
English.
**Why:** the repository is public and the app should be usable by anyone. If
localisation is wanted later, `QTranslator` plus `tr()` wrappers is the path -
it is much easier to add to an English codebase than to a mixed one.
