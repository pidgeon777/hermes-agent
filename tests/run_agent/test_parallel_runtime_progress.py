from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from run_agent import AIAgent


def _agent(*, session_id: str = "session-a") -> AIAgent:
    agent = AIAgent.__new__(AIAgent)
    agent.session_id = session_id
    agent.model = "test-model"
    agent.provider = "test-provider"
    agent._api_call_count = 3
    agent.max_iterations = 12
    agent.iteration_budget = SimpleNamespace(used=4, max_total=12)
    agent._current_tool = "read_file"
    agent._last_activity_ts = 0.0
    agent._last_activity_desc = "initializing"
    return agent


def test_touch_activity_is_noop_without_parallel_progress_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("HERMES_PARALLEL_PROGRESS_FILE", raising=False)
    monkeypatch.delenv("HERMES_PARALLEL_ACTIVITY_LOG", raising=False)
    monkeypatch.delenv("HERMES_PARALLEL_TASK_ID", raising=False)
    monkeypatch.delenv("HERMES_PARALLEL_TASK_DIR", raising=False)

    agent = _agent()
    agent._touch_activity("waiting for model")

    assert agent._last_activity_desc == "waiting for model"
    assert not (tmp_path / "child_progress.json").exists()
    assert not (tmp_path / "activity.log").exists()


def test_touch_activity_writes_atomic_parallel_progress_snapshot(monkeypatch, tmp_path):
    progress = tmp_path / "child_progress.json"
    activity = tmp_path / "activity.log"
    monkeypatch.setenv("HERMES_PARALLEL_PROGRESS_FILE", str(progress))
    monkeypatch.setenv("HERMES_PARALLEL_ACTIVITY_LOG", str(activity))
    monkeypatch.setenv("HERMES_PARALLEL_TASK_ID", "task-a")
    monkeypatch.setenv("HERMES_PARALLEL_TASK_DIR", str(tmp_path))

    agent = _agent()
    agent._touch_activity("API call #3 completed")

    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload == {
        "session_id": "session-a",
        "model": "test-model",
        "provider": "test-provider",
        "api_call_count": 3,
        "max_iterations": 12,
        "budget_used": 4,
        "budget_max": 12,
        "current_tool": "read_file",
        "last_activity_desc": "API call #3 completed",
        "last_activity_ts": agent._last_activity_ts,
        "updated_at": payload["updated_at"],
        "task_id": "task-a",
        "task_dir": str(tmp_path),
    }
    assert "API call #3 completed" in activity.read_text(encoding="utf-8")
    assert not progress.with_suffix(".json.tmp").exists()


def test_parallel_progress_files_remain_isolated_between_tasks(monkeypatch, tmp_path):
    first = tmp_path / "first" / "child_progress.json"
    second = tmp_path / "second" / "child_progress.json"

    monkeypatch.setenv("HERMES_PARALLEL_PROGRESS_FILE", str(first))
    monkeypatch.setenv("HERMES_PARALLEL_TASK_ID", "task-first")
    _agent(session_id="session-first")._touch_activity("first activity")

    monkeypatch.setenv("HERMES_PARALLEL_PROGRESS_FILE", str(second))
    monkeypatch.setenv("HERMES_PARALLEL_TASK_ID", "task-second")
    _agent(session_id="session-second")._touch_activity("second activity")

    assert json.loads(first.read_text(encoding="utf-8"))["session_id"] == "session-first"
    assert json.loads(second.read_text(encoding="utf-8"))["session_id"] == "session-second"


def test_parallel_progress_write_errors_never_break_agent_activity(monkeypatch, tmp_path):
    directory = tmp_path / "not-a-file"
    directory.mkdir()
    monkeypatch.setenv("HERMES_PARALLEL_PROGRESS_FILE", str(directory))

    agent = _agent()
    agent._touch_activity("still alive")

    assert agent._last_activity_desc == "still alive"
