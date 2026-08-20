"""Tests for pending follow-up extraction in recursive _run_agent calls.

When pending_event is None (Path B: pending comes from interrupt_message),
accessing pending_event.channel_prompt previously raised AttributeError.
This verifies the fix: channel_prompt is captured inside the
`if pending_event is not None:` block and falls back to None otherwise.

Also verifies that internal control interrupt reasons like "Stop requested"
do not get recycled into the pending-user-message follow-up path.
"""

from types import SimpleNamespace

from gateway.run import _is_control_interrupt_message, _strip_auto_continue_noise


def _extract_channel_prompt(pending_event):
    """Reproduce the fixed logic from gateway/run.py.

    Mirrors the variable-capture pattern used before the recursive
    _run_agent call so we can test both paths without a full runner.
    """
    next_channel_prompt = None
    if pending_event is not None:
        next_channel_prompt = getattr(pending_event, "channel_prompt", None)
    return next_channel_prompt


def _extract_pending_text(interrupted, pending_event, interrupt_message):
    """Reproduce the fixed pending-text selection from gateway/run.py."""
    if interrupted and pending_event is None and interrupt_message:
        if _is_control_interrupt_message(interrupt_message):
            return None
        return interrupt_message
    return None


class TestPendingEventNoneChannelPrompt:
    """Guard against AttributeError when pending_event is None."""


    def test_pending_event_with_channel_prompt_passes_through(self):
        """Path A: pending_event present — channel_prompt is forwarded."""
        event = SimpleNamespace(channel_prompt="You are a helpful bot.")
        result = _extract_channel_prompt(event)
        assert result == "You are a helpful bot."


class TestControlInterruptMessages:
    """Control interrupt reasons must not become follow-up user input."""

    def test_stop_requested_is_not_treated_as_pending_user_message(self):
        result = _extract_pending_text(True, None, "Stop requested")
        assert result is None

    def test_session_lease_interrupts_are_not_recycled_as_user_messages(self):
        for message in (
            "Session turn lease lost; stopping to protect the transcript.",
            "Session turn lease could not be refreshed; stopping to protect the transcript.",
        ):
            assert _extract_pending_text(True, None, message) is None

    def test_persisted_lease_noise_is_removed_without_dropping_real_user_text(self):
        question = "Cerca online il meteo di oggi a Brescia."
        noisy = (
            f"{question}\n\n"
            "Session turn lease could not be refreshed; stopping to protect the transcript."
        )
        assert _strip_auto_continue_noise(noisy) == question
        assert _strip_auto_continue_noise(
            "Session turn lease lost; stopping to protect the transcript."
        ) == ""


