from pathlib import Path

from hermes_cli.plugins import invoke_plugin_command


def test_invoke_plugin_command_passes_session_id_when_supported():
    captured = {}

    def handler(raw_args, session_id=""):
        captured["raw_args"] = raw_args
        captured["session_id"] = session_id
        return "ok"

    assert invoke_plugin_command(handler, "status", session_id="session-a") == "ok"
    assert captured == {"raw_args": "status", "session_id": "session-a"}


def test_invoke_plugin_command_preserves_legacy_one_argument_handlers():
    def handler(raw_args):
        return f"legacy:{raw_args}"

    assert invoke_plugin_command(handler, "status", session_id="ignored") == "legacy:status"


def test_invoke_plugin_command_supports_kwargs_handlers():
    captured = {}

    def handler(raw_args, **kwargs):
        captured.update(kwargs)
        return raw_args

    assert invoke_plugin_command(handler, "status", session_id="session-b") == "status"
    assert captured["session_id"] == "session-b"


def test_cli_gateway_and_tui_dispatch_pass_session_context():
    root = Path(__file__).resolve().parents[2]
    cli = (root / "cli.py").read_text(encoding="utf-8")
    gateway = (root / "gateway" / "run.py").read_text(encoding="utf-8")
    tui = (root / "tui_gateway" / "methods_tools.py").read_text(encoding="utf-8")

    assert "session_id=self.session_id" in cli
    assert "session_id=self._session_key_for_source(event.source)" in gateway
    assert 'session_id=params.get("session_id", "")' in tui
    assert 'session_id=session["session_key"]' in tui
