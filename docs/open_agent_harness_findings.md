# Choosing an Open, Model-Agnostic Agent Harness

**Research date:** 18 September 2026  
**Objective:** Select a pre-made agent harness for building a local, open-model alternative to Claude Code and a deployable agent platform using FastAPI, PostgreSQL, Chainlit or React, LiteLLM, Langfuse, containers, and a broad tool catalog.

---

## Executive conclusion

For the complete containerized application, the recommended first choice is **OpenHands SDK** as the agent harness, with **FastAPI** as the service layer and **LiteLLM Proxy** as the sole model gateway.

**Pi** remains the best choice for a highly hackable local terminal agent where owning and modifying the agent loop is the main goal. **Cline SDK** is the strongest middle-ground option if the agent runtime is to be implemented in TypeScript rather than Python.

The recommended mapping is:

```text
Personal workstation harness        -> Pi
Deployable Python agent platform    -> OpenHands SDK
TypeScript product/runtime          -> Cline SDK
```

The preferred implementation should place a small, framework-neutral `AgentRuntime` interface around the selected harness. This avoids replacing one kind of model-vendor lock-in with harness lock-in.

---

## 1. The requirement

The target is not simply a coding assistant. It is an open, embeddable, Claude Code-style agent system with:

- open-weight and proprietary model interchangeability;
- local execution through Ollama, vLLM, SGLang, or similar infrastructure;
- a substantial catalog of typed tools;
- controlled shell and filesystem access;
- persistent sessions and application state;
- a Chainlit prototype or custom React frontend;
- a FastAPI backend;
- PostgreSQL for durable application data;
- LiteLLM for model routing, keys, budgets, and governance;
- Langfuse for traces, evaluations, latency, and cost analysis;
- containerized execution and defensible security boundaries;
- enough abstraction to change models, tools, user interfaces, and eventually the harness itself.

A useful agent harness must therefore separate six layers:

```text
Interface: CLI, web, IDE, API, automation
                    |
Agent loop and lifecycle
                    |
Context, memory, and compaction
                    |
Models and provider adapters
                    |
Tools, MCP, and integrations
                    |
Execution, approvals, and sandboxing
```

---

## 2. Recommended architecture

```text
Chainlit or React
        |
        | SSE / WebSocket
        v
FastAPI
Authentication, sessions, authorization, API
        |
        v
Application-owned Agent Service
OpenHands SDK behind an AgentRuntime adapter
        |
        +-- Tool registry
        +-- Agent policies
        +-- Context assembly
        +-- Session management
        +-- Approval requests
        +-- Workspace management
        |
        v
LiteLLM Proxy
        |
        +-- Ollama / vLLM / SGLang
        +-- OpenRouter
        +-- Anthropic
        +-- OpenAI
        +-- Google and other providers
        |
        v
Local or hosted models
```

Cross-cutting systems:

```text
PostgreSQL
+-- users and projects
+-- conversations and messages
+-- agent runs and events
+-- tool calls and approvals
+-- artifacts
+-- model selections
+-- evaluation results
+-- optional pgvector-based memory

Langfuse
+-- agent-level traces
+-- LLM generations
+-- tool spans
+-- latency and token usage
+-- cost
+-- prompt versions
+-- evaluations

Sandbox workers
+-- disposable workspace
+-- restricted filesystem mounts
+-- network policy
+-- CPU and memory limits
+-- short-lived credentials
```

---

## 3. Why OpenHands SDK is the leading deployment choice

### 3.1 Natural fit for FastAPI and Python

OpenHands provides Python, TypeScript, and REST interfaces. Its SDK supports custom agent behavior, predefined and custom tools, and an agent server that can run locally or in containerized environments. This makes it a direct architectural fit for a Python/FastAPI product without requiring a Node.js subprocess bridge. citeturn3search39turn3search40

A simple conceptual flow is:

```text
FastAPI route
    -> application service
    -> OpenHands agent
    -> tool execution
    -> LiteLLM Proxy
```

### 3.2 Provider-neutral model access

OpenHands uses LiteLLM for its provider-agnostic LLM layer. This layer handles provider abstraction, retries, configuration, telemetry, cost tracking, and both Chat Completions and Responses-style interactions across a large provider catalog. citeturn4search65turn3search14

For governance, OpenHands should still be configured to reach a separately operated LiteLLM Proxy rather than contacting upstream providers directly. The proxy then becomes the only component holding provider credentials and enforcing model access policies.

### 3.3 Better production execution primitives

