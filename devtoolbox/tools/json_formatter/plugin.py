# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.fields import BoolField, IntField
from ...core.plugin import ToolMeta, ToolPlugin


class JsonFormatterTool(ToolPlugin):
    meta = ToolMeta(
        id="json_formatter",
        title="JSON Formatter",
        category="Text",
        order=20,
        description="Pretty-print, minify and validate JSON.",
    )

    def settings_schema(self):
        return [
            IntField("indent", "Indent width", default=2, minimum=0, maximum=8,
                     suffix="spaces"),
            BoolField("sort_keys", "Sort object keys", default=False),
            BoolField("ensure_ascii", "Escape non-ASCII characters", default=False,
                      help="Off keeps text such as Korean readable in the output."),
        ]

    def create_widget(self, ctx):
        from .widget import JsonFormatterWidget
        return JsonFormatterWidget(ctx)
