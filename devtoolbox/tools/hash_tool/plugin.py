# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.fields import BoolField, MultiChoiceField, PathField
from ...core.plugin import ToolMeta, ToolPlugin
from .logic import ALGORITHMS


class HashTool(ToolPlugin):
    meta = ToolMeta(
        id="hash_tool",
        title="Hash",
        category="Encoding",
        order=30,
        description="Checksums for text and for files, computed off the UI thread.",
    )

    def __init__(self):
        self._widget = None

    def settings_schema(self):
        return [
            MultiChoiceField(
                "algorithms", "Algorithms", default=["md5", "sha1", "sha256"],
                choices=[(name.upper(), name) for name in ALGORITHMS],
            ),
            BoolField("uppercase", "Show digests in uppercase", default=False),
            PathField("last_dir", "Last used folder", mode="dir", default="", hidden=True),
        ]

    def create_widget(self, ctx):
        from .widget import HashWidget
        self._widget = HashWidget(ctx)
        return self._widget

    def on_close(self) -> bool:
        return not (self._widget and self._widget.is_busy())
