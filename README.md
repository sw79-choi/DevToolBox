# DevToolBox

A PyQt desktop app that collects small developer utilities under one window.
Tools are grouped into **category tabs**; each tool is a **single folder** that the
app discovers on startup, and every setting from every tool lives in **one
`config.json`**.

```
Document   -> PDF Merger
Text       -> JSON Formatter
Encoding   -> Hash | Base64
```

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

On Windows you can double-click `run.bat`, which installs the dependencies the
first time and then launches the app.

Requires Python 3.9 or newer. PyQt6 is the default binding; PyQt5 also works
because `devtoolbox/core/qt.py` absorbs the differences.

## Adding a tool

Create a folder under `devtoolbox/tools/`, then put `TOOL = MyTool()` in its
`__init__.py`. No existing file needs to change. The full walkthrough is in
[docs/ADDING_A_TOOL.md](docs/ADDING_A_TOOL.md).

## Layout

```
main.py                     Entry point: boot order only
devtoolbox/
  core/                     Knows nothing about any specific tool
    qt.py                   The only module that imports PyQt
    paths.py                Config and log locations, portable mode
    fields.py               Setting types (BoolField, ChoiceField, ...)
    plugin.py               ToolMeta, ToolPlugin - the contract
    registry.py             Discovery, error isolation
    config.py               ConfigManager, ConfigScope
    tasks.py                TaskRunner (QThreadPool wrapper)
    context.py              AppContext handed to each tool
    app_settings.py         App-wide settings schema
    logging_setup.py
  ui/                       The shell
    main_window.py          Category tabs -> tool tabs, lazy build
    settings_dialog.py      Schema -> widgets
    theme.py
    widgets/                Reusable widgets shared by tools
  tools/                    One folder per tool
    pdf_merger/             Document
    json_formatter/         Text
    hash_tool/              Encoding
    base64_tool/            Encoding
tests/                      Pure-logic tests, no GUI needed
docs/                       Reference notes - read these before extending
```

## Tests

```bash
pip install pytest
python -m pytest tests -q
```

## Documentation

| File | What it covers |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layers, boot order, the plugin contract, background tasks |
| [docs/ADDING_A_TOOL.md](docs/ADDING_A_TOOL.md) | Step-by-step guide with a complete example |
| [docs/CONFIG.md](docs/CONFIG.md) | ConfigManager API, file layout, field types, migrations |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why things are built this way, and what the alternatives were |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Known gaps and ideas for later |
