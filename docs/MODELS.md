# Model Catalog & SLM Selection Guide (REQ-042)

## 1. Primary Model Deployments & Aliases

The JO Harness uses LiteLLM Proxy to route requests through four virtual aliases. This abstracts model hardware and provider topology from the agent core application code.

| Virtual Alias | Primary Target | Quantization | Context Window | Primary Role |
|---|---|---|---|---|
| `default-agent` | `qwen3.5:4b` | Q4_K_M | 32,768 tokens | Primary agentic loop step execution, tool generation |
| `reasoning-large` | `qwen2.5:14b` | Q4_K_M | 32,768 tokens | Complex multi-step reasoning, plan synthesis |
| `utility-small` | `qwen2.5:1.5b` | Q4_K_M | 16,384 tokens | Fast routing, PII classification, entity extraction |
| `reviewer` | `qwen2.5:14b` | Q4_K_M | 32,768 tokens | LLM-as-a-Judge evaluators (temp = 0.0) |
| `summarizer` | `qwen2.5:1.5b` | Q4_K_M | 16,384 tokens | Context window compression & rolling summaries |

---

## 2. Model Characteristics & Tested Behaviors

### `qwen3.5:4b` (Default Agent)
- **Strengths**: Extremely low time-to-first-token (<150ms on Apple Silicon / CUDA), strong JSON schema adherence, reliable tool-calling formatting.
- **Quirks**: Can produce terse reasoning if not prompted with structured step templates.
- **Recommended Temperature**: 0.2.

### `qwen2.5:14b` (Reasoning & Reviewer)
- **Strengths**: Superior code synthesis, deep step-by-step logic, robust evaluation scoring.
- **Quirks**: Higher memory footprint (~9GB VRAM in 4-bit).
- **Recommended Temperature**: 0.0 for judges, 0.4 for creative tasks.

### `qwen2.5:1.5b` (Utility & Summarizer)
- **Strengths**: Micro-latency, negligible memory footprint (<1.5GB), ideal for continuous background compression.
- **Quirks**: Limited multi-hop reasoning; avoid assigning tool dispatch decisions directly.

---

## 3. Upstream Provider Fallbacks

LiteLLM proxy is configured to fail over automatically:
`default-agent` (Local Ollama) ➔ `reasoning-large` (Local Ollama) ➔ Cloud fallback (if configured).