OpenHands includes workspace and agent-server concepts designed for local and containerized agent execution. Its SDK includes Bash, file editing, web, and MCP capabilities, while custom tools are expressed using explicit action, observation, executor, and tool-definition boundaries. citeturn3search40turn3search43

This is heavier than Pi's extension model, but the structure is beneficial for testability, remote execution, and a service expected to support multiple users.

### 3.4 Principal drawback

OpenHands is more opinionated and operationally heavier than Pi. It brings its own concepts for workspaces, conversations, action/observation handling, and agent-computer interaction. It is also primarily optimized for software-engineering agents rather than being a completely domain-neutral kernel. citeturn3search40

**Verdict:** OpenHands SDK is the strongest default when the prototype is expected to evolve into a containerized, API-exposed, multi-user application.

---

## 4. Where Pi wins

Pi is the strongest fit when the goal is to create a deeply customizable local equivalent to Claude Code and to control the agent loop itself.

Pi provides:

- a unified model API;
- an agent-session SDK;
- custom tools and extensions;
- lifecycle and tool-call interception;
- dynamic context injection;
- replaceable compaction;
- skills and prompt templates;
- model switching during a session;
- session-tree navigation;
- custom provider definitions;
- a terminal interface and headless RPC mode. citeturn3search4turn3search6turn3search50

Pi can connect to local models through Ollama, vLLM, LM Studio, and other OpenAI-compatible services. Its per-provider compatibility configuration can accommodate differences such as unsupported developer roles or reasoning-effort parameters. citeturn4search61

Its RPC mode uses streamed JSONL over standard input and output, supports prompts, steering, follow-up messages, and request correlation, and is explicitly intended for embedding in custom applications and user interfaces. citeturn4search63

### The important security limitation

Pi explicitly has no built-in sandbox. It executes tools and extensions with the permissions of the process that launched it. Project trust controls whether project-local resources are loaded, but it does not constrain commands executed after a project is trusted. citeturn3search49turn3search50

A deployed Pi solution would therefore need an external isolation boundary:

```text
FastAPI
    -> Pi RPC adapter
    -> disposable container or microVM
    -> restricted mounts and network
    -> LiteLLM Proxy
```

It would also require explicit engineering for subprocess lifecycle, crash recovery, cancellation, stream translation, session persistence, worker cleanup, and horizontal scaling.

**Verdict:** Pi is the best local experimentation and agent-kernel choice, but OpenHands is the easier production-service foundation.

---

## 5. Cline SDK as the TypeScript alternative

Cline SDK exposes the same open-source harness used by Cline's IDE and CLI products. Its packages separate the full runtime, stateless agent loop, model gateway, and shared types. It includes checkpoints, web fetch, MCP, scheduled execution, subagents, persistence, and streaming events. citeturn4search71turn4search72turn4search75

Custom Cline tools use typed Zod or JSON Schema inputs and execution handlers, which provides a clean and developer-friendly tool abstraction. citeturn4search73

A Cline-based architecture would be:

```text
React
    -> FastAPI
    -> Cline agent service in Node.js
    -> LiteLLM Proxy
    -> models
```

This is attractive if:

- TypeScript is preferred for the agent runtime;
- React is certain to be the long-term frontend;
- built-in checkpoints, scheduling, MCP, and subagents are valuable;
- operating both Python and Node.js services is acceptable.

**Verdict:** Cline SDK is the best middle ground between Pi's minimalism and OpenHands' platform orientation, particularly for a TypeScript-first product.

---

## 6. Why Aider, Codex, and Claude Code are not the primary foundation

### Aider

Aider is excellent for repository mapping, code editing, Git integration, architect/editor separation, linting, and test-driven repair. It supports many cloud and local models. citeturn3search26turn3search27turn3search30

However, its Python scripting interface is explicitly described as not officially supported and potentially subject to backward-incompatible changes. This makes it less suitable as the durable kernel of a new platform. citeturn3search44

Use Aider as a design reference or specialized editing component, not as the principal service abstraction.

### Codex CLI and SDK

Codex is open source under Apache 2.0 and provides official programmatic control, threads, CI integration, streamed events, sandboxing, approvals, and an application server. citeturn3search20turn3search21turn3search55

Its portability is nevertheless shaped around OpenAI's Responses protocol. Other models can be routed through compatible providers or gateways, but the harness naturally evolves around OpenAI semantics and product priorities. citeturn3search23turn3search25

Use Codex as a high-quality reference or when the OpenAI Responses API is acceptable as the canonical internal protocol.

### Claude Code

