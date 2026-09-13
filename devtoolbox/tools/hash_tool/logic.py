# -*- coding: utf-8 -*-
"""Hashing. Pure Python, no Qt."""
from __future__ import annotations

import hashlib
import os
from typing import Callable, Dict, Optional, Sequence

ALGORITHMS = ("md5", "sha1", "sha256", "sha512")
_CHUNK = 1024 * 1024


def hash_text(text: str, algorithms: Sequence[str] = ALGORITHMS,
              encoding: str = "utf-8") -> Dict[str, str]:
    data = text.encode(encoding)
    return {name: hashlib.new(name, data).hexdigest() for name in algorithms}


def hash_file(path: str, algorithms: Sequence[str] = ALGORITHMS,
              progress: Optional[Callable[[int], None]] = None,
              should_cancel: Optional[Callable[[], bool]] = None) -> Dict[str, str]:
    """Stream the file once and feed every requested digest."""
    digests = {name: hashlib.new(name) for name in algorithms}
    total = max(os.path.getsize(path), 1)
    read = 0
    with open(path, "rb") as handle:
        while True:
            if should_cancel and should_cancel():
                return {}
            chunk = handle.read(_CHUNK)
            if not chunk:
                break
            for digest in digests.values():
                digest.update(chunk)
            read += len(chunk)
            if progress:
                progress(min(int(read * 100 / total), 100))
    return {name: digest.hexdigest() for name, digest in digests.items()}
