# AGENTS.md

Operating guide for AI agents working in the JO Harness repository.

> **This file is a prompt.** It is loaded into context on every agent turn. Keep it dense
> and project-specific. Do not add generic advice the model already knows (PEP 8, naming
> conventions, "write good code"). If a rule cannot change an agent's behaviour on this
> repository specifically, delete it.

---

## 1. What this project is

JO Harness is a **modular, model-agnostic agent platform**. A single agent core is exposed
through four entry points — REST, MCP, A2A, and a web UI — and runs against self-hosted
infrastructure with no mandatory cloud dependency.

The central architectural bet: the application never depends on any specific agent SDK.
Everything goes through the `AgentRuntime` protocol, so the underlying harness (currently
OpenHands) can be replaced without touching product code.

**Read before your first substantive change:**

| File | What it gives you |
|---|---|
| `docs/sdd_requirements.csv` | The 49+ requirements. IDs, acceptance criteria, phases, dependencies. **This is the source of truth for what "done" means.** |
| `docs/implementation_plan.md` | Phase sequencing and the target file layout |
| `docs/architecture.html` | Component overview and resolved design decisions |
| `docs/jo_harness_audit_report.md` | Known defects in the above, with severity ratings. Several requirements are wrong; this file says which. |

When the plan and the audit disagree, **the audit wins** and the plan needs updating. Say so
rather than silently picking one.

---

## 2. Current state — read this before trusting any other section

<!-- UPDATE THIS BLOCK AS PHASES COMPLETE. An out-of-date state block is worse than none. -->

**As of the last update to this file: no implementation exists. All requirements are `Not Started`.**

Current phase: **Phase 0 / Phase 1 — evaluation foundation**

This matters because several controls described in the architecture do **not exist yet**:

| Control | Status |
|---|---|
| Policy engine (budgets, argument validation, thrash breaking) | **Not built** — REQ-051 to REQ-057, proposed |
| Sandboxed execution / read-only rootfs | **Not built** — REQ-027, Phase 3 |
| Workspace path containment | **Not built** — Phase 2 |
| Approval gate for irreversible actions | **Not built** — REQ-050, proposed |

**Do not assume a safety net is catching your mistakes.** There is currently no sandbox, no
budget enforcement, and no path containment. You are operating directly against the
developer's machine. Behave accordingly, and see §6.

If you find this block contradicts what you observe in the repository, the block is stale —
say so and ask for it to be updated.

---

## 3. Spec-driven development workflow

This repository is developed spec-first. Requirements exist before code, and every change
traces back to one.

**The loop, for each requirement:**

1. **Read the requirement** in `docs/sdd_requirements.csv`. Read its acceptance criteria and
   its dependencies. Check that every dependency is `Complete` — if not, stop and say which
   one blocks you.
2. **Restate the acceptance criteria as tests** before implementing. Each AC becomes at least
   one test. If an AC is not testable as written, say so and propose a measurable rewrite
   rather than implementing against a vague criterion.
3. **Implement** the smallest change that satisfies the criteria.
4. **Verify** with the commands in §4. Do not report completion without running them.
5. **Update the CSV**: set `Status` to `Complete` and fill `Verified By` with the test path or
   eval metric that proves it. Never mark a requirement complete on the strength of a passing
   implementation you did not test.

**Rules:**

- **One requirement per branch and per PR.** Branch naming: `req-016-tool-registry`.
- **Reference the REQ ID in every commit**: `feat(agent): add tool registry [REQ-016]`.
  Conventional commit prefixes: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.
- **Do not edit requirement text, acceptance criteria, priority, or phase.** If a requirement
  is wrong, say what is wrong and propose the change — do not make it. `Status` and
  `Verified By` are the only columns you write.
- **If asked to build something with no requirement, stop and say so.** Propose the
  requirement first. Unspecified work is how scope and safety controls get lost.

---

## 4. Verification loop

<!-- CONFIRM THESE COMMANDS MATCH YOUR ACTUAL TOOLING BEFORE RELYING ON THEM. -->

Run these before claiming any task is complete. Report actual output, not a summary of what
you expect the output to be.

```bash
uv sync                          # install / update dependencies
uv run pytest                    # full test suite
uv run pytest tests/unit -q      # fast feedback during iteration
uv run ruff check .              # lint
uv run ruff format --check .     # formatting
uv run mypy backend/             # type checking
```

**Definition of done for a code change:** tests pass, lint passes, types pass, the new tests
actually fail when the implementation is reverted. That last check is not optional — a test
that passes against an empty implementation is worse than no test.

**Stack conventions:**
- Python, managed with `uv`. Dependencies go in `pyproject.toml`, never installed ad hoc.
- Line length 88. `ruff` is the single authority on formatting and linting — do not argue
  with it or add per-file ignores without saying why.
- Type hints on all public functions. `mypy` must pass.
- Docstrings on modules, public functions, and anything non-obvious. **Not** on trivial
  accessors — `"""Get the user."""` above `get_user()` is noise.
- Comments explain **why**, not what. If a comment restates the code, delete one of them.

