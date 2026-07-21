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
