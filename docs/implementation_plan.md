# JO Harness — Implementation Plan

**Date:** 18 September 2026  
**Version:** 1.0  
**Spec reference:** [sdd_requirements.csv](file:///Users/josezenogliodeoliveira/GitHub%20Repos/JO_harness/docs/sdd_requirements.csv)  
**Research reference:** [open_agent_harness_findings.md](file:///Users/josezenogliodeoliveira/GitHub%20Repos/JO_harness/docs/open_agent_harness_findings.md)

---

## 0. Executive Summary

JO Harness is a modular, model-agnostic agent platform built on **OpenHands SDK** (agent harness), **FastAPI** (API layer), **LiteLLM Proxy** (model gateway), **Langfuse** (observability & evaluation), and **PostgreSQL** (application data). It runs locally on small open-source models via **Ollama** and can be scaled to Kubernetes with cloud models by only changing LiteLLM configuration.

The build is organized into **three phases**, with the evaluation suite built *first* (Phase 1) so that every subsequent change to the agent is immediately measurable.

---

## 1. Key Technical Decisions

### 1.1 Default SLM: `qwen3.5:4b`

Based on 2026 benchmarks across the ~4B parameter class:

| Model | Tool Calling | Reasoning | Multimodal | License |
|---|---|---|---|---|
| **Qwen3.5 4B** ✅ | Aggressive, proactive | Best-in-class (4B) | Text + Image | Apache 2.0 |
| Gemma 4 E4B | Conservative | Good | Audio + Vision | Apache 2.0 |
| Nemotron-3-Nano 4B | Excellent | Good | Text only | NVIDIA OML |

**Qwen3.5 4B wins** for our use case because:
- Most reliable tool-calling at this size — it actively reaches for tools rather than guessing from training data
- Strongest pure-text reasoning and coding capability
- Apache 2.0 license (no restrictions)
- Native `thinking` mode for chain-of-thought planning
- Available on Ollama: `ollama pull qwen3.5:4b`

> **Fallback:** Gemma 4 E4B can serve as the multimodal specialist model (for image interpretation) alongside Qwen3.5 as the primary reasoner.

### 1.2 Benchmark Dataset: TriviaQA (subset)

For the evaluation suite, we use a **200-item subset of TriviaQA** from Hugging Face (`mandarjoshi/trivia_qa`):

- **650k+ Q&A triples** with evidence passages — broad general knowledge
- Open-domain format (not multiple choice) — forces the agent to generate free-form answers, which is more realistic than MMLU's multiple-choice format
- Answer strings are short enough for reliable semantic similarity computation
- Well-established, low contamination risk when testing SLMs

We'll sample 200 items across diverse categories for a manageable but statistically meaningful evaluation run.

### 1.3 Harness Choice: OpenHands SDK

OpenHands SDK provides out-of-the-box:
- ✅ Event-driven agent loop with pause/resume
- ✅ Planning before execution
- ✅ Sub-agent delegation (via `openhands.tools`)
- ✅ Context compression (condenser patterns: rolling summary, recursive, agent-controlled)
- ✅ MCP native integration (`openhands.sdk.mcp`)
- ✅ Artifact tracking (append-only event log)
- ✅ Sandbox execution (Action Execution Server in Docker)
- ✅ Python SDK — direct FastAPI integration, no subprocess bridges

This means the core agentic behaviors you described (plan → iterate → tool/sub-agent → shared state → conclude) are **already abstracted by the harness**. Our job is to configure, extend, and wrap them behind our `AgentRuntime` interface.

### 1.4 Interoperability Stack

| Protocol | Purpose | Implementation |
|---|---|---|
| **MCP** (Model Context Protocol) | Expose agent tools to external clients (IDEs, other agents) | FastMCP server alongside FastAPI |
| **A2A** (Agent-to-Agent Protocol) | Allow external agents to delegate tasks to our agent | A2A JSON-RPC endpoint + Agent Card at `/.well-known/agent.json` |
| **LiteLLM** | Model-agnostic LLM calls; gateway for Ollama/cloud switching | LiteLLM Proxy container |

---

## 2. Project Structure

```
JO_harness/
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory
│   ├── config.py                   # Settings (pydantic-settings)
│   ├── dependencies.py             # DI: AgentRuntime, DB, LiteLLM client
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Register, login, Google OAuth
│   │   ├── conversations.py        # CRUD conversations
│   │   ├── agent.py                # Run/stream/cancel agent
│   │   ├── artifacts.py            # List/download artifacts
│   │   ├── tools.py                # List available tools
│   │   └── health.py               # Healthcheck
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py        # Orchestrates agent runs
│   │   ├── auth_service.py         # JWT + Google OAuth logic
│   │   ├── user_service.py         # User CRUD
│   │   ├── conversation_service.py # Conversation CRUD
│   │   ├── artifact_service.py     # Artifact storage
│   │   └── evaluation_service.py   # Runs evals programmatically
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── runtime.py              # AgentRuntime protocol
│   │   ├── openhands_runtime.py    # OpenHands implementation
│   │   ├── fake_runtime.py         # Test double
│   │   ├── events.py               # Canonical event model
│   │   ├── policies.py             # Tool approval policies
│   │   └── compression.py          # Context compression strategies
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py             # Tool registry
│   │   ├── file_tools.py           # read, write, edit, search
│   │   ├── shell_tools.py          # execute_shell
│   │   ├── web_tools.py            # web_search, fetch_url
│   │   ├── code_tools.py           # execute_code sandbox
│   │   ├── doc_tools.py            # PDF, DOCX, LaTeX generation
│   │   ├── rag_tools.py            # ingest, query via pgvector
│   │   ├── image_tools.py          # analyze_image (multimodal)
│   │   ├── email_tools.py          # Gmail connector
│   │   └── extraction_tools.py     # Structured data extraction
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py               # MCP server exposing tools
│   ├── a2a/
│   │   ├── __init__.py
│   │   ├── server.py               # A2A JSON-RPC endpoint
│   │   └── agent_card.py           # Agent Card generator
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                 # SQLAlchemy base, mixins
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── agent_run.py
│   │   ├── agent_event.py
│   │   ├── tool_call.py
│   │   ├── artifact.py
│   │   └── model_config.py
│   ├── schemas/
│   │   └── ...                     # Pydantic request/response schemas
│   └── db/
│       ├── __init__.py
│       ├── session.py              # Async SQLAlchemy session
│       └── migrations/             # Alembic
│           └── ...
├── frontend/
│   ├── chainlit_app.py             # Phase 2: Chainlit UI
│   └── react/                      # Phase 3: React + Vite app
│       └── ...
├── scripts/
│   ├── load_benchmark.py           # Download TriviaQA → Langfuse dataset
│   ├── run_evaluation.py           # Run agent vs. benchmark, score, report
│   └── seed_litellm.py             # Seed LiteLLM config via API
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py                  # Semantic similarity, length ratio
│   ├── judges.py                   # LLM-as-Judge prompt templates + runners
│   └── experiment.py               # Experiment orchestration
├── docs/
│   ├── open_agent_harness_findings.md
│   ├── sdd_requirements.csv
│   ├── implementation_plan.md      # This file
│   └── MODELS.md                   # Tested models, aliases, quirks
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml      # Dev overrides (hot reload, volumes)
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── litellm/
│   │   └── config.yaml             # LiteLLM Proxy configuration
│   ├── searxng/
│   │   └── settings.yml            # SearXNG engine configuration
│   └── authentik/
│       └── ...                     # Authentik flow customizations
├── k8s/                            # Phase 3: Kubernetes manifests
│   └── ...
├── data/
│   └── benchmark/                  # Downloaded benchmark data
├── notebooks/
│   └── exploration.ipynb
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .python-version
└── README.md
```

---

## 3. Phase 1 — Evaluation Foundation (Weeks 1–2)

**Goal:** Before writing any agent code, stand up the infrastructure backbone and a complete evaluation pipeline that can measure any agent implementation we plug in later.

### 3.1 Docker Compose Stack (REQ-040)

Services:
```yaml
services:
  postgres:           # Application DB (port 5432)
  langfuse-db:        # Langfuse's own Postgres (port 5433)
  langfuse:           # Langfuse web + worker (port 3000)
  litellm:            # LiteLLM Proxy (port 4000)
  redis:              # Celery broker + Authentik cache (port 6379)
  searxng:            # Self-hosted meta-search (port 8080)
  authentik-server:   # OIDC identity provider (port 9000)
  authentik-worker:   # Authentik background tasks
```

Ollama is assumed running on the host (`host.docker.internal:11434` or `localhost:11434`).

**Steps:**
1. Write `docker-compose.yml` with all services + networks + volumes.
2. Write `.env.example` with all required env vars.
3. Write `docker/litellm/config.yaml` with:
   - Model alias `default-agent` → `ollama/qwen3.5:4b`
   - Model alias `reviewer` → `ollama/qwen3.5:4b` (same model for now; separate alias so we can swap later)
   - Langfuse callback configuration
4. Write `docker/searxng/settings.yml` with Google, Bing, DuckDuckGo engines enabled and rate limiting configured.
5. Configure Authentik with an initial OIDC application for JO Harness.
6. Verify: `docker-compose up -d` → all services healthy.
7. Verify: Langfuse UI accessible at `localhost:3000`.
8. Verify: LiteLLM responds to `curl http://localhost:4000/v1/models`.
9. Verify: SearXNG responds to `curl 'http://localhost:8080/search?q=test&format=json'`.
10. Verify: Authentik login page at `localhost:9000`.

**Deliverables:** `docker-compose.yml`, `.env.example`, `docker/litellm/config.yaml`, `docker/searxng/settings.yml`

---

### 3.2 Benchmark Dataset Ingestion (REQ-007)

**Steps:**
1. Write `scripts/load_benchmark.py`:
   - Download TriviaQA from Hugging Face (`datasets` library or direct download).
   - Sample 200 items stratified by category.
   - Clean each item: extract question, extract one canonical answer (TriviaQA has aliases — pick the shortest, most canonical one).
   - Upload to Langfuse as a Dataset named `"triviaqa-v1"` with items containing `input`, `expected_output`, and `metadata`.
2. Store raw downloaded data in `data/benchmark/` for reproducibility.
3. Add `datasets` (HuggingFace) and `langfuse` to project dependencies.

**Deliverables:** `scripts/load_benchmark.py`, `data/benchmark/triviaqa_200.jsonl`

---

### 3.3 Evaluation Metrics (REQ-009, REQ-010)

**Steps:**
1. Write `evaluation/metrics.py`:
   - `semantic_similarity(expected: str, generated: str) -> float` — uses `sentence-transformers` with `all-MiniLM-L6-v2` (runs locally, no GPU required).
   - `length_ratio(expected: str, generated: str) -> float` — character-based ratio.
2. Add `sentence-transformers` to project dependencies.
3. Unit tests in `tests/unit/test_metrics.py`.

**Deliverables:** `evaluation/metrics.py`, unit tests

---

### 3.4 LLM-as-Judge Evaluators (REQ-011, REQ-012, REQ-013)

**Steps:**
1. Write `evaluation/judges.py` with three judge functions, each:
   - Constructs a structured prompt with the rubric, question, expected answer, and generated answer.
   - Calls the LLM via LiteLLM (using the `reviewer` alias).
   - Parses the JSON response `{"score": int, "reasoning": str}`.
   - Returns the score + reasoning.

2. **Judge 1 — Content Accuracy** (REQ-011):
   ```
   You are an evaluation judge. Given a QUESTION, an EXPECTED ANSWER, and a
   GENERATED ANSWER, score the generated answer's factual accuracy on a 1-5 scale.

   Scoring rubric:
   1 = Completely wrong or irrelevant to the question
   2 = Partially correct but contains major factual errors or gaps
   3 = Mostly correct with minor factual errors
   4 = Correct with good coverage of key facts
   5 = Fully correct, comprehensive, and well-supported

   Respond ONLY with JSON: {"score": <1-5>, "reasoning": "<brief explanation>"}
   ```

3. **Judge 2 — Form & Language** (REQ-012):
   ```
   You are an evaluation judge. Given a QUESTION and a GENERATED ANSWER,
   score the answer's clarity, structure, grammar, and language quality on a 1-5 scale.

   Scoring rubric:
   1 = Incoherent, unreadable, or garbled text
   2 = Poor structure, frequent grammar errors, hard to follow
   3 = Readable but awkward phrasing or poor organization
   4 = Well-written with only minor stylistic issues
   5 = Excellent clarity, natural flow, and professional structure

   Respond ONLY with JSON: {"score": <1-5>, "reasoning": "<brief explanation>"}
   ```

4. **Judge 3 — Completeness & Gaps** (REQ-013):
   ```
   You are an evaluation judge. Given a QUESTION, an EXPECTED ANSWER, and a
   GENERATED ANSWER, score whether the generated answer addresses all parts
   of the question without significant omissions. Score on a 1-5 scale.

   Scoring rubric:
   1 = Misses the question entirely or answers a different question
   2 = Addresses only a small fraction of what was asked
   3 = Covers the main point but omits significant sub-parts
   4 = Covers most aspects with only minor gaps
   5 = Fully addresses every part of the question

   Respond ONLY with JSON: {"score": <1-5>, "reasoning": "<brief explanation>"}
   ```

5. Each judge call is traced in Langfuse as its own generation span.
6. Unit tests with mocked LLM responses.

**Deliverables:** `evaluation/judges.py`, judge prompt templates, unit tests

---

### 3.5 Experiment Runner (REQ-008)

**Steps:**
1. Write `evaluation/experiment.py` — the orchestration module:
   - Loads dataset items from Langfuse.
   - For each item: calls the agent (via a pluggable callable), gets the generated answer.
   - Computes: semantic similarity, length ratio.
   - Runs all 3 judges.
   - Records all scores back to Langfuse dataset experiment.
2. Write `scripts/run_evaluation.py` — CLI entry point:
   - `--dataset triviaqa-v1`
   - `--experiment-name "baseline-qwen3.5-v1"`
   - `--tier fast|full` (fast = 20 items for CI; full = 200 items for pre-deploy/manual)
   - `--workers 4` (concurrent evaluation)
   - `--agent-endpoint http://localhost:8000/api/v1/agent/run` (or direct function call)
3. For Phase 1, the "agent" is a **stub**: just calls LiteLLM directly with the question (no tools, no planning). This validates the evaluation pipeline independently of the agent.
4. Tag 20 items in the dataset as `smoke` for the fast tier.
5. Output: per-item scores in Langfuse + a summary printed to console.
6. Fast tier must complete in <2 minutes to be CI-viable.

**Deliverables:** `evaluation/experiment.py`, `scripts/run_evaluation.py`

---

### Phase 1 Acceptance Milestone

> ✅ `docker-compose up -d` starts Postgres, Langfuse, LiteLLM, Redis, SearXNG, Authentik  
> ✅ `ollama pull qwen3.5:4b` model is available  
> ✅ `python scripts/load_benchmark.py` creates dataset in Langfuse with 200 items (20 tagged `smoke`)  
> ✅ `python scripts/run_evaluation.py --tier fast` completes in <2 min with 5 metrics  
> ✅ `python scripts/run_evaluation.py --tier full` runs all 200 items with full scoring  
> ✅ Langfuse UI shows traces with structured spans, scores, and experiment results  
> ✅ LiteLLM → Langfuse integration works (LLM calls visible as generations)  
> ✅ SearXNG returns JSON search results  
> ✅ Authentik login page is accessible and can register a test user

---

## 4. Phase 2 — Agent Core & API (Weeks 3–5)

### 4.1 Database Schema (REQ-014)

Using SQLAlchemy 2.0 + Alembic:

```
users (id, authentik_sub, email, name, avatar_url, created_at, updated_at)
conversations (id, user_id FK, title, created_at, updated_at)
messages (id, conversation_id FK, role, content, created_at)
agent_runs (id, conversation_id FK, status, input, output, model_alias, celery_task_id, started_at, completed_at)
agent_events (id, run_id FK, type, data JSONB, timestamp)
tool_calls (id, run_id FK, tool_name, input JSONB, output JSONB, status, started_at, completed_at)
artifacts (id, run_id FK, conversation_id FK, name, mime_type, size_bytes, storage_path, created_at)
model_configs (id, alias, provider, model_name, is_default, created_at)
```

Note: `users.authentik_sub` stores the OIDC subject claim from Authentik. No `password_hash` — password management is handled entirely by Authentik.

**Deliverables:** SQLAlchemy models, Alembic initial migration

---

### 4.2 Authentication via Authentik (REQ-035, REQ-036, REQ-048)

**Steps:**
1. Configure Authentik OIDC application for JO Harness (client_id, client_secret, redirect URIs).
2. Implement FastAPI dependency `get_current_user` that:
   - Extracts Bearer token from Authorization header.
   - Validates JWT signature against Authentik's JWKS endpoint (`http://authentik:9000/application/o/<app>/jwks/`).
   - Extracts `sub`, `email`, `name`, `picture` from claims.
   - Creates/updates local user record in Postgres on first/subsequent login.
3. Authentik handles all user-facing flows:
   - Registration (email/password)
   - Login
   - Password reset (email link)
   - Profile editing
   - Optional: Google/GitHub social login (configured as federated sources in Authentik)
4. User ID is injected into every Langfuse trace (REQ-037).
5. Frontend redirects unauthenticated users to Authentik's login page.

**Deliverables:** `auth_service.py`, `auth.py` routes (token validation only), Authentik OIDC config

---

### 4.3 AgentRuntime Abstraction (REQ-017)

```python
# backend/agent/runtime.py
from typing import Protocol, AsyncIterator

class AgentRuntime(Protocol):
    async def create_session(self, config: SessionConfig) -> str: ...
    async def run(self, session_id: str, message: str) -> AsyncIterator[AgentEvent]: ...
    async def steer(self, session_id: str, directive: str) -> None: ...
    async def cancel(self, session_id: str) -> None: ...
    async def approve_tool_call(self, approval_id: str) -> None: ...
    async def close_session(self, session_id: str) -> None: ...
```

**Deliverables:** `runtime.py` (protocol), `openhands_runtime.py`, `fake_runtime.py`

---

### 4.4 OpenHands Integration (REQ-016, REQ-018, REQ-019, REQ-020)

**Steps:**
1. Install `openhands-sdk`.
2. Implement `OpenHandsRuntime`:
   - `create_session` → instantiate OpenHands Agent + Conversation + Workspace.
   - `run` → feed message, iterate event stream, yield `AgentEvent`s.
   - Map OpenHands events to our canonical event model.
3. Configure **planning**: system prompt instructs the agent to emit a plan before acting.
4. Configure **iterative loop**: shared state dict updated at each step; agent evaluates sufficiency.
5. Configure **context compression**: register a condenser (rolling summary) triggered at 80% context fill.
6. Configure **tool registry**: register core tools (file, shell, web) with OpenHands.
7. Configure **LiteLLM**: point OpenHands' LLM layer at our LiteLLM Proxy (`http://litellm:4000`).

**Deliverables:** `openhands_runtime.py`, agent system prompt, compression config

---

### 4.5 Core Tools (REQ-023, REQ-024, REQ-025, REQ-026)

Register with OpenHands via its custom tool API:

| Tool | Module | Actions |
|---|---|---|
| File Tools | `file_tools.py` | `read_file`, `write_file`, `edit_file`, `search_files`, `list_directory` |
| Shell Tools | `shell_tools.py` | `execute_shell` (with deny-list policy) |
| Web Tools | `web_tools.py` | `web_search` (via SearXNG at `http://searxng:8080`), `fetch_url` |

All tools are sandboxed to the workspace root. Shell commands are subject to a deny-list policy (`policies.py`).

**Deliverables:** Tool modules, policy config, tool tests

---

### 4.6 FastAPI Routes & Streaming (REQ-033, REQ-021, REQ-046)

**Endpoints:**
```
GET    /api/v1/auth/me                       # Current user from Authentik JWT
GET    /api/v1/conversations
POST   /api/v1/conversations
GET    /api/v1/conversations/{id}
POST   /api/v1/conversations/{id}/messages
POST   /api/v1/agent/run                    # Dispatches Celery task, returns task_id
GET    /api/v1/agent/stream/{session_id}    # SSE streaming (reads from Celery task events)
GET    /api/v1/agent/status/{task_id}       # Task status (pending/running/completed/failed)
POST   /api/v1/agent/cancel/{session_id}
POST   /api/v1/agent/approve/{approval_id}
GET    /api/v1/artifacts/{id}
GET    /api/v1/tools
GET    /api/v1/health
```

Agent runs are dispatched as **Celery tasks** via Redis broker. The SSE endpoint reads events published by the Celery task through Redis pub/sub.

SSE stream emits typed events:
```json
{"type": "plan", "data": {"steps": [...]}}
{"type": "tool_call", "data": {"tool": "web_search", "input": {...}}}
{"type": "observation", "data": {"tool": "web_search", "output": {...}}}
{"type": "delta", "data": {"text": "The answer is..."}}
{"type": "answer", "data": {"text": "...", "artifacts": [...]}}
{"type": "error", "data": {"message": "..."}}
```

**Deliverables:** All route modules, SSE streaming logic, Celery task definitions, request/response schemas

---

### 4.7 Chainlit UI (REQ-038)

**Steps:**
1. Mount Chainlit within the FastAPI app using `chainlit.utils.mount_chainlit`.
2. Configure Authentik OIDC header auth passthrough from FastAPI → Chainlit.
3. Wire Chainlit's message handler to dispatch agent runs via Celery.
4. Display tool calls as expandable Chainlit Steps.
5. Display artifacts as downloadable files in the chat.
6. Stream token-by-token deltas for reduced perceived latency.
7. Support concurrent multi-user sessions (each user gets independent Celery tasks).

**Deliverables:** `frontend/chainlit_app.py`, Chainlit config

---

### 4.8 Re-run Evaluation with Real Agent

Once the agent is functional:
1. Update `scripts/run_evaluation.py` to point at the real agent API endpoint.
2. Run: `python scripts/run_evaluation.py --experiment-name "openhands-qwen3.5-v1"`
3. Compare results against the Phase 1 stub baseline in Langfuse.

---

### Phase 2 Acceptance Milestone

> ✅ FastAPI starts with all endpoints documented at `/docs`  
> ✅ User can register/login via Authentik (email/password + optional social SSO)  
> ✅ Password reset and profile management work via Authentik self-service  
> ✅ Chainlit chat UI at `/chat` with streaming responses  
> ✅ Multiple users can run concurrent agent sessions (Celery workers)  
> ✅ Agent plans before executing, uses tools, iterates, and concludes  
> ✅ Context compression triggers on long sessions  
> ✅ All agent events stored in Postgres + traced in Langfuse  
> ✅ Evaluation experiment shows measurable improvement over the stub baseline  
> ✅ Per-user tracking visible in Langfuse  

---

## 5. Phase 3 — Extension, Interoperability & Production (Weeks 6–10)

### 5.1 Extended Tools (REQ-027–031, REQ-043–045)

| Tool | Description | Implementation |
|---|---|---|
| Code execution | Python/JS in disposable Docker container | `code_tools.py` + sandbox Dockerfile |
| Document generation | PDF (via WeasyPrint), DOCX (via python-docx), LaTeX (via texlive) | `doc_tools.py` |
| RAG | Ingest → chunk → embed → pgvector; query → top-k retrieval | `rag_tools.py` + pgvector |
| Image interpretation | Multimodal model (Gemma 4 E4B) for vision tasks | `image_tools.py` |
| Gmail connector | Authentik-brokered OAuth2 → Gmail API read/search/draft | `email_tools.py` |
| Sub-agent delegation | Spawn specialized sub-agents via OpenHands delegation tool | `openhands_runtime.py` extension |
| Extraction | LLM + structured output for data extraction from text/PDF/images | `extraction_tools.py` |
| Research agent | Multi-step web research → synthesis → report artifact | `research_tools.py` (compound tool) |

### 5.2 MCP Server (REQ-032)

- Implement using **FastMCP** (Python MCP SDK).
- Expose all registered tools via `tools/list` and `tools/call`.
- Support stdio transport (for IDE integration) and HTTP/SSE (for remote clients).
- Optional: enable/disable via `MCP_ENABLED=true` in `.env`.

### 5.3 A2A Server (REQ-034)

- Serve Agent Card at `/.well-known/agent.json`.
- JSON-RPC 2.0 endpoint at `/a2a` accepting `tasks/send`, `tasks/get`, `tasks/cancel`.
- Task lifecycle: submitted → working → completed/failed.
- SSE streaming for task progress updates.
- Optional: enable/disable via `A2A_ENABLED=true` in `.env`.

### 5.4 Production Frontend (REQ-039)

**Primary option: Customize Open WebUI**
- Open WebUI has a native FastAPI backend — ideal architectural fit.
- Built-in Ollama integration, Pipes/Actions extensibility.
- Wire our agent API into Open WebUI via its custom Pipe system.
- Auth delegates to Authentik via OIDC.

**Fallback option: Custom React + Vite**
- Build from scratch if Open WebUI's customization model is too constraining.
- Features: streaming chat, workspace file tree, artifact inspector, conversation branching, model selector, settings panel.
- Consumes the same FastAPI endpoints as Chainlit.

### 5.5 Kubernetes Manifests (REQ-041)

- Multi-stage Dockerfiles for backend and frontend.
- Helm chart or raw manifests for: FastAPI deployment, Postgres StatefulSet, LiteLLM deployment, Langfuse deployment.
- HPA for FastAPI workers.
- ConfigMaps and Secrets for configuration.

### 5.6 Advanced LiteLLM Features (REQ-002, REQ-003)

- Multiple model aliases with routing rules.
- Multi-deployment load balancing for a single alias.
- Automatic failover on quota/error.
- Per-user budgets via LiteLLM virtual keys.

---

## 6. Dependency Summary

### Python (managed via `uv`)
```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic-settings
python-jose[cryptography]      # JWT validation (Authentik tokens)
httpx                           # HTTP client for Authentik JWKS, SearXNG
langfuse
litellm
openhands-sdk
sentence-transformers            # Semantic similarity (all-MiniLM-L6-v2)
celery[redis]                    # Task queue for concurrent agent runs
chainlit
python-multipart
python-docx
weasyprint
```

### Infrastructure (Docker)
```
postgres:16                      # Application DB
postgres:16 (second instance)    # Langfuse DB (port 5433)
langfuse/langfuse:latest         # Observability & evaluation
ghcr.io/berriai/litellm:main-latest  # LLM gateway
redis:7-alpine                   # Celery broker + Authentik cache
goauthentik.io/server:latest     # OIDC identity provider
goauthentik.io/proxy:latest      # Authentik outpost (optional)
searxng/searxng:latest           # Self-hosted meta-search
```

### External
```
Ollama (host-installed, running qwen3.5:4b)
```

---

## 7. Resolved Design Decisions

All initial open questions have been resolved:

| # | Decision | Resolution |
|---|---|---|
| 1 | **Authentication** | **Authentik** (self-hosted OIDC). No GCP project needed. Authentik handles email/password, password reset, profile mgmt, and optional Google/GitHub social login. FastAPI only validates JWTs. |
| 2 | **Web search** | **SearXNG** (self-hosted Docker). Aggregates Google, Bing, DuckDuckGo results. No API keys needed. |
| 3 | **Sandbox model** | Agent tools execute inside the docker-compose containers. For Phase 3 code execution tool, disposable sibling containers are spawned via Docker socket. |
| 4 | **Production frontend** | **Customize Open WebUI** (FastAPI-native, Ollama-integrated). Fallback to custom React+Vite if needed. |
| 5 | **Evaluation frequency** | **Tiered**: fast tier (20 items, <2 min) runs in CI on every push/PR. Full tier (200 items) triggered manually or for pre-deployment. |
| 6 | **Embedding model** | **sentence-transformers** (`all-MiniLM-L6-v2`). CPU-only, no GPU required. |
| 7 | **Multi-user** | **Yes, from Phase 2**. Celery + Redis task queue enables concurrent agent runs. K8s-ready scaling by design. |

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Qwen3.5 4B tool-calling reliability with complex multi-tool chains | Agent fails mid-task | Configurable escalation to larger model; max-retries on tool-call parse failures |
| OpenHands SDK API instability (actively developed) | Breaking changes during build | Pin SDK version; wrap behind AgentRuntime abstraction |
| Context window exhaustion on long tasks (4B model = ~8k context) | Lost context, incoherent answers | Aggressive compression; configurable context budget; task decomposition via sub-agents |
| LLM-as-Judge scoring variance with a 4B model as judge | Noisy evaluation scores | Use `reviewer` alias that can be pointed at a stronger model; track judge trace quality in Langfuse |
| Docker-in-Docker complexity for sandboxed code execution | DevOps overhead | Start with same-container execution; isolate later |

---

## 9. Timeline Summary

| Phase | Weeks | Key Deliverables |
|---|---|---|
| **Phase 1** | 1–2 | Docker Compose (all services), LiteLLM + Langfuse + SearXNG + Authentik + Redis, benchmark dataset, tiered evaluation suite (5 metrics), baseline experiment |
| **Phase 2** | 3–5 | Postgres schema, Authentik OIDC auth, Celery task queue, AgentRuntime + OpenHands, core tools, FastAPI API, SSE streaming, Chainlit UI, agent evaluation run |
| **Phase 3** | 6–10 | Extended tools, MCP server, A2A server, Open WebUI/React frontend, Kubernetes manifests, advanced LiteLLM routing, RAG, Gmail, sub-agents |

---

## 10. Success Criteria

The project is successful when:

1. **A user can chat with the agent** via Chainlit (Phase 2) or React (Phase 3), and the agent plans, uses tools, and delivers answers with visible reasoning.
2. **The same agent can be consumed** via the REST API, as an MCP server, via A2A protocol, or through the UI — all hitting the same `AgentRuntime`.
3. **Switching from Ollama to a cloud model** requires changing only `docker/litellm/config.yaml` — zero code changes.
4. **Every agent call is fully traced** in Langfuse with structured spans, costs, and user attribution.
5. **The evaluation suite** produces reproducible, quantified quality metrics across 5 dimensions, and regressions are detectable experiment-over-experiment.
6. **The tool catalog is extensible** — adding a new tool requires only writing a single module in `backend/tools/` and registering it.
