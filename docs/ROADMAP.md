# Roadmap and known gaps

Notes for later. Nothing here is required for the current skeleton to work.

## Known gaps

* **No toolbar or icons.** `ToolMeta.icon` is defined but unused. Wiring it up
  means adding a `resources/` lookup in `MainWindow._build_tabs`.
* **Theme is minimal.** `ui/theme.py` only swaps a Fusion palette. "Follow
  system" does not actually detect the OS theme; it just uses the style default.
* **No translations.** See the decision note in `docs/DECISIONS.md`.
* **`ActionField` is unused** by any shipped tool. It works, but it has not been
  exercised in anger - useful for things like "Clear cache".
* **No packaging yet.** See below.

## Packaging

PyInstaller in `onedir` mode is the intended route:

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name DevToolBox ^
            --add-data "devtoolbox/tools;devtoolbox/tools" main.py
```

Two things to watch:

1. **Hidden imports.** Tools are discovered with `pkgutil`, so PyInstaller
   cannot see them statically. Either list each tool package under
   `--hidden-import` or add a hook that collects `devtoolbox.tools.*`.
2. **Portable mode.** Dropping an empty `config.json` next to the produced
   `DevToolBox.exe` makes it store settings beside the executable.

`onedir` is preferred over `onefile`: it starts faster and works with portable
mode, since `onefile` unpacks to a temp folder on every launch.

## Tool ideas

Reasonable next tools, with the category each would land in:

| Tool | Category | Note |
| --- | --- | --- |
| PDF split / extract pages | Document | Reuses `pdf_merger/logic.py` helpers |
| PDF page rotate, watermark | Document | |
| Image batch convert / resize | Image | New category; Pillow |
| Bulk file rename | File | Regex preview before applying |
| Regex tester | Text | Live match highlighting |
| Diff viewer | Text | `difflib` plus a side-by-side view |
| Timestamp / epoch converter | Encoding | |
| URL encode / decode, JWT decode | Encoding | Sits next to Base64 |
| QR code generator | Encoding | |

## Possible core improvements

* **Per-tool state beyond settings.** Right now anything persistent is a
  `hidden=True` field. A `ctx.state` store (same file, `state.<id>.*`) would
  separate "user preferences" from "remembered UI state" more honestly.
* **Recent files service** shared through `AppContext`, since several tools
  would want one.
* **Status bar task indicator** showing `TaskRunner.active_count`, so long jobs
  are visible even after switching tabs.
* **Keyboard shortcuts per tool**, declared in `ToolMeta` and registered by the
  shell.
* **Search across tools** - a Ctrl+K palette that jumps to a tab.
