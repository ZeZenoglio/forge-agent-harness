"""LLM-as-Judge evaluators for Track B trajectory assessment.

Implements REQ-011 (content accuracy), REQ-012 (form & language), and
REQ-013 (completeness).  Each judge calls a LiteLLM-compatible endpoint via
the ``reviewer`` model alias.  When the endpoint is unreachable the judge
logs a warning and returns the stub value ``0.0`` so the pipeline degrades
gracefully rather than crashing.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# LiteLLM proxy endpoint.  Override via LITELLM_BASE_URL environment variable.
_LITELLM_BASE = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
_REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "reviewer")
_JUDGE_TIMEOUT = 30  # seconds


def _build_prompt(criterion: str, task: str, response: str) -> str:
    return (
        f"You are an expert evaluator. Score the following response on {criterion} "
        f"from 0.0 to 1.0 (higher is better). Return ONLY a JSON object with a "
        f"single key 'score' containing the float, e.g. {{\"score\": 0.85}}.\n\n"
        f"TASK:\n{task}\n\nRESPONSE:\n{response}"
    )


async def _call_judge(criterion: str, task: str, response: str) -> float:
    """POST to the LiteLLM proxy and parse the score.

    Returns 0.0 on any network or parsing error so callers are never blocked.
    """
    prompt = _build_prompt(criterion, task, response)
    payload: dict[str, Any] = {
        "model": _REVIEWER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 64,
    }
    try:
        async with httpx.AsyncClient(timeout=_JUDGE_TIMEOUT) as client:
            res = await client.post(
                f"{_LITELLM_BASE}/chat/completions",
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
            content: str = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return float(parsed["score"])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "LLM judge unavailable for '%s': %s — returning 0.0 stub", criterion, exc
        )
        return 0.0


class LLMJudge:
    """Track B trajectory evaluator using LLM-as-a-judge (REQ-011 to REQ-013).

    Configured to use the ``reviewer`` model alias at temperature 0 via the
    LiteLLM proxy.  Degrades gracefully to 0.0 stubs when the proxy is offline.
    """

    def __init__(self, model_alias: str = _REVIEWER_MODEL) -> None:
        self.model_alias = model_alias

    async def evaluate_content_accuracy(self, task: str, response: str) -> float:
        """Score [0, 1]: how factually accurate the response is (REQ-011)."""
        return await _call_judge(
            "content accuracy (factual correctness)", task, response
        )

    async def evaluate_form_language(self, task: str, response: str) -> float:
        """Score [0, 1]: quality of reasoning form and language (REQ-012).

        Checks for: coherent step-by-step reasoning, no hallucinated tool
        names, no irrelevant tangents.
        """
        return await _call_judge(
            "form and language (reasoning quality, no hallucinated tools)",
            task,
            response,
        )

    async def evaluate_completeness(self, task: str, response: str) -> float:
        """Score [0, 1]: whether all task requirements were met (REQ-013)."""
        return await _call_judge(
            "completeness (all task requirements addressed)", task, response
        )

    async def evaluate_all(self, task: str, response: str) -> dict[str, float]:
        """Run all three judges and return aggregated scores."""
        import asyncio

        accuracy, form, completeness = await asyncio.gather(
            self.evaluate_content_accuracy(task, response),
            self.evaluate_form_language(task, response),
            self.evaluate_completeness(task, response),
        )
        composite = (accuracy + form + completeness) / 3.0
        return {
            "content_accuracy": accuracy,
            "form_language": form,
            "completeness": completeness,
            "composite_judge": composite,
        }
