# Non-Functional Requirements: Latency Budget & Data Retention Policies (REQ-060, REQ-062)

## 1. Latency Budgets & Performance Targets (REQ-060)

| Metric | Target (Local SLM) | Measurement Point | Alert Threshold |
|---|---|---|---|
| **Time to First Token (TTFT)** | < 300 ms (p95) | API gateway to first SSE token event | > 800 ms |
| **Tool Execution Latency** | < 100 ms (p95) | Internal tool dispatch duration | > 500 ms |
| **Turn-to-Turn Cycle** | < 1,500 ms (p95) | Complete loop cycle including policy check | > 3,000 ms |
| **Trace Ingestion Latency** | < 50 ms (async) | Background push to Langfuse/clickhouse | > 200 ms |

Telemetry from LiteLLM and OpenHands runtime emits span timestamps to Langfuse for continuous regression testing.

---

## 2. Data Retention & Backup Policies (REQ-062)

### 2.1 PostgreSQL Application Database
- **Backup Schedule**: Automated daily snapshot via pg_dump.
- **Retention Period**:
  - Daily backups: 7 days.
  - Weekly snapshots: 30 days.
  - Monthly archives: 1 year.

### 2.2 Observability Traces (Langfuse)
- **Retention Policy**:
  - Raw generation spans & tool traces: 30 days default.
  - Evaluation experiment benchmark datasets: Retained indefinitely for regression comparisons.
- **Scrubbing**: Secrets and PII are redacted synchronously prior to persistence.

---

## 3. Concurrency Targets & Load Testing (REQ-061)

### 3.1 Concurrency Sizing & Targets
- **Target Concurrent User Sessions**: The platform supports a minimum of 20 concurrent active user sessions per worker node without request degradation or connection dropouts.
- **Celery Worker Concurrency**: Managed via `CELERY_WORKER_CONCURRENCY` (default: 8 worker threads/processes per container).
- **Horizontal Scaling**: Worker count scales horizontally via Celery (`docker-compose up --scale celery-worker=N` or Kubernetes HPA based on CPU/queue depth).
- **Task Isolation**: Tasks run with late acknowledgment (`task_acks_late=True`) and unbuffered prefetch (`worker_prefetch_multiplier=1`) to prevent task starvation across worker pools.

### 3.2 Verification & Load Testing
- Automated load testing runner located at `scripts/load_test.py`.
- Execution command:
  ```bash
  uv run python scripts/load_test.py --url http://localhost:8000 --concurrency 20 --total 100
  ```
- Acceptance criteria: 0 dropped sessions, >99% success rate, and p95 session roundtrip within acceptable limits under peak concurrent load.

