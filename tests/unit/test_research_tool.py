from unittest.mock import MagicMock, patch

from backend.services.artifact_service import get_artifact_service
from backend.tools.research import research_topic


def test_research_topic_shallow_workflow() -> None:
    mock_search = [
        {"title": "Doc 1", "snippet": "Snippet 1", "url": "https://example.com/1"},
        {"title": "Doc 2", "snippet": "Snippet 2", "url": "https://example.com/2"},
        {"title": "Doc 3", "snippet": "Snippet 3", "url": "https://example.com/3"},
    ]

    mock_llm_resp = MagicMock()
    mock_llm_resp.choices = [
        MagicMock(
            message=MagicMock(
                content="# Research Report: Quantum Computing\n\n## Findings\nFast processing.\n\n## Citations\n- https://example.com/1"
            )
        )
    ]

    with (
        patch("backend.tools.research.web_search", return_value=mock_search) as mock_s,
        patch(
            "backend.tools.research.fetch_url",
            return_value="Detailed article content here",
        ),
        patch("litellm.completion", return_value=mock_llm_resp),
    ):
        result = research_topic(query="Quantum Computing", depth="shallow")

    mock_s.assert_called_once_with(query="Quantum Computing", num_results=3)
    assert result["sources_count"] == 3
    assert result["depth"] == "shallow"
    assert "artifact_id" in result
    assert "Quantum Computing" in result["report"]

    # Verify artifact exists
    artifact = get_artifact_service().get_artifact(result["artifact_id"])
    assert artifact is not None
    assert artifact.name.startswith("research_")
    assert artifact.content == result["report"]


def test_research_topic_deep_workflow() -> None:
    mock_search = [
        {
            "title": f"Doc {i}",
            "snippet": f"Snippet {i}",
            "url": f"https://example.com/{i}",
        }
        for i in range(10)
    ]

    with (
        patch("backend.tools.research.web_search", return_value=mock_search) as mock_s,
        patch("backend.tools.research.fetch_url", return_value="Detailed content"),
        patch("litellm.completion", side_effect=Exception("LLM unavailable")),
    ):
        result = research_topic(query="AI Agents", depth="deep")

    mock_s.assert_called_once_with(query="AI Agents", num_results=10)
    assert result["sources_count"] == 10
    assert result["depth"] == "deep"
    # Even if LLM failed, fallback generated the report with citations
    assert "Executive Summary" in result["report"]
    assert "Citations and References" in result["report"]
    assert "artifact_id" in result
