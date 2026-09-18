# 🔥 Forge — Open Agent Harness

> A modular, model-agnostic agent evaluation & orchestration platform.  
> Build it local. Scale it global. Measure everything.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)](https://python.org)
[![UV](https://img.shields.io/badge/Managed%20with-UV-blueviolet)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What is Forge?

**Forge** is a batteries-included harness for building, evaluating, and iterating on autonomous AI agents. It is built around the principle that **evaluation comes first** — every agent change is immediately measurable through a rigorous, automated benchmark suite.

### Core Stack

| Layer | Technology |
|---|---|
| **Agent Harness** | OpenHands SDK |
| **API Layer** | FastAPI |
| **Model Gateway** | LiteLLM Proxy |
| **Observability & Eval** | Langfuse |
| **Application Data** | PostgreSQL |
| **Local Models** | Ollama (`qwen3.5:4b` default) |
| **Dependency Management** | Astral UV |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Forge Platform                       │
│                                                             │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │  Frontend │    │   FastAPI    │    │  LiteLLM Proxy   │ │
│  │  (React)  │───▶│   Backend   │───▶│  (Model Gateway) │ │
│  └───────────┘    └──────────────┘    └──────────────────┘ │
│                          │                      │           │
│                   ┌──────▼──────┐      ┌────────▼────────┐ │
│                   │  OpenHands  │      │   Ollama / API  │ │
│                   │  SDK Agent  │      │   (qwen3.5:4b)  │ │
│                   └──────┬──────┘      └─────────────────┘ │
│                          │                                  │
│             ┌────────────▼────────────┐                     │
│             │  Langfuse Observability │                     │
│             │  + Eval Suite (TriviaQA)│                     │
│             └────────────┬────────────┘                     │
│                          │                                  │
│                  ┌───────▼──────┐                           │
│                  │  PostgreSQL  │                           │
│                  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
forge/
├── backend/
│   ├── routes/          # FastAPI route handlers
│   └── services/        # Business logic & agent orchestration
├── frontend/            # React UI (coming soon)
├── notebooks/           # Evaluation & analysis notebooks
├── data/                # Benchmark datasets & results
├── docs/
│   ├── implementation_plan.md          # Full technical spec
│   ├── open_agent_harness_findings.md  # Research findings
│   ├── architecture.html               # Interactive architecture diagram
│   └── sdd_requirements.csv            # Software design requirements
├── pyproject.toml       # Project config (UV)
└── uv.lock              # Locked dependencies
```

---

## Build Phases

### Phase 1 — Evaluation First *(current)*
- TriviaQA benchmark suite (200-item subset)
- Langfuse integration for trace logging
- Semantic similarity scoring pipeline
- Baseline metrics for all subsequent improvements

### Phase 2 — Agent Core
- OpenHands SDK agent with tool calling
- LiteLLM proxy with Qwen3.5:4b via Ollama
- FastAPI REST endpoints
- PostgreSQL persistence

### Phase 3 — Observability & Scale
- Full Langfuse dashboard integration
- Kubernetes deployment manifests
- Cloud model provider configuration
- CI/CD evaluation pipeline

---

## Default Model: `qwen3.5:4b`

Selected as the default small language model based on 2026 benchmarks:

| Model | Tool Calling | Reasoning | License |
|---|---|---|---|
| **Qwen3.5 4B** ✅ | Aggressive, proactive | Best-in-class | Apache 2.0 |
| Gemma 4 E4B | Conservative | Good | Apache 2.0 |
| Nemotron-3-Nano 4B | Excellent | Good | NVIDIA OML |

Pull locally with: `ollama pull qwen3.5:4b`

---

## Getting Started

### Prerequisites
- Python 3.12+
- [UV](https://github.com/astral-sh/uv) (`pip install uv`)
- [Ollama](https://ollama.com) (for local models)

### Setup

```bash
# Clone the repo
git clone https://github.com/josezenoglio/forge.git
cd forge

# Install dependencies with UV
uv sync

# Pull the default model
ollama pull qwen3.5:4b

# Start the backend
uv run uvicorn backend.main:app --reload
```

---

## Documentation

- 📋 [Implementation Plan](docs/implementation_plan.md)
- 🔬 [Open Agent Harness Research Findings](docs/open_agent_harness_findings.md)
- 🏗️ [Architecture Diagram](docs/architecture.html)
- 📊 [Requirements Spec](docs/sdd_requirements.csv)

---

## License

MIT — see [LICENSE](LICENSE) for details.