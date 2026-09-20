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
