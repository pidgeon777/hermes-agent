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


def test_public_schemas_hide_internal_revision_preconditions():
    from tools.file_tools import PATCH_SCHEMA, WRITE_FILE_SCHEMA

    internal_fields = {
        "expected_revision",
        "expected_sha256",
        "expected_start_line",
        "expected_end_line",
    }
    write_props = WRITE_FILE_SCHEMA["parameters"]["properties"]
    patch_props = PATCH_SCHEMA["parameters"]["properties"]

    assert internal_fields.isdisjoint(write_props)
    assert internal_fields.isdisjoint(patch_props)


def test_write_file_treats_empty_revision_object_as_omitted(tmp_path):
    from tools.file_tools import write_file_tool

    target = tmp_path / "sample.txt"
    target.write_text("old\n", encoding="utf-8")

    result = json.loads(write_file_tool(
        str(target), "new\n", expected_revision={}, task_id="empty-write-revision",
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "new\n"


def test_patch_treats_empty_revision_object_as_omitted(tmp_path):
    from tools.file_tools import patch_tool

    target = tmp_path / "sample.txt"
    target.write_text("old\n", encoding="utf-8")

    result = json.loads(patch_tool(
        mode="replace",
        path=str(target),
        old_string="old",
        new_string="new",
        expected_revision={},
        task_id="empty-patch-revision",
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "new\n"


def test_handlers_treat_empty_revision_object_as_omitted(tmp_path):
    from tools.file_tools import _handle_patch, _handle_write_file

    write_target = tmp_path / "write.txt"
    write_target.write_text("old\n", encoding="utf-8")
    write_result = json.loads(_handle_write_file({
        "path": str(write_target),
        "content": "new\n",
        "expected_revision": {},
    }, task_id="empty-handler-write"))

    patch_target = tmp_path / "patch.txt"
    patch_target.write_text("old\n", encoding="utf-8")
    patch_result = json.loads(_handle_patch({
        "mode": "replace",
        "path": str(patch_target),
        "old_string": "old",
        "new_string": "new",
        "expected_revision": {},
    }, task_id="empty-handler-patch"))

    assert not write_result.get("error"), write_result
    assert not patch_result.get("error"), patch_result
    assert write_target.read_text(encoding="utf-8") == "new\n"
    assert patch_target.read_text(encoding="utf-8") == "new\n"

def test_write_and_patch_publish_persistence_policy_without_revision_fields():
    from tools.file_tools import WRITE_FILE_SCHEMA, PATCH_SCHEMA
    for schema in (WRITE_FILE_SCHEMA, PATCH_SCHEMA):
        props = schema["parameters"]["properties"]
        assert props["persistence"]["enum"] == ["auto", "buffer-only", "save"]
        assert props["persistence"]["default"] == "auto"
        assert "allow_save_preexisting_dirty" in props


def test_native_write_rejects_buffer_only_instead_of_falling_back_to_disk(tmp_path):
    from tools.file_tools import _handle_write_file
    target = tmp_path / "must-not-exist.txt"
    result = json.loads(_handle_write_file({
        "path": str(target), "content": "x", "persistence": "buffer-only",
    }, task_id="persistence-native"))
    assert "requires an enabled live Context Runtime" in result["error"]
    assert not target.exists()


def test_native_patch_rejects_buffer_only_instead_of_falling_back_to_disk(tmp_path):
    from tools.file_tools import _handle_patch
    target = tmp_path / "native.txt"
    target.write_text("old", encoding="utf-8")
    result = json.loads(_handle_patch({
        "mode": "replace", "path": str(target), "old_string": "old",
        "new_string": "new", "persistence": "buffer-only",
    }, task_id="persistence-native"))
    assert "requires an enabled live Context Runtime" in result["error"]
    assert target.read_text(encoding="utf-8") == "old"


def test_empty_materialized_persistence_is_auto_for_native_handlers(tmp_path):
    from tools.file_tools import _handle_write_file, _handle_patch
    for empty in (None, "", {}):
        target = tmp_path / f"write-{type(empty).__name__}.txt"
        result = json.loads(_handle_write_file({
            "path": str(target), "content": "new", "persistence": empty,
        }, task_id="persistence-empty"))
        assert result.get("success") is not False
        assert target.read_text(encoding="utf-8") == "new"
        patch_target = tmp_path / f"patch-{type(empty).__name__}.txt"
        patch_target.write_text("old", encoding="utf-8")
        patch_result = json.loads(_handle_patch({
            "mode": "replace", "path": str(patch_target), "old_string": "old",
            "new_string": "new", "persistence": empty,
        }, task_id="persistence-empty"))
        assert patch_result.get("success") is not False
        assert patch_target.read_text(encoding="utf-8") == "new"
