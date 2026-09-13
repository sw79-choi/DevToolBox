# -*- coding: utf-8 -*-
"""JSON formatting. Pure Python, no Qt."""
from __future__ import annotations

import json
from typing import Any, Tuple


def parse(text: str) -> Any:
    return json.loads(text)


def format_json(text: str, indent: int = 2, sort_keys: bool = False,
                ensure_ascii: bool = False) -> str:
    return json.dumps(parse(text), indent=indent, sort_keys=sort_keys,
                      ensure_ascii=ensure_ascii)


def minify_json(text: str, sort_keys: bool = False,
                ensure_ascii: bool = False) -> str:
    return json.dumps(parse(text), separators=(",", ":"), sort_keys=sort_keys,
                      ensure_ascii=ensure_ascii)


def validate(text: str) -> Tuple[bool, str]:
    """Return (ok, human readable message)."""
    try:
        value = parse(text)
    except json.JSONDecodeError as exc:
        return False, "Line %d, column %d: %s" % (exc.lineno, exc.colno, exc.msg)
    except Exception as exc:
        return False, str(exc)
    kind = type(value).__name__
    size = len(value) if isinstance(value, (list, dict)) else 1
    return True, "Valid JSON (%s, %d item(s))" % (kind, size)
