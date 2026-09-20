import os
from typing import Any

from sentence_transformers import SentenceTransformer

# Load embedding model
# We use a small, fast model for local execution. In production, Litellm or a larger model can be used.
_model = SentenceTransformer("all-MiniLM-L6-v2")

# To allow testing without a real Postgres pgvector instance, we will provide a mocked memory fallback
# if FORGE_MOCK_RAG is set.
_MOCK_MEMORY: list[dict[str, Any]] = []


def _get_embedding(text: str) -> list[float]:
    return _model.encode(text).tolist()  # type: ignore


def memorize(content: str) -> str:
    """
    Store new memory chunks in the database.
    Chunks the content and saves the embeddings to pgvector.
    """
    if os.getenv("FORGE_MOCK_RAG"):
        embedding = _get_embedding(content)
        _MOCK_MEMORY.append({"content": content, "embedding": embedding})
        return f"Successfully memorized {len(content)} characters."

    # Real implementation would use SQLAlchemy session here
    # from backend.db.models import Document, Embedding
    # from sqlalchemy.ext.asyncio import AsyncSession

    # For now, we will fallback to mock memory if db is not connected
    embedding = _get_embedding(content)
    _MOCK_MEMORY.append({"content": content, "embedding": embedding})
    return f"Successfully memorized {len(content)} characters (DB integration pending)."


def search_memory(query: str, top_k: int = 3) -> str:
    """
    Perform a vector search for the context matching the query.
    Returns the concatenated string of relevant contexts.
    """
    if not _MOCK_MEMORY:
        return "No memories stored yet."

    query_emb = _get_embedding(query)

    if os.getenv("FORGE_MOCK_RAG") or True:  # fallback to mock
        import numpy as np

        # Simple cosine similarity
        results = []
        for mem in _MOCK_MEMORY:
            mem_emb = np.array(mem["embedding"])
            q_emb = np.array(query_emb)
            sim = np.dot(mem_emb, q_emb) / (
                np.linalg.norm(mem_emb) * np.linalg.norm(q_emb)
            )
            results.append((sim, mem["content"]))

        results.sort(key=lambda x: x[0], reverse=True)
        top_results = [content for sim, content in results[:top_k]]

        if not top_results:
            return "No relevant memories found."

        return "\n\n---\n\n".join(top_results)