Claude Code is a valuable behavioral and user-experience benchmark, but it remains centered on Claude models even when accessed through Anthropic, AWS, Google Cloud, or Microsoft-hosted routes. Some features also depend on a Claude account. citeturn3search9turn3search10

Study its context management, permissions, planning, compaction, streaming, steering, delegation, and recovery behavior. Do not use it as the vendor-neutral foundation.

---

## 7. Framework-neutral AgentRuntime abstraction

The application should not expose OpenHands, Pi, or Cline types throughout the codebase. Instead, define a narrow internal contract:

```python
class AgentRuntime:
    async def create_session(self, config): ...
    async def run(self, session_id, message): ...
    async def steer(self, session_id, message): ...
    async def cancel(self, session_id): ...
    async def approve_tool_call(self, approval_id): ...
    async def close_session(self, session_id): ...
```

Then provide adapters:

```text
OpenHandsRuntime
PiRuntime
ClineRuntime
FakeRuntime for tests
```

The framework-neutral event model should include at least:

```text
session.created
user.message
assistant.delta
assistant.message
model.requested
model.completed
tool.requested
tool.approved
tool.denied
tool.started
tool.completed
tool.failed
artifact.created
run.completed
run.failed
```

PostgreSQL should store this canonical event history. A harness's native session file or database may be retained, but it should not be the application's only authoritative record.

---

## 8. Model abstraction without losing capabilities

Avoid reducing all models to a lowest-common-denominator interface of “messages in, text out.” That would provide superficial portability while losing the features that make strong agents effective.

Maintain a capability model such as:

```text
ModelCapabilities
+-- native tool calling
+-- parallel tool calls
+-- structured output
+-- reasoning controls
+-- prompt caching
+-- image input
+-- context management
+-- computer use
+-- streaming
+-- response continuation
```

The runtime should negotiate requested capabilities:

```text
Requested capability
       |
Supported natively?
   /          \
 yes          no
  |            |
native path   emulation or graceful degradation
```

Likewise, agent code should request logical model profiles rather than provider-specific model IDs:

```text
local-fast
local-coder
reasoning-large
reviewer
```

LiteLLM then maps those stable aliases to the currently approved local or hosted models. LiteLLM Proxy exposes compatible endpoints and can route requests to different upstream providers and self-hosted endpoints. citeturn4search59turn4search64

---

## 9. Component responsibilities

### FastAPI

FastAPI should own:

- authentication and authorization;
- conversation and project APIs;
- SSE or WebSocket streams;
- tool-approval endpoints;
- uploads and artifact downloads;
- quotas;
- session ownership;
- worker orchestration;
- audit APIs.

### PostgreSQL

PostgreSQL should hold authoritative application state:

- users and roles;
- projects and workspaces;
- conversations and messages;
- runs and normalized events;
- tool calls and approval decisions;
- model selections;
- artifacts and references;
- evaluation results;
- optional vector memory.

### LiteLLM Proxy

LiteLLM should own:

- provider routing;
- virtual model aliases;
- provider credentials;
- budgets and rate limits;
- per-user or per-team keys;
- model access policy;
- fallback policy;
- token and cost accounting.

Provider credentials should not be placed inside general-purpose agent workers. Workers should receive a limited LiteLLM virtual key.

### Langfuse

Langfuse should capture:

- end-to-end agent traces;
- individual model calls;
- tool spans;
- latency;
- cost and token usage;
- prompt versions;
- evaluation data.

Langfuse integrates with LiteLLM Proxy and can receive model-call telemetry with usage, cost, latency, session IDs, user IDs, and tags. citeturn4search66turn4search67

The FastAPI application should create the parent agent trace, while LiteLLM records the child model-call spans. Otherwise, model calls may be observable without the surrounding agent trajectory.

### Chainlit versus React

Use **Chainlit** first when fast experimentation and conversational UX are the priority.

Use **React** when the product requires:

- tailored approval experiences;
- workspace and file-tree views;
- terminal output;
- artifact inspection;
- branchable conversations;
- custom streaming state;
- a polished multi-user product.

Recommended sequence:

```text
Phase 1 -> Chainlit
Phase 2 -> React
```

---

## 10. Security architecture

A superpowered coding agent should not run directly in the FastAPI process with unrestricted host access.

Use a worker boundary:

```text
FastAPI control plane
        |
        v
Job queue or worker manager
        |
        v
Disposable agent worker
+-- per-task filesystem
+-- restricted mounts
+-- non-root user
+-- CPU, memory, and time limits
+-- outbound network allow-list
+-- no direct provider keys
+-- short-lived LiteLLM credential
+-- approval requirement for sensitive calls
```

