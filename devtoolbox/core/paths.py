# -*- coding: utf-8 -*-
"""Config and log locations. No Qt dependency, so this is unit-testable."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "DevToolBox"


def app_dir() -> Path:
    """Folder of the executable (frozen) or the project root (source run)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _portable_config() -> Path:
    return app_dir() / "config.json"


def is_portable() -> bool:
    """A config.json next to the app switches on portable mode."""
    return _portable_config().exists()


def user_config_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME


def config_file() -> Path:
    return _portable_config() if is_portable() else user_config_dir() / "config.json"


def log_dir() -> Path:
    base = app_dir() if is_portable() else user_config_dir()
    return base / "logs"


def ensure_dirs() -> None:
    config_file().parent.mkdir(parents=True, exist_ok=True)
    log_dir().mkdir(parents=True, exist_ok=True)


def open_in_file_manager(path) -> None:
    """Reveal a folder in Explorer / Finder / the desktop file manager."""
    target = Path(path)
    target = str(target if target.is_dir() else target.parent)
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
    except Exception:
        pass
