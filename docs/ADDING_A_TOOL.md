# Adding a tool

Five steps. None of them edits an existing file.

## 1. Create the folder

```
devtoolbox/tools/my_tool/
    __init__.py
    plugin.py
    logic.py
    widget.py
```

## 2. `logic.py` - the work, with no Qt

Keep this importable on its own so it can be tested and reused.

```python
# -*- coding: utf-8 -*-
"""What this tool actually does. Pure Python, no Qt."""
from __future__ import annotations


def slugify(text: str, separator: str = "-") -> str:
    parts = [p for p in text.lower().split() if p]
    return separator.join(parts)
```

If the work is slow, declare any of `progress`, `should_cancel` or `message`
and the task runner will inject them:

```python
def convert_all(paths, progress=None, should_cancel=None):
    for index, path in enumerate(paths):
        if should_cancel and should_cancel():
            return None
        ...
        if progress:
            progress(int(index * 100 / len(paths)))
```

## 3. `plugin.py` - metadata and settings

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.fields import BoolField, ChoiceField
from ...core.plugin import ToolMeta, ToolPlugin


class MyTool(ToolPlugin):
    meta = ToolMeta(
        id="my_tool",              # settings namespace; must be unique
        title="My Tool",           # tool tab label
        category="Text",           # top-level tab; a new name creates a new one
        order=40,                  # position among tools, and of the category
        description="One line shown as a tooltip and in Settings.",
    )

    def settings_schema(self):
        return [
            BoolField("trim", "Trim surrounding whitespace", default=True),
            ChoiceField("separator", "Word separator", default="-",
                        choices=[("Hyphen", "-"), ("Underscore", "_")],
                        depends_on="trim"),
        ]

    def create_widget(self, ctx):
        from .widget import MyToolWidget     # late import keeps startup fast
        return MyToolWidget(ctx)
```

## 4. `widget.py` - the screen

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.qt import QtWidgets          # never import PyQt directly
from .logic import slugify


class MyToolWidget(QtWidgets.QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cfg = ctx.config              # scoped to tools.my_tool

        layout = QtWidgets.QVBoxLayout(self)
        self.input = QtWidgets.QLineEdit("Hello DevToolBox")
        self.output = QtWidgets.QLineEdit(readOnly=True)
        run = QtWidgets.QPushButton("Convert")
        run.clicked.connect(self.on_run)
        layout.addWidget(self.input)
        layout.addWidget(run)
        layout.addWidget(self.output)

        self.cfg.changed.connect(self.on_setting_changed)

    def on_run(self):
        text = self.input.text()
        if self.cfg.get("trim"):
            text = text.strip()
        self.output.setText(slugify(text, self.cfg.get("separator")))
        self.ctx.notify("Converted")

    def on_setting_changed(self, key, value):
        """Called when the Settings dialog changes one of our keys."""
        self.on_run()
```

## 5. `__init__.py` - the registration point

```python
# -*- coding: utf-8 -*-
"""My Tool."""
from .plugin import MyTool

TOOL = MyTool()
```

Restart the app. The tab is there, and the Settings dialog has a **My Tool**
page under **Text**.

## Checklist

- [ ] `meta.id` is unique and matches the folder name
- [ ] Setting keys are unique within the tool
- [ ] No `from PyQt6 import ...` outside `core/qt.py`
- [ ] Slow work goes through `ctx.tasks.submit(...)`, not the UI thread
- [ ] Buttons, labels and comments are written in English
- [ ] Business logic sits in `logic.py` with a test in `tests/`
- [ ] `on_close()` returns False while a long task is still running

## Conventions

**Categories in use:** `Document`, `Text`, `Encoding`. Adding a tool with a new
category string creates a new top-level tab automatically.

**Order ranges** so categories stay grouped:

| Range | Category |
| --- | --- |
| 10-19 | Document |
| 20-29 | Text |
| 30-39 | Encoding |
| 100+ | Uncategorised / General |

**Persisting things the user should not see** (last folder, window splitter
sizes): declare the field with `hidden=True`. It is stored and restored like any
other setting but never appears in the Settings dialog.
