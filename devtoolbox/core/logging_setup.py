# -*- coding: utf-8 -*-
"""Rotating file log plus a console handler whose level is a user setting."""
from __future__ import annotations

import logging
import logging.handlers

from . import paths

_FORMAT = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"


def setup(level: str = "INFO") -> logging.Logger:
    paths.ensure_dirs()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    file_handler = logging.handlers.RotatingFileHandler(
        str(paths.log_dir() / "devtoolbox.log"),
        maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMAT))
    console.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    console.set_name("console")
    root.addHandler(console)

    return logging.getLogger("devtoolbox")


def set_console_level(level: str) -> None:
    for handler in logging.getLogger().handlers:
        if handler.get_name() == "console":
            handler.setLevel(getattr(logging, str(level).upper(), logging.INFO))
