# JO Harness — Stakeholder Demo Script

**Presenter Note:** This script is designed for a 10-15 minute live demonstration to stakeholders. The goal is to prove the platform is secure, modular, visually interactive via API, and production-ready, even before the final React frontend is built.

---

## 🛠️ Prep Work (Before the meeting starts)
1. **Start the Database & SMTP Mock:**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d postgres mailpit
   ```
2. **Start the API Server:**
   ```bash
   uv run uvicorn backend.api.main:app --reload
   ```
3. **Open Browser Tabs:**
   - Tab 1: `docs/architecture.html` (The Architecture Diagram)
   - Tab 2: `http://localhost:8000/docs` (FastAPI Swagger UI)
   - Tab 3: `http://localhost:8025` (Mailpit Web UI)

---

## 🎙️ The Presentation

### Introduction (Tab 1: Architecture)
**Action:** Open Tab 1 showing the interactive `architecture.html`.

**Script:**
> "Welcome everyone. Today we are demonstrating the core engine of the JO Harness platform. Before we look at the live system, I want to show you our architecture diagram.
> 
> As you can see, our system is entirely modular. The most critical decision we made was to isolate our product code from the underlying AI framework (like OpenHands). We communicate entirely through an `AgentRuntime` protocol. If the AI landscape shifts tomorrow, we can swap out the underlying agent framework without touching our APIs, databases, or frontend."

### Step 1: The API in Action (Tab 2: Swagger UI)
**Action:** Switch to Tab 2 (`http://localhost:8000/docs`).

**Script:**
> "Let's look at the live system. What you are seeing here is the interactive API dashboard that powers the platform. This is fully automatically generated from our code.
> 
> Every capability of our agent—running tasks, streaming responses, and managing memory—is exposed here. This means the agent isn't just a chatbot; it can be integrated into any existing enterprise system, triggered by webhooks, or controlled programmatically."

**Action:** Expand the `/api/v1/a2a` (Agent-to-Agent) routes to show them on screen.
> "For example, look at our A2A (Agent-to-Agent) endpoints. We comply with the draft JSON-RPC specification. This means our agent can receive tasks from *other* external agents across different platforms, acting as a specialized worker in a larger multi-agent ecosystem."

### Step 2: Safety & The Policy Engine (Terminal)
**Action:** Bring up your terminal.

**Script:**
> "A major concern with autonomous agents is safety. We've built a strict `PolicyEngine` that intercepts everything the agent tries to do. 
> Let's look at how it catches LLM hallucinations."

**Action:** Run the tests: `uv run pytest tests/unit/test_policies.py`
> "Here, our tests are passing immediately. The policy engine uses a Human-in-the-Loop system. If the agent tries to delete a file, or send an email, it is physically paused and blocked until a human clicks 'Approve'. Furthermore, if the agent hallucinates a fake quote and claims it came from a document, our engine scans the text and rejects the response. Safety is baked in at the lowest level."

### Step 3: Enterprise Readiness (Tab 3: Mailpit)
**Action:** Switch to Tab 3 (`http://localhost:8025`).

**Script:**
> "Finally, let's talk about real-world connectivity. We've just implemented an Email Integration tool allowing the agent to draft and send emails.
> 
> To develop this safely, we use a local SMTP testing server called Mailpit. When the agent sends an email, it gets caught right here in this local dashboard. This proves we can integrate with external tools seamlessly.
> 
> Beyond this, we have already generated full Kubernetes manifests for every piece of this infrastructure, meaning we are ready to deploy to production at any time."

### Wrap Up
**Script:**
> "To summarize: Phase 1 through 3 are complete. We have a secure, interoperable, memory-capable agent backend. 
> 
> Our next step—Phase 4—is attaching a rich React frontend to this API, which will give our end users a beautiful, chat-like interface to collaborate with the agent. 
> 
> Any questions?"
