# -*- coding: utf-8 -*-
"""Pure logic of the remaining tools."""
import pytest

from devtoolbox.tools.base64_tool.logic import decode, encode
from devtoolbox.tools.hash_tool.logic import hash_file, hash_text
from devtoolbox.tools.json_formatter.logic import format_json, minify_json, validate


def test_json_round_trip():
    text = '{"b":1,"a":[1,2]}'
    assert minify_json(format_json(text)) == '{"b":1,"a":[1,2]}'
    assert minify_json(text, sort_keys=True) == '{"a":[1,2],"b":1}'


def test_json_keeps_non_ascii_readable():
    assert "한글" in format_json('{"k":"한글"}', ensure_ascii=False)
    assert "\\u" in format_json('{"k":"한글"}', ensure_ascii=True)


def test_json_validate_reports_location():
    ok, message = validate("{")
    assert not ok and "Line 1" in message
    ok, message = validate('{"a":1}')
    assert ok and "dict" in message


def test_hash_text_known_digest():
    digests = hash_text("abc", ["md5", "sha256"])
    assert digests["md5"] == "900150983cd24fb0d6963f7d28e17f72"
    assert digests["sha256"].startswith("ba7816bf")


def test_hash_file_matches_hash_text(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("abc", encoding="utf-8")
    assert hash_file(str(path), ["sha256"]) == hash_text("abc", ["sha256"])


def test_hash_file_cancellation(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("abc", encoding="utf-8")
    assert hash_file(str(path), ["md5"], should_cancel=lambda: True) == {}


@pytest.mark.parametrize("url_safe", [False, True])
def test_base64_round_trip(url_safe):
    text = "DevToolBox 한글 ?>?>"
    assert decode(encode(text, url_safe=url_safe), url_safe=url_safe) == text


def test_base64_tolerates_missing_padding():
    assert decode("YWJj") == "abc"
    assert decode("YWJj\n") == "abc"
