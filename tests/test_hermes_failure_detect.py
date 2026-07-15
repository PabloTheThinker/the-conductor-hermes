"""Hermes-aligned failure detection — no false scars from success dumps."""

from __future__ import annotations

import json

from conductor.hermes_bridge import tool_result_looks_failed


def test_success_json_with_error_word_in_content_is_ok():
    body = json.dumps(
        {
            "ok": True,
            "content": "fixed the error in parse_failed_handler",
            "notes": "errno was a red herring",
        }
    )
    assert tool_result_looks_failed(body) is False
    assert tool_result_looks_failed(body, status="ok") is False
    assert tool_result_looks_failed(body, tool_name="read_file") is False


def test_json_truthy_error_key_is_failure():
    body = json.dumps({"error": "no such file", "path": "/tmp/x"})
    assert tool_result_looks_failed(body) is True
    assert tool_result_looks_failed(body, status="error") is True


def test_host_status_ok_overrides_body_words():
    body = "ERROR: this is just log text from a successful dump"
    assert tool_result_looks_failed(body, status="ok") is False


def test_host_status_error_marks_failed():
    assert tool_result_looks_failed(
        "upstream timeout",
        status="error",
        error_type="TimeoutError",
    )


def test_exit_code_nonzero_even_when_status_ok():
    body = json.dumps({"exit_code": 1, "output": "cmd failed"})
    assert tool_result_looks_failed(body, status="ok") is True
    body0 = json.dumps({"exit_code": 0, "output": "ok error string in dump"})
    assert tool_result_looks_failed(body0, status="ok") is False


def test_plain_text_strong_markers_only():
    assert tool_result_looks_failed("Traceback (most recent call last):") is True
    assert tool_result_looks_failed("permission denied: /etc/shadow") is True
    # Bare "error" must NOT scar
    assert tool_result_looks_failed("no error in this line of prose") is False
    assert tool_result_looks_failed("failed to start") is False  # not strong enough alone


def test_already_annotated_not_reclassified():
    body = "something\n[integrity cascade] scar=abc kind=tool_error"
    assert tool_result_looks_failed(body) is False
    body2 = "Conductor spine blocked: path outside workspace"
    assert tool_result_looks_failed(body2) is False


def test_error_type_without_body():
    assert tool_result_looks_failed(None, error_type="RateLimitError") is True
    assert tool_result_looks_failed("", status="error") is True
    assert tool_result_looks_failed(None) is False
