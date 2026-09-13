# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.fields import BoolField, ChoiceField, PathField
from ...core.plugin import ToolMeta, ToolPlugin


class PdfMergerTool(ToolPlugin):
    meta = ToolMeta(
        id="pdf_merger",
        title="PDF Merger",
        category="Document",
        order=10,
        description="Combine PDFs into one file and keep duplex printing aligned.",
    )

    def __init__(self):
        self._widget = None

    def settings_schema(self):
        return [
            BoolField(
                "pad_odd", "Add a blank page after odd-length documents",
                default=True,
                help="Keeps each document starting on a front side when printing duplex.",
            ),
            ChoiceField(
                "pad_size", "Blank page size", default="last",
                choices=[("Same as the document's last page", "last"),
                         ("Same as the document's first page", "first"),
                         ("Always A4", "a4")],
                depends_on="pad_odd",
            ),
            BoolField("bookmarks", "Create one bookmark per document", default=True),
            BoolField("recursive", "Include subfolders when adding a folder", default=False),
            BoolField("open_when_done", "Reveal the result when the merge finishes",
                      default=True),
            PathField("last_dir", "Last used folder", mode="dir", default="", hidden=True),
        ]

    def create_widget(self, ctx):
        from .widget import PdfMergerWidget      # imported late so startup stays fast
        self._widget = PdfMergerWidget(ctx)
        return self._widget

    def on_close(self) -> bool:
        return not (self._widget and self._widget.is_busy())
