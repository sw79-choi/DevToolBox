# -*- coding: utf-8 -*-
"""PDF merging. Pure Python: no Qt here, so it is testable and reusable from a CLI.

The runner injects `progress` / `should_cancel` when they are declared, which is
how this module reports progress without knowing that Qt exists.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from pypdf import PdfReader, PdfWriter

# A4 in PostScript points, used when the blank page size is pinned to A4.
A4_WIDTH_PT = 595.276
A4_HEIGHT_PT = 841.890


@dataclass
class MergeOptions:
    pad_odd: bool = True          # append a blank page after odd-length documents
    pad_size: str = "last"        # last | first | a4
    bookmarks: bool = True        # one outline entry per source document


@dataclass
class MergeResult:
    output_path: str
    files: int = 0
    content_pages: int = 0
    blank_pages: int = 0
    skipped: List[Tuple[str, str]] = field(default_factory=list)
    cancelled: bool = False

    @property
    def total_pages(self) -> int:
        return self.content_pages + self.blank_pages


def open_reader(path: str) -> PdfReader:
    """Open a PDF, transparently handling the empty-password case."""
    reader = PdfReader(path)
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as exc:
            raise RuntimeError("password protected") from exc
    return reader


def read_page_count(path: str) -> int:
    return len(open_reader(path).pages)


def page_size(page) -> Tuple[float, float]:
    try:
        box = page.mediabox
        return float(box.width), float(box.height)
    except Exception:
        return A4_WIDTH_PT, A4_HEIGHT_PT


def merge_pdfs(
    paths: Sequence[str],
    output_path: str,
    options: MergeOptions,
    progress: Optional[Callable[[int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
    message: Optional[Callable[[str], None]] = None,
) -> MergeResult:
    """Concatenate `paths` into `output_path`.

    With options.pad_odd on, a blank page follows every document that has an odd
    page count, so duplex printing keeps each document starting on a front side.
    """
    result = MergeResult(output_path=output_path)
    writer = PdfWriter()
    total = max(len(paths), 1)
    cursor = 0                      # page index inside the merged document

    for index, path in enumerate(paths):
        if should_cancel and should_cancel():
            result.cancelled = True
            return result
        name = os.path.basename(path)
        if message:
            message("Merging %s" % name)
        if progress:
            progress(int(index * 95 / total))

        try:
            reader = open_reader(path)
            pages = reader.pages
            if len(pages) == 0:
                result.skipped.append((name, "no pages"))
                continue

            if options.bookmarks:
                title = os.path.splitext(name)[0]
                try:
                    writer.add_outline_item(title, cursor)
                except AttributeError:          # pypdf < 3 spelling
                    writer.add_bookmark(title, cursor)

            first_size = page_size(pages[0])
            last_size = first_size
            for page in pages:
                writer.add_page(page)
                last_size = page_size(page)
            cursor += len(pages)
            result.files += 1
            result.content_pages += len(pages)

            if options.pad_odd and len(pages) % 2 == 1:
                if options.pad_size == "a4":
                    width, height = A4_WIDTH_PT, A4_HEIGHT_PT
                elif options.pad_size == "first":
                    width, height = first_size
                else:
                    width, height = last_size
                writer.add_blank_page(width=width, height=height)
                cursor += 1
                result.blank_pages += 1

        except Exception as exc:
            result.skipped.append((name, str(exc) or exc.__class__.__name__))

    if result.files == 0:
        raise RuntimeError("None of the selected files could be merged.")

    if progress:
        progress(96)
    if message:
        message("Writing %s" % os.path.basename(output_path))

    temp_path = output_path + ".part"
    with open(temp_path, "wb") as handle:
        writer.write(handle)
    if os.path.exists(output_path):
        os.remove(output_path)
    os.replace(temp_path, output_path)

    if progress:
        progress(100)
    return result


def natural_key(text: str):
    """Sort helper so file2 comes before file10."""
    import re
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", text)]
