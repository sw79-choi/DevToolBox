# -*- coding: utf-8 -*-
"""Base64 encoding and decoding. Pure Python, no Qt."""
from __future__ import annotations

import base64


def encode(text: str, url_safe: bool = False, encoding: str = "utf-8") -> str:
    raw = text.encode(encoding)
    data = base64.urlsafe_b64encode(raw) if url_safe else base64.b64encode(raw)
    return data.decode("ascii")


def decode(text: str, url_safe: bool = False, encoding: str = "utf-8") -> str:
    cleaned = "".join(text.split())
    padding = "=" * (-len(cleaned) % 4)          # tolerate stripped padding
    raw = cleaned + padding
    data = (base64.urlsafe_b64decode(raw) if url_safe else base64.b64decode(raw))
    return data.decode(encoding)
