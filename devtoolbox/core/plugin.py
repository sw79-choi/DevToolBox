# -*- coding: utf-8 -*-
"""The contract a tool makes with the core."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from .fields import Field


@dataclass(frozen=True)
class ToolMeta:
    id: str                          # Also the settings namespace key. Must be unique
    title: str                       # Label on the tool tab
    category: str = "General"        # Top-level tab this tool lives under
    order: int = 100                 # Tool order; a category inherits its lowest value
    description: str = ""            # Tooltip and Settings subtitle
    icon: Optional[str] = None


class ToolPlugin(ABC):
    """Base class for every tool.

    Only `meta` and `create_widget()` are required.
    """

    meta: ToolMeta

    def settings_schema(self) -> List[Field]:
        """Settings this tool owns. The core builds the UI and defaults from it."""
        return []

    @abstractmethod
    def create_widget(self, ctx):
        """Called once, the first time the tab becomes visible (lazy build)."""

    def on_close(self) -> bool:
        """Called before the app quits. Return False to veto the shutdown."""
        return True