**Test conventions:**
- `tests/unit/` — no network, no containers, no LLM calls. Must run in seconds.
- `tests/integration/` — may use the docker-compose stack.
- Agent-facing code is tested against `FakeRuntime`, never a live model (REQ-017). A unit
  test that calls an LLM is misfiled.

---

## 5. Architecture invariants

These are the rules that make the design work. Violating one is a defect even if the tests pass.

**1. Never import `openhands.*` outside the runtime adapter.**
The only module permitted to import OpenHands is `backend/agent/openhands_runtime.py`.
Everything else depends on the `AgentRuntime` protocol. This is what makes the SDK
replaceable and survivable — the SDK ships roughly a minor version a week with real
breaking changes. If you need something OpenHands offers, extend the protocol; do not
reach through it. *(REQ-017; enforce mechanically with `import-linter` in CI.)*

**2. Pin the OpenHands package set together.**
`openhands-sdk`, `openhands-tools`, `openhands-workspace` and `openhands-agent-server` must
all be pinned to the **same exact version**. Mismatched versions fail at import. Never
upgrade one alone, and never leave any of them unpinned.

**3. Policy enforcement lives below the `AgentRuntime` seam, never in FastAPI middleware.**
MCP and A2A are separate protocol servers, not FastAPI routes. Anything enforced in HTTP
middleware is bypassed by them — and those are exactly the callers with no human watching.
Guardrails go in the policy engine invoked by the runtime, so every entry point inherits
them structurally.

**4. Prompt assembly order is fixed, and volatile content goes last.**
`system prompt → tool definitions (deterministic sorted order) → history → dynamic state →
current turn`. Anything that changes between turns must sit at the end. Content injected
near the head of the prompt invalidates the KV cache on every iteration, which on local
inference is paid directly in user-visible latency. Do not inject mutable state, timestamps,
or randomized examples early in the prompt.

**5. Every agent event carries a monotonic `seq`.**
Timestamps are not an ordering key. Event replay and stream reconnection depend on `seq`.

**6. Tool observations are capped and scrubbed before entering context.**
Never place an unbounded tool result into the model's context. Truncate with an explicit
marker so the model knows content was removed. Large results go to the artifact store with a
handle in context, not the full body.

**7. Errors follow RFC 7807 problem details; successful responses use a consistent envelope.**

---

## 6. Boundaries

### Always ask before

- Modifying `docker/` compose files, service definitions, or ports
- Adding, removing, or changing the version of any dependency
- Changing anything in `docs/sdd_requirements.csv` other than `Status` and `Verified By`
- Changing database schema or writing a migration
- Deleting files, or moving more than a couple at once
- Any change to authentication, the policy engine, or tool permissions
- Running anything that touches the network beyond package installation

### Never

- **`git push`.** Commit locally; the human reviews and pushes. No exceptions.
- **Commit to `main`.** Work on a `req-NNN-*` branch.
- **`git commit -a`.** Stage deliberately with `git add <path>`. Auto-staging sweeps up
  unrelated edits and misses new files.
- **Read or write `.env`, `.env.*`, or any credentials file.** Not to inspect it, not to
  debug it, not to check whether a variable is set. If you need a config value, ask.
- **Write credentials, tokens, or keys into source, docs, comments, test fixtures, or commit
  messages.** Including examples and placeholders that look real.
- **Disable, weaken, or add exceptions to a security control or guardrail to make a test
  pass.** Report the conflict instead. A guardrail that gets loosened under schedule
  pressure is how this project's threat model fails.
- **Mark a requirement `Complete` without a test or eval that verifies it.**
- **Fabricate command output, test results, or benchmark numbers.** If you did not run it,
  say you did not run it.

### On uncertainty

Ask rather than guess, and prefer a narrow question to a broad one. Two specific cases:

- **The frontend choice is unresolved.** `frontend/` may become Open WebUI integration or a
  React app. Do not pick one. Ask.
- **If a task seems to require violating something above,** that is a signal the task or the
  rule is wrong. Surface it; do not route around it.

---

## 7. Project structure

```
backend/
  api/            FastAPI routes, dependencies, response envelopes
  agent/          AgentRuntime protocol, OpenHands adapter, policy engine, tools
  services/       Application services (no SDK imports)
  models/         SQLAlchemy models and Pydantic schemas
  mcp/            MCP server (separate protocol server — see invariant 3)
  a2a/            A2A server (separate protocol server — see invariant 3)
evaluation/       Metrics, judges, trajectory evaluators
scripts/          Eval runners, dataset loaders, utilities
docker/           Compose files and service configuration
docs/             Specifications, architecture, audit
frontend/         UNRESOLVED — do not create without asking
tests/
  unit/           Fast, isolated, FakeRuntime only
  integration/    May use the compose stack
```

Follow the conventions already present in a directory over the conventions in this file. If
they conflict badly enough to matter, say so.

---

## 8. Maintaining this file

- Keep it under roughly 200 lines. It costs tokens on every turn.
- Update §2 whenever a phase completes or a control ships. A stale state block actively
  misleads.
- Directory-specific conventions belong in a nested `AGENTS.md` (e.g. `evaluation/AGENTS.md`
  for metric conventions), not here.
- Every rule should be one an agent could plausibly violate. Delete anything that reads as
  general good practice.
