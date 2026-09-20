"""Unit tests for context compression strategies (REQ-020)."""

from __future__ import annotations

import pytest

from backend.agent.compression import ContextCompressor


@pytest.mark.unit
@pytest.mark.smoke
def test_compression_threshold_detection() -> None:
    compressor = ContextCompressor(max_context_tokens=100, threshold_ratio=0.8)

    short_messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Short question"},
    ]
    assert compressor.should_compress(short_messages) is False

    long_messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Long word " * 100},
    ]
    assert compressor.should_compress(long_messages) is True


@pytest.mark.unit
def test_rolling_summary_compression() -> None:
    compressor = ContextCompressor(
        max_context_tokens=50, threshold_ratio=0.5, strategy="rolling-summary"
    )

    messages = [
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "user", "content": "Turn 1 content " * 10},
        {"role": "assistant", "content": "Turn 2 content " * 10},
        {"role": "user", "content": "Turn 3 content " * 10},
        {"role": "assistant", "content": "Turn 4 content " * 10},
        {"role": "user", "content": "Turn 5 content " * 10},
        {"role": "assistant", "content": "Turn 6 content " * 10},
        {"role": "user", "content": "Latest user request"},
    ]

    compressed = compressor.compress(messages, system_preserve=1, tail_preserve=2)

    # Head (system prompt) preserved
    assert compressed[0]["role"] == "system"
    assert "coding assistant" in compressed[0]["content"]

    # Middle replaced with summary
    assert compressed[1]["role"] == "system"
    assert "Summary of Previous Turns" in compressed[1]["content"]

    # Tail preserved
    assert compressed[-1]["content"] == "Latest user request"
    assert len(compressed) < len(messages)


@pytest.mark.unit
def test_truncate_oldest_compression() -> None:
    compressor = ContextCompressor(
        max_context_tokens=50, threshold_ratio=0.5, strategy="truncate-oldest"
    )

    messages = [
        {"role": "system", "content": "System instruction."},
        {"role": "user", "content": "Old message 1 " * 10},
        {"role": "assistant", "content": "Old message 2 " * 10},
        {"role": "user", "content": "Old message 3 " * 10},
        {"role": "assistant", "content": "Old message 4 " * 10},
        {"role": "user", "content": "Current question"},
    ]

    compressed = compressor.compress(messages, system_preserve=1, tail_preserve=1)

    assert compressed[0]["content"] == "System instruction."
    assert "earlier conversation turns truncated" in compressed[1]["content"]
    assert compressed[-1]["content"] == "Current question"
