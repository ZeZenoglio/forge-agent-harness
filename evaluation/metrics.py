"""Evaluation metrics for JO Harness.

Implements REQ-009 (semantic similarity), REQ-010 (length ratio),
and the shared helpers used by REQ-007/REQ-008 evaluation runners.
"""

from __future__ import annotations

from typing import Any


# ── REQ-009: Semantic similarity ─────────────────────────────────────────────
def semantic_similarity(prediction: str, ground_truth: str) -> float:
    """Return cosine similarity in [0, 1] between *prediction* and *ground_truth*.

    Uses a singleton ``SentenceTransformer`` model (all-MiniLM-L6-v2) so the
    model is loaded only once per process.  Falls back to 0.0 if the
    ``sentence-transformers`` package is not installed so the rest of the
    evaluation pipeline still runs without the heavy dependency.
    """
    try:
        from sentence_transformers import util
    except ImportError:
        return 0.0

    model = _get_st_model()
    embeddings = model.encode([prediction, ground_truth], convert_to_tensor=True)
    score: float = float(util.cos_sim(embeddings[0], embeddings[1]).item())
    return max(0.0, min(1.0, score))


_st_model: Any = None


def _get_st_model() -> Any:
    """Return a cached SentenceTransformer instance."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer

        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


# ── REQ-010: Length ratio ─────────────────────────────────────────────────────
def length_ratio(prediction: str, ground_truth: str) -> float:
    """Return min(len_pred, len_ref) / max(len_pred, len_ref) in [0, 1].

    A score of 1.0 means both strings are exactly the same length; lower
    values indicate disproportionate verbosity or brevity.
    """
    len_pred = len(prediction.split())
    len_ref = len(ground_truth.split())
    if len_pred == 0 and len_ref == 0:
        return 1.0
    if len_pred == 0 or len_ref == 0:
        return 0.0
    return min(len_pred, len_ref) / max(len_pred, len_ref)


# ── Existing metrics (preserved) ──────────────────────────────────────────────
def exact_match(prediction: str, ground_truth: str) -> bool:
    """Evaluate Exact Match (EM) for Track A regression."""
    return prediction.strip().lower() == ground_truth.strip().lower()


def compute_f1(prediction: str, ground_truth: str) -> float:
    """Evaluate token-level F1 score for Track A regression."""
    pred_tokens = prediction.strip().lower().split()
    truth_tokens = ground_truth.strip().lower().split()

    if len(pred_tokens) == 0 or len(truth_tokens) == 0:
        return float(pred_tokens == truth_tokens)

    common = set(pred_tokens) & set(truth_tokens)
    if not common:
        return 0.0

    prec = len(common) / len(pred_tokens)
    rec = len(common) / len(truth_tokens)
    return 2 * (prec * rec) / (prec + rec)


# ── Aggregate scorer ──────────────────────────────────────────────────────────
def score_prediction(prediction: str, ground_truth: str) -> dict[str, float]:
    """Compute all available metrics and return as a dict."""
    return {
        "exact_match": float(exact_match(prediction, ground_truth)),
        "f1": compute_f1(prediction, ground_truth),
        "semantic_similarity": semantic_similarity(prediction, ground_truth),
        "length_ratio": length_ratio(prediction, ground_truth),
    }


# ── Tool-result cap (REQ-057 support) ─────────────────────────────────────────
_TRUNCATION_MARKER = (
    "\n\n[... content truncated — see artifact store for full output ...]"
)
_MAX_OBSERVATION_CHARS = 8_000


def cap_observation(text: str, max_chars: int = _MAX_OBSERVATION_CHARS) -> str:
    """Truncate *text* to *max_chars* with an explicit marker (REQ-057).

    Never place unbounded tool output into the model context.  Content that
    exceeds the ceiling is cut here; the caller is responsible for storing
    the full content in the artifact store and providing a handle.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + _TRUNCATION_MARKER
