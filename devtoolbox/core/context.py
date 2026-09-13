# -*- coding: utf-8 -*-
"""The single channel through which a tool reaches the core."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .config import ConfigScope
from .tasks import TaskRunner


def _noop_notify(message: str, msec: int = 4000) -> None:
    pass


@dataclass
class AppContext:
    config: ConfigScope                          # This tool's own settings
    app_config: ConfigScope                      # App-wide settings (read mostly)
    tasks: TaskRunner                            # Shared background runner
    log: logging.Logger                          # Logger named after the tool
    notify: Callable[..., None] = _noop_notify   # Status bar message
    main_window: Optional[Any] = None
    extras: dict = field(default_factory=dict)
