"""Concurrent session load test runner (REQ-061).

Tests concurrency targets by simulating N concurrent user sessions interacting
with the Forge Agent API endpoints (/api/v1/agent/run, /api/v1/health, /api/v1/tools).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Any

import httpx


async def simulate_user_session(
    client: httpx.AsyncClient,
    base_url: str,
    user_index: int,
    results: list[dict[str, Any]],
) -> None:
    session_start = time.perf_counter()
    errors = 0

    try:
        # 1. Health check
        r1 = await client.get(f"{base_url}/api/v1/health")
        if r1.status_code != 200:
            errors += 1

        # 2. Tool listing
        r2 = await client.get(f"{base_url}/api/v1/tools")
        if r2.status_code != 200:
            errors += 1

        # 3. Agent task run
        r3 = await client.post(
            f"{base_url}/api/v1/agent/run",
            json={"task": f"Load test task from simulated user {user_index}"},
        )
        if r3.status_code != 200:
            errors += 1

    except Exception:  # noqa: BLE001
        errors += 1

    session_duration = time.perf_counter() - session_start
    results.append(
        {
            "user_index": user_index,
            "duration_seconds": session_duration,
            "errors": errors,
        }
    )


async def run_load_test(
    base_url: str = "http://localhost:8000",
    concurrency: int = 20,
    total_sessions: int = 50,
) -> dict[str, Any]:
    """Execute load test with specified concurrency."""
    print(
        f"🚀 Starting load test: {total_sessions} sessions with concurrency {concurrency} against {base_url}"
    )
    results: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def bounded_user(idx: int) -> None:
            async with semaphore:
                await simulate_user_session(client, base_url, idx, results)

        start_time = time.perf_counter()
        tasks = [bounded_user(i) for i in range(total_sessions)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    durations = [r["duration_seconds"] for r in results]
    total_errors = sum(r["errors"] for r in results)
    p50 = sorted(durations)[int(len(durations) * 0.5)] if durations else 0
    p95 = sorted(durations)[int(len(durations) * 0.95)] if durations else 0

    report = {
        "concurrency_target": concurrency,
        "total_sessions": total_sessions,
        "total_time_seconds": round(total_time, 2),
        "throughput_sessions_per_sec": round(total_sessions / total_time, 2)
        if total_time > 0
        else 0,
        "p50_duration_sec": round(p50, 3),
        "p95_duration_sec": round(p95, 3),
        "total_errors": total_errors,
        "success_rate_pct": round(
            (total_sessions - total_errors) / total_sessions * 100, 1
        ),
    }

    print("📊 Load Test Summary:")
    for k, v in report.items():
        print(f"  {k}: {v}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Forge Agent Concurrency Load Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base API URL")
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Target concurrent sessions"
    )
    parser.add_argument("--total", type=int, default=20, help="Total sessions to run")
    args = parser.parse_args()

    report = asyncio.run(
        run_load_test(
            base_url=args.url, concurrency=args.concurrency, total_sessions=args.total
        )
    )
    if report["total_errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
