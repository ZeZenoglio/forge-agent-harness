from backend.services.artifact_service import get_artifact_service
from backend.tools.docgen import compile_latex, generate_docx, generate_pdf


def test_generate_pdf() -> None:
    res = generate_pdf(
        "## Executive Summary\n\nAll systems nominal.", title="Quarterly Report"
    )
    assert res["success"] is True
    assert res["filename"] == "quarterly_report.pdf"
    assert res["mime_type"] == "application/pdf"

    artifact = get_artifact_service().get_artifact(res["artifact_id"])
    assert artifact is not None
    assert "%PDF-1.4" in artifact.content


def test_generate_docx() -> None:
    res = generate_docx("Content for Word doc", title="Meeting Notes")
    assert res["success"] is True
    assert res["filename"] == "meeting_notes.docx"
    assert "wordprocessingml" in res["mime_type"]

    artifact = get_artifact_service().get_artifact(res["artifact_id"])
    assert artifact is not None
    assert "<w:document" in artifact.content


def test_compile_latex() -> None:
    tex = r"\documentclass{article}\begin{document}Hello LaTeX\end{document}"
    res = compile_latex(tex, title="Paper Draft")
    assert res["success"] is True
    assert res["filename"] == "paper_draft.pdf"

    artifact = get_artifact_service().get_artifact(res["artifact_id"])
    assert artifact is not None
    assert artifact.size_bytes > 0
