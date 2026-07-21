from __future__ import annotations

import json


def test_read_file_returns_canonical_revision_token_for_complete_file(tmp_path):
    from tools.file_tools import read_file_tool

    target = tmp_path / "sample.txt"
    target.write_bytes(b"\xef\xbb\xbfalpha\r\nbeta\r\n")

    result = json.loads(read_file_tool(str(target), task_id="revision-complete"))

    assert result["revision"]["algorithm"] == "sha256"
    assert result["revision"]["canonicalization"] == "utf8-sig+logical-lf"
    assert result["revision"]["scope"] == "file"
    assert result["revision"]["complete"] is True
    assert len(result["revision"]["token"]) == 64


def test_read_file_returns_range_revision_for_partial_read(tmp_path):
    from tools.file_tools import read_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\ntwo\nthree\n", encoding="utf-8")
    result = json.loads(read_file_tool(
        str(target), offset=2, limit=1, task_id="revision-range"
    ))

    revision = result["revision"]
    assert revision["scope"] == "range"
    assert revision["start_line"] == 2
    assert revision["end_line"] == 2
    assert revision["complete"] is True


def test_patch_accepts_revision_token_without_raw_hash_argument(tmp_path):
    from tools.file_tools import patch_tool, read_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\ntwo\nthree\n", encoding="utf-8")
    read = json.loads(read_file_tool(
        str(target), offset=2, limit=1, task_id="revision-patch"
    ))
    result = json.loads(patch_tool(
        mode="replace", path=str(target), old_string="two", new_string="TWO",
        expected_revision=read["revision"], task_id="revision-patch",
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "one\nTWO\nthree\n"


def test_revision_token_fails_closed_when_file_changed(tmp_path):
    from tools.file_tools import patch_tool, read_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\ntwo\n", encoding="utf-8")
    read = json.loads(read_file_tool(str(target), task_id="revision-stale"))
    target.write_text("one\nchanged\n", encoding="utf-8")
    result = json.loads(patch_tool(
        mode="replace", path=str(target), old_string="changed", new_string="CHANGED",
        expected_revision=read["revision"], task_id="revision-stale",
    ))

    assert "STALE_CONTEXT" in result["error"]
    assert target.read_text(encoding="utf-8") == "one\nchanged\n"


def test_write_file_accepts_complete_file_revision(tmp_path):
    from tools.file_tools import read_file_tool, write_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("old\n", encoding="utf-8")
    read = json.loads(read_file_tool(str(target), task_id="revision-write"))
    result = json.loads(write_file_tool(
        str(target), "new\n", expected_revision=read["revision"],
        task_id="revision-write",
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_file_rejects_range_revision(tmp_path):
    from tools.file_tools import read_file_tool, write_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\ntwo\n", encoding="utf-8")
    read = json.loads(read_file_tool(
        str(target), offset=1, limit=1, task_id="revision-write-range"
    ))
    result = json.loads(write_file_tool(
        str(target), "new\n", expected_revision=read["revision"],
        task_id="revision-write-range",
    ))

    assert "complete-file revision" in result["error"]
    assert target.read_text(encoding="utf-8") == "one\ntwo\n"


def test_revision_is_omitted_when_redaction_changes_returned_content(tmp_path, monkeypatch):
    import tools.file_tools as file_tools

    target = tmp_path / "sample.txt"
    target.write_text("secret\n", encoding="utf-8")
    monkeypatch.setattr(file_tools, "redact_sensitive_text", lambda text, **_: "[REDACTED]")
    result = json.loads(file_tools.read_file_tool(
        str(target), task_id="revision-redacted"
    ))

    assert "revision" not in result
    assert "revision_omitted" in result


def test_schemas_expose_expected_revision_and_keep_hash_compatibility():
    from tools.file_tools import PATCH_SCHEMA, WRITE_FILE_SCHEMA

    write_props = WRITE_FILE_SCHEMA["parameters"]["properties"]
    patch_props = PATCH_SCHEMA["parameters"]["properties"]
    assert "expected_revision" in write_props
    assert "expected_revision" in patch_props
    assert "expected_sha256" in write_props
    assert "expected_sha256" in patch_props
