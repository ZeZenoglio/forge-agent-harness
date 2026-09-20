# Threat Model & Security Architecture (REQ-055)

## 1. Overview & System Boundaries

JO Harness is a modular, model-agnostic agent platform that executes user prompts and autonomously runs tools (file manipulation, shell execution, web search) on self-hosted infrastructure.

### Entry Points
- **REST API (FastAPI)**: HTTP endpoints for chat, sessions, and artifacts.
- **MCP Server**: FastMCP-based protocol server for model context protocol clients.
- **A2A Server**: Agent-to-Agent protocol server.
- **Web UI**: Web interface communicating via SSE and REST.

### Execution Boundaries
- **Untrusted Input**: User queries and external web pages / tools observations.
- **Agent Core / Policy Seam**: The synchronous guardrail layer (`PolicyEngine`) evaluating tool calls before execution.
- **Execution Environment**: Isolated workspace directories (`/tmp/forge_workspace`), with sandboxed execution, strict path containment, and tool command deny-lists.

---

## 2. Threat Vectors & Mitigations

### 2.1 Prompt Injection & Jailbreaking
- **Threat**: Malicious input attempting to override system instructions or bypass policy checks.
- **Mitigation**: Canonical prompt assembly order (REQ-058) keeping system prompt immutable and prefixes deterministic; structured LLM-as-judge evaluation (REQ-011–013) for outputs; structural Trajectory Evaluator (REQ-063).

### 2.2 Arbitrary File System Access / Path Traversal
- **Threat**: Agent attempting to read or overwrite host system files (e.g., `/etc/passwd`, ssh keys, `.env`).
- **Mitigation**: Strict workspace containment (`_resolve_safe` in `backend/tools/file.py` and `PolicyEngine.validate_path`) resolving all paths to canonical representations and enforcing boundaries (REQ-023, REQ-024).

### 2.3 Dangerous Shell Command Execution
- **Threat**: Execution of destructive commands (`rm -rf /`, `mkfs`, fork bombs, curl piped to bash).
- **Mitigation**: Deny-list in `backend/tools/shell.py` (REQ-025), command execution scoped strictly inside workspace root, timeout enforcement, clean environment without sensitive host variables, and HITL approval gates (REQ-050) for irreversible operations.

### 2.4 Unbounded Resource Consumption & Context Flooding
- **Threat**: Infinite loops, thrashing on failing tool calls, or massive tool observations exhausting memory and budget.
- **Mitigation**: Token accounting and per-observation ceilings with truncation markers (REQ-057), iteration limits (max 15), thrash breaker intercepting repeated failed actions, and model cascades (REQ-059).

### 2.5 Credential & Secret Leakage
- **Threat**: Hardcoded secrets in code, repositories, or leaking environment variables into tool contexts or trace logs (REQ-056).
- **Mitigation**: No secrets committed; CI workflow running `detect-secrets` and `pip-audit`; PII & secret scrubbing in observations before logging or context injection.

---

## 3. Dependency Scanning & Continuous Verification
- **Automated CI**: GitHub Actions workflow running `pip-audit` to detect CVEs in third-party packages.
- **Secret Baseline**: Continuous secret scanning across all repository files via `detect-secrets`.
