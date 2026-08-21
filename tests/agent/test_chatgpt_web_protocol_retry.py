from agent.conversation_loop import _is_deterministic_gateway_protocol_error


def test_malformed_chatgpt_web_tool_protocol_errors_are_not_retryable():
    assert _is_deterministic_gateway_protocol_error(
        Exception("completion_verification_invalid:invalid_envelope:Invalid JSON")
    )
    assert _is_deterministic_gateway_protocol_error(
        Exception("required_tool_call_missing:not_tool_call:No hermes-tool envelope found")
    )


def test_transport_and_browser_errors_remain_retryable():
    for message in (
        "first_token_timeout",
        "send_not_started",
        "extension_disconnected",
        "browser_bridge_error:image_mode_not_applied",
        "HTTP 503 Service Unavailable",
    ):
        assert not _is_deterministic_gateway_protocol_error(Exception(message))
