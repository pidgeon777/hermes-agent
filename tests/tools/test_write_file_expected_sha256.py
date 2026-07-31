from __future__ import annotations

import hashlib
import json


def _hash(text: str) -> str:
    return hashlib.sha256("\n".join(text.splitlines()).encode("utf-8")).hexdigest()


def test_write_file_expected_sha256_allows_matching_target(tmp_path):
    from tools.file_tools import write_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    result = json.loads(write_file_tool(
        path=str(target),
        content="replacement\n",
        expected_sha256=_hash("alpha\nbeta"),
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "replacement\n"


def test_write_file_expected_sha256_blocks_stale_target(tmp_path):
    from tools.file_tools import write_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    result = json.loads(write_file_tool(
        path=str(target),
        content="replacement\n",
        expected_sha256=_hash("stale"),
    ))

    assert "STALE_CONTEXT" in result["error"]
    assert result["actual_sha256"] == _hash("alpha\nbeta")
    assert target.read_text(encoding="utf-8") == "alpha\nbeta\n"


def test_write_file_expected_sha256_requires_existing_target(tmp_path):
    from tools.file_tools import write_file_tool

    target = tmp_path / "missing.txt"
    result = json.loads(write_file_tool(
        path=str(target),
        content="new\n",
        expected_sha256=_hash("anything"),
    ))

    assert "requires an existing target" in result["error"]
    assert not target.exists()


def test_write_file_tool_treats_empty_expected_sha256_as_omitted(tmp_path):
    from tools.file_tools import write_file_tool

    target = tmp_path / "new-direct-empty-precondition.txt"
    result = json.loads(write_file_tool(
        path=str(target),
        content="new\n",
        expected_sha256="",
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_file_handler_treats_empty_expected_sha256_as_omitted(tmp_path):
    from tools.file_tools import _handle_write_file

    target = tmp_path / "new-empty-precondition.txt"
    result = json.loads(_handle_write_file({
        "path": str(target),
        "content": "new\n",
        "expected_sha256": "",
    }))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_file_handler_treats_whitespace_expected_sha256_as_omitted(tmp_path):
    from tools.file_tools import _handle_write_file

    target = tmp_path / "new-whitespace-precondition.txt"
    result = json.loads(_handle_write_file({
        "path": str(target),
        "content": "new\n",
        "expected_sha256": "   ",
    }))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_file_schema_keeps_sha256_precondition_internal():
    from tools.file_tools import WRITE_FILE_SCHEMA

    properties = WRITE_FILE_SCHEMA["parameters"]["properties"]
    assert "expected_sha256" not in properties
    assert "expected_revision" not in properties