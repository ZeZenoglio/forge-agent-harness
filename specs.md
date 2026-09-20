# specs.md

Modular Agent Platform with Model Cascade and Dual-Track Evaluation

### Tech Stack
- Python 3.14
- FastAPI
- OpenHands SDK (pinned)
- LiteLLM Proxy (Gateway)
- Langfuse (Observability)
- PostgreSQL & pgvector (Database & Memory)
- Authentik (OIDC Auth)
- Redis & Celery (Event streaming & Task queue)
- SearXNG (Web Search)

***

### 1. Overview

JO Harness is a modular, model-agnostic agent platform that runs locally on small open-source models (via Ollama) and can scale to cloud models. It wraps the OpenHands SDK inside a strict `AgentRuntime` protocol and enforces robust security guardrails (Policy Engine) before execution. The platform emphasizes "Prefix Stability" for token economics and implements a 4-tier model cascade to optimize costs and capabilities.

***

### 2. Functional Specifications

#### 2.1 User Stories

- As an **end-user**, I can chat with an agent via a UI, view its structured plan, and observe its tool executions in real-time.
- As an **end-user**, I can authenticate via email/password or SSO (Google/GitHub) managed by Authentik.
- As an **end-user**, I can explicitly approve or deny irreversible or dangerous tool actions requested by the agent.
- As an **administrator**, I can define budget caps and model routing aliases in the LiteLLM Proxy to control usage costs.
- As an **administrator**, I can view detailed hierarchical traces (planning, tool calls, final answers) in Langfuse to audit agent behavior.
- As a **developer**, I can run a fast Track A evaluation (TriviaQA) to quickly verify regression on every commit.
- As an **external system**, I can interact with the agent's tool catalog via the FastMCP (Model Context Protocol) server.

#### 2.2 Features

| Feature                 | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| **Model Cascade**       | Routes to `default-agent`, `utility-small`, `summarizer`, or `reviewer`.    |
| **Policy Engine**       | Synchronously blocks thrashing, enforces budgets, and scrubs PII/Secrets.   |
| **SSE Streaming**       | Real-time event streaming of agent loops to the frontend via Redis Streams. |
| **Sandboxed Tools**     | Secure file read/write, deny-listed shell execution, SSRF-protected web fetch. |
| **Dual-Track Eval**     | Track A (Deterministic Regression) & Track B (Agentic Trajectory Eval).     |
| **Sub-agent Delegation**| Agents can spawn child agents for specialized tasks (e.g., deep research).  |
| **RAG Memory**          | Document ingestion and vector retrieval using pgvector.                     |

***

### 3. Non-Functional Requirements
- **Performance**: Agent time-to-first-token (TTFT) and time-to-completion must stay within acceptable limits. Track A eval completes in under 2 mins.
- **Scalability**: Celery task queue enables concurrent multi-user agent execution and horizontal scaling of workers.
- **Security**: Complete sandbox containment (dropped Linux capabilities, read-only rootfs). No long-lived secrets in `.env`.
- **Reliability**: LiteLLM proxy handles automatic failovers if an upstream model deployment times out or hits quotas.
- **Maintainability**: `AgentRuntime` abstraction prevents lock-in to the OpenHands SDK. Strict version pinning ensures reproducible builds.

***

### 4. Interfaces

#### 4.1 Web UI (Chainlit / Open WebUI)
- **Chat Interface**: Supports SSE streaming, showing agent plans, typed event rendering, and tool calls as expandable steps.
- **Workspace Panel**: Shows the file tree and allows direct file inspection.
- **Artifact Inspector**: Previews generated files (code, markdown, PDF, images) and provides download links.
- **Settings Panel**: Allows users to switch model aliases dynamically.

#### 4.2 API (FastAPI)
- `POST /api/v1/auth/*`: Authentik JWT validation and syncing.
- `GET /api/v1/conversations`: List user sessions.
- `POST /api/v1/agent/run`: Submit an agent task (dispatched to Celery).
- `GET /api/v1/agent/stream/{id}`: Connect to SSE stream for a specific run.
- `POST /api/v1/agent/cancel`: Abort a running agent task.
- `GET /api/v1/artifacts/{id}`: Download generated artifacts.
- `GET /api/v1/tools/list`: Discover available tools.
