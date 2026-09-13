# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.fields import BoolField, ChoiceField, PathField
from ...core.plugin import ToolMeta, ToolPlugin


class StreamingToMp3Tool(ToolPlugin):
    meta = ToolMeta(
        id="streaming_to_mp3",
        title="StreamingToMp3",
        category="Sound",
        order=40,
        description="Record the PC's system audio output (loopback) straight to an MP3 file.",
    )

    def __init__(self):
        self._widget = None

    def settings_schema(self):
        return [
            ChoiceField(
                "bitrate", "Default bitrate", default=192,
                choices=[("128 kbps", 128), ("192 kbps", 192),
                         ("256 kbps", 256), ("320 kbps", 320)],
            ),
            BoolField("open_when_done", "Reveal the file when recording stops", default=True),
            PathField("last_dir", "Last used folder", mode="dir", default="", hidden=True),
        ]

    def create_widget(self, ctx):
        from .widget import StreamingToMp3Widget      # late import keeps startup fast
        self._widget = StreamingToMp3Widget(ctx)
        return self._widget

    def on_close(self) -> bool:
        return not (self._widget and self._widget.is_busy())
