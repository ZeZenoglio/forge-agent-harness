# JO Harness — Stakeholder Demo 1

This document outlines a structured, step-by-step demonstration to walk stakeholders through the current capabilities of the JO Harness platform.

## Goal of the Demo
To prove that JO Harness is a secure, modular, enterprise-ready platform capable of running autonomous AI agents with strict safety guardrails, advanced memory capabilities, and deep interoperability.

---

### Step 1: The Core Architecture (Modularity)
**Objective:** Show that the platform is not permanently tied to one specific underlying framework, minimizing vendor lock-in.

* **What to show:** Open `backend/agent/openhands_runtime.py`.
* **Talking points:**
  * Notice how all agent actions flow through our `AgentRuntime` protocol. 
  * Currently, this is powered by OpenHands under the hood, but the product code never touches OpenHands directly. If we want to swap to a different open-source harness next year, we only replace this one adapter file.

### Step 2: The Policy Engine (Safety First)
**Objective:** Prove that the agent is sandboxed and cannot perform unauthorized or destructive actions on the host machine.

* **What to show:** Open `backend/agent/policies.py` and run a quick unit test (`uv run pytest tests/unit/test_policies.py`).
* **Talking points:**
  * **Path Containment:** The agent is physically locked to a specific workspace root (e.g. `/tmp/forge_workspace`). Any attempt to traverse out of this folder (`../../etc/passwd`) is caught and blocked by the `PolicyEngine`.
  * **Human-in-the-Loop (HITL):** Show the tool interception logic. If the agent tries to run destructive tools like `delete_file` or `send_email`, it raises an `ApprovalRequiredException`. Execution pauses until a human physically clicks "Approve".
  * **Hallucination Catching:** Explain the `validate_citations` method. If the agent generates a quote and claims it came from a document, our regex extracts it and verifies the quote physically exists in the source text. If not, the engine rejects the response.

### Step 3: Advanced Agent Capabilities (Memory & Orchestration)
**Objective:** Highlight the advanced features that make the agent smart and scalable.

* **What to show:** The `backend/tools/rag.py` and `backend/tools/delegation.py` files.
* **Talking points:**
  * **RAG (Retrieval-Augmented Generation):** The agent can self-manage its memory using semantic vector embeddings (`SentenceTransformer`). It uses `memorize` to store knowledge and `search_memory` to recall it logically.
  * **Parallel Sub-Agents:** When a task is too complex, the primary agent can spawn multiple *parallel* sub-agents (via `delegate_task`). Each sub-agent gets its own workspace context, works independently, and returns a rich trace of its logic trajectory back to the master agent.

### Step 4: Interoperability (MCP & A2A)
**Objective:** Show that the agent is a good citizen in the broader AI ecosystem.

* **What to show:** `backend/mcp/server.py` and `backend/api/routes_a2a.py`.
* **Talking points:**
  * **Model Context Protocol (MCP):** We expose the agent's tool catalog securely over stdio using FastMCP. Any standard IDE (like Cursor or Windsurf) can connect to this platform and utilize our sandboxed tools directly.
  * **Agent-to-Agent (A2A):** We conform to the draft A2A JSON-RPC specification. External agents from entirely different platforms can send tasks to our agent and get streaming SSE updates on progress.

### Step 5: Enterprise Infrastructure
**Objective:** Prove that this isn't just a prototype, but a system ready for production scale.

* **What to show:** The `docker/docker-compose.yml` and the `k8s/` folder.
* **Talking points:**
  * For local dev, a single `docker-compose` brings up Postgres (with pgvector), Redis, LiteLLM, and an SMTP mock server (Mailpit).
  * We also have auto-generated Kubernetes manifests for every component. Whether we deploy on local Minikube or cloud-based GKE, the services are fully decoupled and scalable.

---

## Wrap Up / Q&A
* "As you can see, Phase 1 through 3 of our requirements are now completed. We have a robust, secure backend that handles agent orchestration, memory, and interoperability. The next natural step is to attach the React frontend so we can interact with it visually."
