"""Unit tests for the evaluation module (REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-047, REQ-063)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.judges import LLMJudge
from evaluation.metrics import (
    cap_observation,
    length_ratio,
    score_prediction,
    semantic_similarity,
)
from evaluation.trajectory import TrajectoryEvaluator


@pytest.mark.unit
@pytest.mark.smoke
def test_length_ratio() -> None:
    # Terse
    assert length_ratio("short", "much longer text than short") < 1.0
    # Verbose
    assert length_ratio("this is a verbose answer", "short") < 1.0
    # Equal
    assert length_ratio("two words", "two words") == 1.0
    # Empty
    assert length_ratio("", "expected") == 0.0
    assert length_ratio("generated", "") == 0.0


@pytest.mark.unit
@pytest.mark.smoke
def test_semantic_similarity_fallback_and_scoring() -> None:
    # Exact match
    score_exact = semantic_similarity("Paris", "Paris")
    assert 0.95 <= score_exact <= 1.0

    # Completely different
    score_diff = semantic_similarity("Paris", "Quantum electrodynamics in a vacuum")
    assert score_diff < score_exact


@pytest.mark.unit
def test_cap_observation() -> None:
    short_text = "Short output"
    assert cap_observation(short_text, max_chars=100) == short_text

    long_text = "word " * 500
    capped = cap_observation(long_text, max_chars=50)
    assert "[... content truncated" in capped
    assert len(capped) < len(long_text)


@pytest.mark.unit
def test_score_prediction() -> None:
    scores = score_prediction("Paris", "Paris")
    assert scores["exact_match"] == 1.0
    assert scores["f1"] == 1.0
    assert scores["length_ratio"] == 1.0
    assert scores["semantic_similarity"] >= 0.95


@pytest.mark.asyncio
@pytest.mark.unit
async def test_llm_judges_fallback() -> None:
    judge = LLMJudge()
    acc = await judge.evaluate_content_accuracy("What is 2+2?", "4")
    assert isinstance(acc, float)
    assert 0.0 <= acc <= 1.0

    form = await judge.evaluate_form_language("What is 2+2?", "The answer is 4.")
    assert isinstance(form, float)
    assert 0.0 <= form <= 1.0

    comp = await judge.evaluate_completeness(
        "List capitals of France and Germany", "Paris and Berlin"
    )
    assert isinstance(comp, float)
    assert 0.0 <= comp <= 1.0

    all_scores = await judge.evaluate_all("Task", "Response")
    assert "content_accuracy" in all_scores
    assert "form_language" in all_scores
    assert "completeness" in all_scores
    assert "composite_judge" in all_scores


@pytest.mark.unit
@pytest.mark.smoke
def test_trajectory_evaluator() -> None:
    events = [
        {"seq": 1, "event_type": "start", "content": "Starting"},
        {"seq": 2, "event_type": "tool_call", "metadata": {"tool_name": "read_file"}},
        {"seq": 3, "event_type": "tool_result", "content": "file contents"},
        {"seq": 4, "event_type": "tool_call", "metadata": {"tool_name": "write_file"}},
        {"seq": 5, "event_type": "tool_result", "content": "saved"},
        {"seq": 6, "event_type": "finish", "content": "Done"},
    ]
    evaluator = TrajectoryEvaluator()
    report = evaluator.evaluate(events)

    assert report.total_events == 6
    assert report.completed is True
    assert report.errored is False
    assert report.tool_calls == 2
    assert report.schema_violations == 0
    assert report.plan_adherence == 1.0
    assert report.schema_validity == 1.0


@pytest.mark.unit
def test_dataset_files_valid() -> None:
    track_a_path = Path("evaluation/datasets/track_a/questions.json")
    track_b_path = Path("evaluation/datasets/track_b/tasks.json")

    assert track_a_path.exists()
    assert track_b_path.exists()

    with open(track_a_path, encoding="utf-8") as f:
        questions = json.load(f)
        assert len(questions) >= 5
        assert all("question" in q and "ground_truth" in q for q in questions)

    with open(track_b_path, encoding="utf-8") as f:
        tasks = json.load(f)
        assert len(tasks) >= 3
        assert all("task" in t for t in tasks)
