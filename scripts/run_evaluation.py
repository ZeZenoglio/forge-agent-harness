"""Two-stage automated evaluation experiment runner.

Usage::

    # Stage 1: Generate agent responses
    python scripts/run_evaluation.py generate --track a
    python scripts/run_evaluation.py generate --track b

    # Stage 2: Score saved responses
    python scripts/run_evaluation.py score --track a
    python scripts/run_evaluation.py score --track b

    # Run both stages in sequence
    python scripts/run_evaluation.py run --track a

Implements REQ-007 (Track A & B suite), REQ-008 (automated runner),
and REQ-047 (tiered evaluation — use ``--tier smoke`` for the fast subset).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from evaluation.metrics import score_prediction

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

DATASETS = {
    "a": _REPO_ROOT / "evaluation" / "datasets" / "track_a" / "questions.json",
    "b": _REPO_ROOT / "evaluation" / "datasets" / "track_b" / "tasks.json",
}
RESULTS_DIR = _REPO_ROOT / "evaluation" / "results"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_dataset(track: str) -> list[dict]:
    path = DATASETS[track]
    with path.open() as f:
        return json.load(f)


def _results_path(track: str, stage: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return RESULTS_DIR / f"track_{track}_{stage}_{ts}.json"


# ── Stage 1: Generate ─────────────────────────────────────────────────────────


async def _generate_track_a(items: list[dict], tier: str) -> list[dict]:
    """Call the backend API for each Track A question and collect responses."""
    import httpx

    if tier == "smoke":
        items = items[:2]

    base = "http://localhost:8000/api/v1/agent"
    results = []

    for item in items:
        logger.info("[Track A] Generating: %s", item["id"])
        prediction = ""
        error = None

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Start the agent
                r = await client.post(f"{base}/run", json={"task": item["question"]})
                r.raise_for_status()
                session_id: str = r.json()["session_id"]

                # Consume the SSE stream
                async with client.stream(
                    "GET", f"{base}/stream/{session_id}"
                ) as stream:
                    async for line in stream.aiter_lines():
                        if line.startswith("data: "):
                            event = json.loads(line[6:])
                            if event.get("event_type") == "finish":
                                prediction = event.get("content", "")
                                break
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            logger.warning("[Track A] %s failed: %s", item["id"], exc)

        results.append(
            {
                "id": item["id"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "prediction": prediction,
                "error": error,
            }
        )

    return results


async def _generate_track_b(items: list[dict], tier: str) -> list[dict]:
    """Call the backend API for each Track B agentic task."""
    import httpx

    if tier == "smoke":
        items = items[:1]

    base = "http://localhost:8000/api/v1/agent"
    results = []

    for item in items:
        logger.info("[Track B] Generating: %s", item["id"])
        events: list[dict] = []
        error = None

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(f"{base}/run", json={"task": item["task"]})
                r.raise_for_status()
                session_id = r.json()["session_id"]

                async with client.stream(
                    "GET", f"{base}/stream/{session_id}"
                ) as stream:
                    async for line in stream.aiter_lines():
                        if line.startswith("data: "):
                            event = json.loads(line[6:])
                            events.append(event)
                            if event.get("event_type") in ("finish", "error"):
                                break
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            logger.warning("[Track B] %s failed: %s", item["id"], exc)

        results.append(
            {
                "id": item["id"],
                "task": item["task"],
                "expected_tools": item.get("expected_tools", []),
                "events": events,
                "error": error,
            }
        )

    return results


# ── Stage 2: Score ────────────────────────────────────────────────────────────


def _score_track_a(results: list[dict]) -> list[dict]:

    scored = []
    for r in results:
        metrics = score_prediction(r.get("prediction", ""), r.get("ground_truth", ""))
        scored.append({**r, "metrics": metrics})
    return scored


def _score_track_b(results: list[dict]) -> list[dict]:
    from evaluation.trajectory import TrajectoryEvaluator

    evaluator = TrajectoryEvaluator()
    scored = []
    for r in results:
        traj = evaluator.evaluate(r.get("events", []))
        scored.append({**r, "trajectory": traj.as_dict()})
    return scored


def _print_summary_a(results: list[dict]) -> None:
    print("\n─── Track A Results ──────────────────────────────")
    print(f"{'ID':<12} {'EM':>5} {'F1':>6} {'SemSim':>8} {'LenR':>6}")
    print("─" * 45)
    for r in results:
        m = r.get("metrics", {})
        print(
            f"{r['id']:<12}"
            f" {m.get('exact_match', 0):>5.2f}"
            f" {m.get('f1', 0):>6.2f}"
            f" {m.get('semantic_similarity', 0):>8.4f}"
            f" {m.get('length_ratio', 0):>6.2f}"
        )
    print("─" * 45)


def _print_summary_b(results: list[dict]) -> None:
    print("\n─── Track B Results ──────────────────────────────")
    print(f"{'ID':<12} {'Done':>5} {'Err':>5} {'PlanAdh':>9} {'SchemaV':>9}")
    print("─" * 50)
    for r in results:
        t = r.get("trajectory", {})
        print(
            f"{r['id']:<12}"
            f" {t.get('completed', False)!s:>5}"
            f" {t.get('errored', False)!s:>5}"
            f" {t.get('plan_adherence', 0):>9.2f}"
            f" {t.get('schema_validity', 0):>9.2f}"
        )
    print("─" * 50)


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="JO Harness evaluation runner")
    p.add_argument(
        "command", choices=["generate", "score", "run"], help="Stage to execute"
    )
    p.add_argument(
        "--track", choices=["a", "b"], default="a", help="Evaluation track (default: a)"
    )
    p.add_argument(
        "--tier",
        choices=["smoke", "full"],
        default="full",
        help="Tier: smoke (fast subset) or full (default: full)",
    )
    p.add_argument(
        "--input", help="Path to generated results JSON (required for 'score')"
    )
    return p.parse_args()


async def main() -> None:
    args = _parse_args()
    track = args.track
    tier = args.tier

    if args.command in ("generate", "run"):
        dataset = _load_dataset(track)
        logger.info(
            "Generating Track %s responses (%s tier, %d items)...",
            track.upper(),
            tier,
            len(dataset),
        )

        if track == "a":
            results = await _generate_track_a(dataset, tier)
        else:
            results = await _generate_track_b(dataset, tier)

        out_path = _results_path(track, "generated")
        out_path.write_text(json.dumps(results, indent=2))
        logger.info("Saved generated results → %s", out_path)

        if args.command == "run":
            # Fall through to scoring
            args.input = str(out_path)
        else:
            return

    # ── Score stage ──────────────────────────────────────────────────────────
    if not args.input:
        logger.error("--input is required for 'score' command")
        sys.exit(1)

    raw = json.loads(Path(args.input).read_text())

    if track == "a":
        scored = _score_track_a(raw)
        _print_summary_a(scored)
    else:
        scored = _score_track_b(raw)
        _print_summary_b(scored)

    out_path = _results_path(track, "scored")
    out_path.write_text(json.dumps(scored, indent=2))
    logger.info("Saved scored results → %s", out_path)


if __name__ == "__main__":
    asyncio.run(main())
