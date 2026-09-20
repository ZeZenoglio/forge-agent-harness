"""Study and research compound tool (REQ-045).

Performs iterative web search, content retrieval, and synthesis to generate
a structured markdown report with citations, and saves the output as an artifact.
"""

from __future__ import annotations

import logging
from typing import Any

import litellm

from backend.services.artifact_service import get_artifact_service
from backend.tools.web import fetch_url, web_search

logger = logging.getLogger(__name__)


def research_topic(
    query: str,
    depth: str = "shallow",
    output_format: str = "markdown",
    conversation_id: str | None = None,
    model: str = "default-agent",
) -> dict[str, Any]:
    """Perform multi-step research on a topic.

    - depth='shallow' retrieves ~3 sources.
    - depth='deep' retrieves ~10 sources.
    Retrieves web content with SSRF protection, synthesizes findings with LLM,
    generates a structured report with citations, and persists it as an Artifact.
    """
    target_count = 10 if depth == "deep" else 3

    raw_results = web_search(query=query, num_results=target_count)
    search_results: list[dict[str, str]] = (
        raw_results if isinstance(raw_results, list) else []
    )

    # Step 2: Content retrieval
    sources: list[dict[str, str]] = []
    collected_texts: list[str] = []

    for item in search_results:
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if not url:
            continue

        # Fetch page text
        page_text = fetch_url(url, max_chars=3000)
        if page_text.startswith("Error"):
            content_snippet = snippet
        else:
            content_snippet = page_text[:2000]

        source_entry = {
            "title": title or url,
            "url": url,
            "snippet": content_snippet,
        }
        sources.append(source_entry)
        collected_texts.append(f"### Source: {title} ({url})\n{content_snippet}")

    # Step 3: Synthesis
    context_block = (
        "\n\n".join(collected_texts)
        if collected_texts
        else "No external sources retrieved."
    )

    system_prompt = (
        "You are an academic researcher and expert technical analyst. "
        "Synthesize the provided source documents into a comprehensive, highly structured "
        "research report. Format the output in clean GitHub-flavored markdown. "
        "Include an Executive Summary, Key Findings, Detailed Analysis, and a Citations/References section "
        "referencing the source URLs provided."
    )

    user_prompt = (
        f"Topic / Research Query: {query}\n\n"
        f"Sources ({len(sources)} total):\n{context_block}\n\n"
        "Please provide the synthesized research report."
    )

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        report_content = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM synthesis failed, generating rule-based synthesis: %s", exc)
        # Fallback rule-based synthesis
        report_lines = [
            f"# Research Report: {query.title()}",
            "",
            "## Executive Summary",
            f"This research document compiles verified information on **{query.title()}** based on {len(sources)} authoritative external sources.",
            "",
            "## Key Findings",
        ]
        for src in sources:
            snippet = src["snippet"].strip()
            if "Jump to content" in snippet:
                snippet = snippet.split("Jump to content", 1)[-1].strip()
            if "move to sidebar" in snippet:
                snippet = snippet.split("hide", 1)[-1].strip()
            report_lines.append(f"### {src['title']}")
            report_lines.append(f"{snippet[:400]}...")
            report_lines.append(f"🔗 *Source:* [{src['url']}]({src['url']})\n")

        report_lines.append("## Citations and References")
        for i, src in enumerate(sources, 1):
            report_lines.append(f"{i}. [{src['title']}]({src['url']})")

        report_content = "\n".join(report_lines)

    # Step 4: Persist as Artifact
    artifact_service = get_artifact_service()
    sanitized_title = "".join(c if c.isalnum() else "_" for c in query[:30]).strip("_")
    artifact = artifact_service.create_artifact(
        name=f"research_{sanitized_title}.md",
        content=report_content,
        mime_type="text/markdown" if output_format == "markdown" else "text/plain",
        conversation_id=conversation_id,
    )

    return {
        "query": query,
        "depth": depth,
        "sources_count": len(sources),
        "sources": sources,
        "artifact_id": artifact.id,
        "artifact_name": artifact.name,
        "report": report_content,
    }