Tool policy should be enforced below or outside the language model. The model may propose an operation, but deterministic policy code should authorize, deny, or require human approval.

Typical policy levels:

```text
Read-only tools                  -> automatic
Workspace-contained writes      -> automatic or reviewed
Shell commands                   -> policy-dependent
Package installation            -> reviewed
External network calls          -> allow-listed
Secrets and host filesystem     -> denied
Destructive operations          -> denied or explicit approval
```

---

## 11. Local-model reality

A harness cannot make a weak model behave like Claude Code. Strong agent performance depends on:

- reliable tool calling;
- instruction adherence;
- long-context use;
- code reasoning;
- file-edit accuracy;
- recovery after failed tools;
- disciplined completion behavior.

OpenHands supports local servers including Ollama, LM Studio, vLLM, and SGLang, but its documentation notes that open-weight and local models still vary in tool-use reliability. citeturn3search15

The deployment should therefore support model profiles and selective escalation. Routine search and edits may remain local, while difficult planning or review can be routed to a stronger approved model when necessary.

---

## 12. Recommended implementation plan

### Phase 1: Local proof of concept

Build:

```text
Chainlit
FastAPI
OpenHands SDK
LiteLLM Proxy
Ollama or vLLM
PostgreSQL
Langfuse
one disposable Docker worker
```

Initial tools:

- read and search files;
- write and patch files;
- execute tests;
- restricted shell;
- Git diff and status;
- retrieve approved web content;
- query PostgreSQL using read-only statements;
- create and retrieve artifacts.

### Phase 2: Harness comparison

Implement the same limited task suite with:

1. OpenHands SDK;
2. Pi through RPC;
3. Cline SDK if TypeScript remains strategically attractive.

Evaluate:

- quality of task completion;
- tokens and latency;
- failed tool calls;
- model-switch degradation;
- session recovery;
- custom-tool effort;
- trace completeness;
- security-policy enforcement;
- amount of framework-specific adapter code.

The most meaningful portability metric is:

> How much framework-specific application code survives when both the model and user interface change?

### Phase 3: Productization

- replace Chainlit with React if needed;
- introduce queued workers;
- add per-user budgets and virtual keys;
- formalize tool approvals;
- add evaluation datasets;
- implement workspace snapshots and restoration;
- introduce network and filesystem policy;
- add horizontal worker scaling;
- retain a second harness adapter as an escape route.

---

## 13. Final decision

For the full containerized FastAPI/PostgreSQL/LiteLLM/Langfuse application:

> **Choose OpenHands SDK as the initial pre-made harness.**

For a local, deeply modifiable Claude Code-style terminal agent:

> **Use Pi, pointed at the same LiteLLM Proxy.**

For a TypeScript-first product:

> **Evaluate Cline SDK as the strongest alternative.**

The resulting landscape is:

```text
Pi desktop/terminal
        |
        +-------------------+
                            v
React/Chainlit -> FastAPI -> LiteLLM Proxy -> models
                      ^
                      |
              OpenHands agent workers
```

This gives a coherent system:

- Pi as the personal power-user interface;
- OpenHands as the deployed agent engine;
- LiteLLM as the shared model-control plane;
- Langfuse as the shared observability layer;
- PostgreSQL as the authoritative application store;
- FastAPI as the stable product API;
- an application-owned `AgentRuntime` interface as protection against harness lock-in.

---

## Sources consulted

- Pi homepage, SDK, provider, model, RPC, extension, and security documentation. citeturn2view1turn3search2turn3search4turn3search6turn3search49turn3search50turn4search61turn4search63
- OpenHands SDK, LLM architecture, custom-tool, model, and deployment documentation. citeturn3search14turn3search15turn3search39turn3search40turn3search43turn4search65
- Cline SDK, provider, tool, and architecture documentation. citeturn3search32turn3search33turn4search71turn4search72turn4search73turn4search75
- Aider model, chat-mode, repository, and scripting documentation. citeturn3search26turn3search27turn3search30turn3search44
- Codex repository, licensing, SDK, and custom-provider material. citeturn3search20turn3search21turn3search23turn3search25turn3search55
- Claude Code deployment and model-configuration documentation. citeturn3search9turn3search10
- LiteLLM supported endpoint and OpenAI-compatible endpoint documentation. citeturn4search59turn4search64
- Langfuse integrations for LiteLLM Proxy and SDK. citeturn4search66turn4search67
