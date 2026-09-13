# -*- coding: utf-8 -*-
"""The merge logic is pure Python, so it tests without a GUI."""
import pytest
from pypdf import PdfReader, PdfWriter

from devtoolbox.tools.pdf_merger.logic import (MergeOptions, merge_pdfs,
                                               natural_key, read_page_count)


def make_pdf(path, page_count, seed=0):
    writer = PdfWriter()
    for i in range(page_count):
        # Unique page sizes keep pypdf from de-duplicating identical objects.
        writer.add_blank_page(width=595 + seed + i, height=842 + seed + i)
    with open(path, "wb") as handle:
        writer.write(handle)
    return str(path)


@pytest.fixture
def sources(tmp_path):
    counts = [3, 4, 1, 6, 5]
    return [make_pdf(tmp_path / ("doc%d.pdf" % i), n, seed=i * 10)
            for i, n in enumerate(counts)]


def test_page_counts_are_read(sources):
    assert [read_page_count(p) for p in sources] == [3, 4, 1, 6, 5]


def test_padding_makes_every_document_start_on_a_front_side(sources, tmp_path):
    out = str(tmp_path / "merged.pdf")
    result = merge_pdfs(sources, out, MergeOptions(pad_odd=True))
    assert result.content_pages == 19
    assert result.blank_pages == 3          # the 3, 1 and 5 page documents
    assert result.total_pages == 22

    reader = PdfReader(out)
    assert len(reader.pages) == 22
    starts = [int(item.get("/Page")) for item in reader.outline]
    assert starts == [0, 4, 8, 10, 16]
    assert all(start % 2 == 0 for start in starts)


def test_without_padding_pages_are_untouched(sources, tmp_path):
    out = str(tmp_path / "merged.pdf")
    result = merge_pdfs(sources, out, MergeOptions(pad_odd=False))
    assert result.blank_pages == 0
    assert len(PdfReader(out).pages) == 19


def test_bookmarks_can_be_turned_off(sources, tmp_path):
    out = str(tmp_path / "merged.pdf")
    merge_pdfs(sources, out, MergeOptions(bookmarks=False))
    assert list(PdfReader(out).outline) == []


def test_cancellation_writes_nothing(sources, tmp_path):
    out = tmp_path / "merged.pdf"
    result = merge_pdfs(sources, str(out), MergeOptions(), should_cancel=lambda: True)
    assert result.cancelled
    assert not out.exists()


def test_unreadable_file_is_skipped(sources, tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf at all")
    out = str(tmp_path / "merged.pdf")
    result = merge_pdfs(sources[:2] + [str(broken)], out, MergeOptions())
    assert result.files == 2
    assert len(result.skipped) == 1


def test_all_inputs_unreadable_raises(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"nope")
    with pytest.raises(RuntimeError):
        merge_pdfs([str(broken)], str(tmp_path / "out.pdf"), MergeOptions())


def test_natural_sort_order():
    names = ["file10.pdf", "file2.pdf", "file1.pdf"]
    assert sorted(names, key=natural_key) == ["file1.pdf", "file2.pdf", "file10.pdf"]
