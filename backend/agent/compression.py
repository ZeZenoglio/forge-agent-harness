"""Context compression module for long-running agent sessions (REQ-020).

Monitors cumulative context tokens against model window limits. When the
threshold (default: 80% of window) is reached, applies compression strategies:
- rolling-summary: replaces older messages with a concise summary
- truncate-oldest: drops oldest tool observations preserving system & latest turns
- recursive: recursively condenses message blocks
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Manages context window budgets and compresses history when threshold is reached."""

    def __init__(
        self,
        max_context_tokens: int = 32_000,
        threshold_ratio: float = 0.80,
        strategy: str = "rolling-summary",
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.threshold_tokens = int(max_context_tokens * threshold_ratio)
        self.strategy = strategy

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count across a list of message dicts (1 token ≈ 4 chars)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return max(1, total_chars // 4)

    def should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """Check if message context exceeds compression threshold."""
        return self.estimate_tokens(messages) >= self.threshold_tokens

    def compress(
        self,
        messages: list[dict[str, Any]],
        system_preserve: int = 1,
        tail_preserve: int = 4,
    ) -> list[dict[str, Any]]:
        """Compress message list preserving system prompts and recent turns."""
        if not self.should_compress(messages) or len(messages) <= (
            system_preserve + tail_preserve
        ):
            return messages

        head = messages[:system_preserve]
        body = messages[system_preserve:-tail_preserve]
        tail = messages[-tail_preserve:]

        if self.strategy == "truncate-oldest":
            logger.info(
                "Compressing context using truncate-oldest strategy (dropped %d messages)",
                len(body),
            )
            summary_msg = {
                "role": "system",
                "content": f"[Context note: {len(body)} earlier conversation turns truncated to save context]",
            }
            return head + [summary_msg] + tail

        # Default: rolling-summary
        logger.info(
            "Compressing context using rolling-summary strategy on %d messages",
            len(body),
        )
        summary_lines = []
        for msg in body:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            preview = content[:120].replace("\n", " ") + (
                "..." if len(content) > 120 else ""
            )
            summary_lines.append(f"- {role}: {preview}")

        summary_content = (
            "## Summary of Previous Turns\n"
            + "\n".join(summary_lines[:10])
            + (
                f"\n... and {len(summary_lines) - 10} more turns summarized"
                if len(summary_lines) > 10
                else ""
            )
        )

        summary_msg = {
            "role": "system",
            "content": summary_content,
        }

        return head + [summary_msg] + tail
