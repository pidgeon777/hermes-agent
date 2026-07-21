from __future__ import annotations

import hashlib
import json


def _hash(text: str) -> str:
    normalized = "\n".join(text.splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def test_patch_expected_sha256_allows_matching_complete_file(tmp_path):
    from tools.file_tools import patch_tool

    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    result = json.loads(patch_tool(
        mode="replace",
        path=str(target),
        old_string="beta",
        new_string="BETA",
        expected_sha256=_hash("alpha\nbeta"),
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "alpha\nBETA\n"


def test_patch_expected_sha256_blocks_stale_complete_file(tmp_path):
    from tools.file_tools import patch_tool

    target = tmp_path / "sample.txt"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    result = json.loads(patch_tool(
        mode="replace",
        path=str(target),
        old_string="beta",
        new_string="BETA",
        expected_sha256=_hash("stale"),
    ))

    assert "STALE_CONTEXT" in result["error"]
    assert result["expected_sha256"] == _hash("stale")
    assert result["actual_sha256"] == _hash("alpha\nbeta")
    assert target.read_text(encoding="utf-8") == "alpha\nbeta\n"


def test_patch_expected_sha256_supports_selected_range(tmp_path):
    from tools.file_tools import patch_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\ntwo\nthree\n", encoding="utf-8")
    result = json.loads(patch_tool(
        mode="replace",
        path=str(target),
        old_string="two",
        new_string="TWO",
        expected_sha256=_hash("two"),
        expected_start_line=2,
        expected_end_line=2,
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "one\nTWO\nthree\n"


def test_patch_tool_treats_empty_expected_sha256_as_omitted_in_v4a_mode(tmp_path):
    from tools.file_tools import patch_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\n", encoding="utf-8")
    v4a = (
        "*** Begin Patch\n"
        f"*** Update File: {target}\n"
        "@@\n"
        "-one\n"
        "+ONE\n"
        "*** End Patch"
    )
    result = json.loads(patch_tool(
        mode="patch",
        patch=v4a,
        expected_sha256="",
    ))

    assert not result.get("error"), result
    assert target.read_text(encoding="utf-8") == "ONE\n"


def test_patch_expected_sha256_rejects_v4a_mode(tmp_path):
    from tools.file_tools import patch_tool

    target = tmp_path / "sample.txt"
    target.write_text("one\n", encoding="utf-8")
    v4a = (
        "*** Begin Patch\n"
        f"*** Update File: {target}\n"
        "@@\n"
        "-one\n"
        "+ONE\n"
        "*** End Patch"
    )
    result = json.loads(patch_tool(
        mode="patch",
        patch=v4a,
        expected_sha256=_hash("one"),
    ))

    assert "supported only for replace mode" in result["error"]
    assert target.read_text(encoding="utf-8") == "one\n"