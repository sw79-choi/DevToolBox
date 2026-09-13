# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.fields import BoolField, ChoiceField
from ...core.plugin import ToolMeta, ToolPlugin


class Base64Tool(ToolPlugin):
    meta = ToolMeta(
        id="base64_tool",
        title="Base64",
        category="Encoding",
        order=31,
        description="Encode and decode Base64 text.",
    )

    def settings_schema(self):
        return [
            BoolField("url_safe", "Use the URL-safe alphabet (-_)", default=False),
            ChoiceField("encoding", "Text encoding", default="utf-8",
                        choices=[("UTF-8", "utf-8"), ("CP949", "cp949"),
                                 ("Latin-1", "latin-1")]),
        ]

    def create_widget(self, ctx):
        from .widget import Base64Widget
        return Base64Widget(ctx)
