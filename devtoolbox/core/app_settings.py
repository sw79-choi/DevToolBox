# -*- coding: utf-8 -*-
"""Application-wide settings that belong to no single tool."""
from __future__ import annotations

from .fields import BoolField, ChoiceField

APP_NS = "app"

APP_SCHEMA = [
    ChoiceField(
        "theme", "Theme", default="system",
        choices=[("Follow system", "system"), ("Light", "light"), ("Dark", "dark")],
        help="Applied immediately.",
    ),
    BoolField(
        "restore_last_tab", "Reopen the last used tab on startup", default=True,
    ),
    ChoiceField(
        "log_level", "Console log level", default="INFO",
        choices=[("WARNING", "WARNING"), ("INFO", "INFO"), ("DEBUG", "DEBUG")],
    ),
    ChoiceField("last_tab", "", default="", hidden=True),
]
