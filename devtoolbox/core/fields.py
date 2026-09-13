# -*- coding: utf-8 -*-
"""Declarative setting types.

A tool declares this list and nothing else; widget creation, persistence and
change notification are the core's job. To add a new input type, add a
dataclass here and one branch to the factory in ui/settings_dialog.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dc_field
from typing import Any, Callable, Optional, Sequence, Tuple


@dataclass
class Field:
    key: str
    label: str
    default: Any = None
    help: str = ""
    hidden: bool = False                 # Not shown in Settings, still persisted
    depends_on: Optional[str] = None     # Enabled only while that key is truthy


@dataclass
class BoolField(Field):
    default: bool = False


@dataclass
class IntField(Field):
    default: int = 0
    minimum: int = 0
    maximum: int = 999999
    step: int = 1
    suffix: str = ""


@dataclass
class TextField(Field):
    default: str = ""
    placeholder: str = ""


@dataclass
class ChoiceField(Field):
    default: Any = None
    choices: Sequence[Tuple[str, Any]] = ()


@dataclass
class MultiChoiceField(Field):
    default: list = _dc_field(default_factory=list)
    choices: Sequence[Tuple[str, Any]] = ()


@dataclass
class PathField(Field):
    default: str = ""
    mode: str = "dir"                    # file | dir | save
    filter: str = "All files (*.*)"


@dataclass
class ActionField(Field):
    """A button rather than a value. Calls callback(ctx)."""
    callback: Optional[Callable] = None
