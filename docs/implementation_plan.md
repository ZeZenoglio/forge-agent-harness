# JO Harness — Implementation Plan

**Date:** 18 September 2026  
**Version:** 2.0 (Post-Audit Remediation)  
**Spec reference:** [sdd_requirements.csv](file:///Users/josezenogliodeoliveira/GitHub%20Repos/JO_harness/docs/sdd_requirements.csv)  
**Research reference:** [open_agent_harness_findings.md](file:///Users/josezenogliodeoliveira/GitHub%20Repos/JO_harness/docs/open_agent_harness_findings.md)  
**Audit reference:** [jo_harness_audit_report.md](file:///Users/josezenogliodeoliveira/GitHub%20Repos/JO_harness/docs/jo_harness_audit_report.md)

---

## 0. Executive Summary

JO Harness is a modular, model-agnostic agent platform built on **OpenHands SDK** (agent harness), **FastAPI** (API layer), **LiteLLM Proxy** (model gateway), **Langfuse** (observability & evaluation), and **PostgreSQL** (application data). It runs locally on small open-source models via **Ollama** and can scale to cloud models by changing LiteLLM configuration.

The build is organized into **three phases**, with the evaluation suite built *first* (Phase 1) so that every subsequent change to the agent is immediately measurable. Following the Phase 0 architecture audit, this plan enforces strict **deterministic guardrails**, **prefix-stability for prompt caching**, and a **split evaluation methodology** separating regression benchmarks from agentic trajectory tests.

---

## 1. Key Technical Decisions

### 1.1 Model Cascade

Instead of a single default SLM, the harness employs a **4-alias model cascade** to optimize cost, latency, and capability:
1. `default-agent` (qwen3.5:4b) — The primary iterative loop and tool-calling engine.
2. `utility-small` (e.g. qwen2.5:1.5b) — Fast classification and intent routing.
3. `summarizer` — Dedicated context compression.
4. `reviewer` (e.g. qwen3.5:9b or cloud model) — Used for LLM-as-Judge evaluation with `temperature: 0`.

**Escalation Trigger:** If tool-call schema validity rate drops below 90% or Track B success rate < 40% after two prompt iterations, `default-agent` is escalated to the 9B model.

### 1.2 Evaluation Re-design (Track A & Track B)

- **Track A (Regression):** 200-item subset of TriviaQA, evaluated purely using Exact Match (EM) and F1 (alias-aware) for fast, deterministic regression testing.
- **Track B (Agentic):** A 30-item internal suite of multi-step agentic tasks evaluated via a **Trajectory Evaluator** and programmatic verifiers (plan adherence, tool validity, iterations, recovery).

### 1.3 Harness Choice: OpenHands SDK

OpenHands SDK is the core harness. To mitigate upstream API instability (packages pin strictly), the application code relies entirely on an `AgentRuntime` interface. The implementation `OpenHandsRuntime` wraps the pinned SDK.

### 1.4 Interoperability Stack

| Protocol | Purpose | Implementation |
|---|---|---|
| **MCP** | Expose agent tools to clients | FastMCP server (stateless **2026-07-28** protocol spec) |
| **A2A** | Receive delegated tasks | A2A JSON-RPC + `/.well-known/agent-card.json` |
| **LiteLLM** | Model-agnostic LLM calls | LiteLLM Proxy container |

### 1.5 Threat Model & Security Posture

- **Sandbox Environment:** Code execution and file operations must be heavily contained. For local dev, we explicitly accept risk but mandate running the entire stack in a **disposable VM**.
- **Guardrails (Policy Engine):** A synchronous policy engine operates below the `AgentRuntime` to enforce run budgets, thrash breaking, argument validation, and secret scrubbing *before* any tool is invoked.
- **Token Economics:** Token tracking includes prefix-stability discipline (volatile state appended last to maximize KV caching) and per-observation token ceilings.

---

## 2. Project Structure

```
JO_harness/
├── backend/
│   ├── main.py                     
│   ├── config.py                   
│   ├── dependencies.py             
│   ├── routes/
│   ├── services/
│   ├── agent/
│   │   ├── runtime.py              
│   │   ├── openhands_runtime.py    
│   │   ├── fake_runtime.py         
│   │   ├── events.py               
│   │   ├── policies.py             # Guardrails & Policy Engine
│   │   └── compression.py          
│   ├── tools/
│   ├── mcp/
│   ├── a2a/
│   ├── models/
│   └── db/
├── scripts/
│   ├── load_benchmark.py           
│   └── run_evaluation.py           
├── evaluation/
│   ├── metrics.py                  
│   ├── judges.py                   
│   ├── trajectory.py               # Trajectory Evaluator
│   └── experiment.py               
├── docs/
│   └── ... 
├── docker/
│   ├── docker-compose.yml
│   └── ...
├── tests/
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 3. Phase 1 — Evaluation Foundation (Weeks 1–2)

**Goal:** Stand up the infrastructure backbone and the dual-track evaluation pipeline.

### 3.1 Docker Compose Stack (REQ-040)

Langfuse requires ClickHouse and MinIO. Redis is split to isolate caching from pub/sub.

```yaml
services:
  postgres:           # Application DB
  langfuse-db:        # Langfuse Postgres
  langfuse-clickhouse:# ClickHouse for Langfuse traces
  langfuse-minio:     # Object storage for Langfuse
  langfuse-web:       # Langfuse UI
  langfuse-worker:    # Langfuse async worker
  litellm:            # LiteLLM Proxy
  redis-cache:        # Redis (noeviction) for Celery
  redis-stream:       # Redis for event streaming
  searxng:            # Self-hosted meta-search
  authentik-server:   
  authentik-worker:   
  mailpit:            # Local SMTP testing
```

**Deliverables:** `docker-compose.yml`, `.env.example` (no PAT included), `config.yaml` for LiteLLM.

### 3.2 Evaluation Metrics & Trajectory Evaluator

1. **Track A (TriviaQA):** `semantic_similarity` (sentence-transformers), `length_ratio`, and Exact Match / F1.
2. **Track B (Trajectory):** Parse Langfuse traces to compute:
   - Plan adherence (ratio of tool calls matching the plan).
   - Tool-call schema validity rate.
   - Iteration counts and cost per task.
3. **LLM Judges:** `content_accuracy`, `form_language`, `completeness`. Configured to use the `reviewer` alias with `temperature: 0`.

### 3.3 Experiment Runner & CI

- Split evaluation into two stages: `generate` (produces traces/outputs) and `score` (runs judges/metrics).
- **CI Setup:** Replace local `.env` PAT with GitHub Actions OIDC or short-lived token. Run `pip-audit` for dependency scanning.

**Phase 1 Acceptance Milestone:**
> ✅ `docker-compose up -d` starts full Langfuse topology successfully.
> ✅ Track A (TriviaQA) and Track B (Agentic Suite) evaluators complete.
> ✅ GitHub Actions CI runs fast tier (Track A) on every push and fails if latency or EM regresses.

---

## 4. Phase 2 — Agent Core & API (Weeks 3–5)

### 4.1 Policy Engine & Guardrails (REQ-051, REQ-052)

Before any LLM call or tool execution, the synchronous Policy Engine evaluates:
1. **Budget Tracker:** Aborts if max iterations, token count, or wall-clock limits are exceeded.
2. **Thrash Breaker:** Aborts if the agent loops exactly the same action >3 times.
3. **Scrubber:** Strips PII and Secrets from Langfuse payloads.
4. **Tool Validator:** Blocks illegal arguments and enforces workspace containment (via `realpath`).

### 4.2 Core Tools & Egress (REQ-023, REQ-024, REQ-025, REQ-053, REQ-054)

- **File Tools:** Strict containment to workspace directories.
- **Shell Tools:** Deny-list and read-only rootfs enforcement.
- **Web Tools:** SSRF protection on `fetch_url` (blocking internal IP ranges). Egress policy restricts outbound connections.
- **Human-in-the-loop:** Required for any action failing the 'safe' heuristic (REQ-050).

### 4.3 Streaming & Concurrency (REQ-046)

- Transition from Redis pub/sub to **Redis Streams** for reliable SSE event delivery (prevents dropped events if client reconnects). Events include `seq` and `Last-Event-ID`.
- Agent events are persisted with `seq` column in `agent_events`.

**Phase 2 Acceptance Milestone:**
> ✅ Agent loop successfully completes Track B tasks.
> ✅ Policy Engine reliably blocks prompt injection, SSRF, and thrashing.
> ✅ SSE streaming via Redis Streams resumes cleanly without data loss.

---

## 5. Phase 3 — High-Value Extensions (Weeks 6–8)

**Scope Reduced:** To ensure quality, Phase 3 focuses solely on two high-leverage bets. The remaining features are deferred to the Backlog.

### 5.1 MCP Server (REQ-032)
- Implement FastMCP using the latest **2026-07-28** stateless specification.
- Expose all registered, guardrailed tools to external IDEs.

### 5.2 Retrieval-Augmented Generation (RAG)
- Implement pgvector-backed memory.
- Introduce citation validation to prevent hallucinated references.

---

## 6. Backlog (Deferred from Phase 3)

- **A2A Server:** Agent-to-Agent protocol and signed Agent Cards.
- **Gmail / Email Integration:** OAuth2 flows and email tools.
- **Sub-agents:** Complex multi-agent orchestration.
- **Production UI:** Open WebUI integration.
- **Kubernetes Manifests:** Prod deployments.

---

## 7. Dependency Summary

### Python (managed via `uv`)
```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic-settings
PyJWT                          # JWT validation (CVE-2024-33663 mitigation)
httpx
langfuse
litellm
openhands-sdk==1.24.0          # STRICT PINNING required
sentence-transformers
celery[redis]
```

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Model fails multi-tool chains | Agent loops infinitely | Escalation trigger (9B model); synchronous thrash breaker |
| Prompt Injection | Unauthorized actions executed | Workspace containment; Policy Engine strict validation |
| Token bloat | Massive latency & cost | Prefix stability routing; per-observation token ceilings |
| OpenHands SDK instability | Broken builds | Strict version pinning for all OpenHands sub-packages |
