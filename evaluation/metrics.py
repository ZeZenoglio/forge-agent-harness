def exact_match(prediction: str, ground_truth: str) -> bool:
    """Evaluate Exact Match (EM) for Track A regression."""
    return prediction.strip().lower() == ground_truth.strip().lower()


def compute_f1(prediction: str, ground_truth: str) -> float:
    """Evaluate F1 score for Track A regression."""
    pred_tokens = prediction.strip().lower().split()
    truth_tokens = ground_truth.strip().lower().split()

    if len(pred_tokens) == 0 or len(truth_tokens) == 0:
        return int(pred_tokens == truth_tokens)

    common = set(pred_tokens) & set(truth_tokens)
    if not common:
        return 0.0

    prec = len(common) / len(pred_tokens)
    rec = len(common) / len(truth_tokens)
    return 2 * (prec * rec) / (prec + rec)


def semantic_similarity(prediction: str, ground_truth: str) -> float:
    """Evaluate Semantic Similarity using sentence-transformers."""
    # Stub for Phase 1
    return 0.0
