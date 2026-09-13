# -*- coding: utf-8 -*-
"""Scans tools/ for plugins. One broken tool must not stop the whole app."""
from __future__ import annotations

import importlib
import logging
import pkgutil
import traceback
from dataclasses import dataclass
from typing import List, Tuple

from .plugin import ToolPlugin

log = logging.getLogger(__name__)

DEFAULT_PACKAGE = "devtoolbox.tools"


@dataclass
class LoadError:
    module: str
    message: str
    traceback: str


def discover(package: str = DEFAULT_PACKAGE) -> Tuple[List[ToolPlugin], List[LoadError]]:
    """Import every sub-package of `package` and collect its TOOL object."""
    plugins: List[ToolPlugin] = []
    errors: List[LoadError] = []
    seen_ids = set()

    pkg = importlib.import_module(package)
    for info in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if info.name.startswith("_"):
            continue
        module_name = "%s.%s" % (package, info.name)
        try:
            module = importlib.import_module(module_name)
            tool = getattr(module, "TOOL", None)
            if tool is None:
                raise AttributeError("module does not define TOOL")
            if not isinstance(tool, ToolPlugin):
                raise TypeError("TOOL is not a ToolPlugin instance")
            if tool.meta.id in seen_ids:
                raise ValueError("duplicate tool id: %s" % tool.meta.id)
            seen_ids.add(tool.meta.id)
            plugins.append(tool)
            log.debug("Loaded tool %s (%s)", tool.meta.id, tool.meta.category)
        except Exception as exc:
            log.exception("Failed to load tool: %s", module_name)
            errors.append(LoadError(info.name, str(exc) or exc.__class__.__name__,
                                    traceback.format_exc()))

    # Categories inherit the lowest order of their tools, so sort by order only.
    plugins.sort(key=lambda p: (p.meta.order, p.meta.title))
    return plugins, errors
