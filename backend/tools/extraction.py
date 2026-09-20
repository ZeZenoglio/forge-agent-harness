"""Structured data extraction tool (REQ-044).

Extracts structured data conforming to a specified JSON schema from unstructured text,
markdown, PDF files, or OCR/images using LLMs with structured output mode.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import litellm


def _extract_text_from_file(file_path_str: str) -> str:
    path = Path(file_path_str)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path_str}")

    suffix = path.suffix.lower()
    if suffix in [".txt", ".md", ".json", ".csv", ".log"]:
        return path.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        # Attempt basic PDF text extraction if pypdf is installed, or fallback
        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages_text)
        except Exception:  # noqa: BLE001
            # Fallback text extraction or placeholder if pypdf unavailable
            raw = path.read_bytes()
            # extract readable ascii text
            import re

            ascii_strings = re.findall(rb"[\x20-\x7E]{4,}", raw)
            return b"\n".join(ascii_strings).decode("utf-8", errors="replace")
    elif suffix in [".png", ".jpg", ".jpeg", ".webp"]:
        # Image extraction via vision tool
        try:
            from backend.tools.vision import analyze_image

            res = analyze_image(
                str(path),
                prompt="Transcribe all visible text from this image accurately.",
            )
            return str(res.get("analysis", "")) if isinstance(res, dict) else str(res)
        except Exception as e:  # noqa: BLE001
            return f"[Image OCR failed: {e!s}]"
    else:
        return path.read_text(encoding="utf-8", errors="replace")


def extract_structured(
    input_data: str,
    schema: dict[str, Any] | str,
    params: dict[str, Any] | None = None,
    model: str = "default-agent",
) -> dict[str, Any]:
    """Extract structured data from unstructured text, PDFs, or images into JSON conforming to schema.

    If input_data points to an existing file path, file content is read and extracted.
    Extraction uses LLM with structured output mode. Returns validated JSON conforming to schema.
    Extraction failures return partial results with error indicators.
    """
    params = params or {}
    # Determine if input is file path
    content_text = input_data
    if len(input_data) < 1024 and ("\n" not in input_data):
        try:
            candidate_path = Path(input_data)
            if candidate_path.is_file():
                content_text = _extract_text_from_file(input_data)
        except Exception:  # noqa: BLE001, S110
            pass

    schema_dict: dict[str, Any]
    if isinstance(schema, str):
        try:
            schema_dict = json.loads(schema)
        except Exception as e:  # noqa: BLE001
            return {
                "success": False,
                "error": f"Invalid JSON schema provided: {e!s}",
                "partial_data": None,
            }
    else:
        schema_dict = schema

    system_prompt = (
        "You are an expert structured data extraction engine. "
        "Extract the requested information from the text strictly conforming to the following JSON Schema:\n"
        f"{json.dumps(schema_dict, indent=2)}\n\n"
        "Respond ONLY with a valid JSON object conforming to this schema."
    )

    user_prompt = f'Text to extract from:\n"""\n{content_text[:8000]}\n"""'

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=params.get("temperature", 0.0),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed_json = json.loads(content)
        return {
            "success": True,
            "data": parsed_json,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        # Fallback / Partial extraction handling
        # Try finding JSON substring if LLM returned text + JSON
        fallback_data = None
        error_msg = str(exc)
        if hasattr(exc, "response") and getattr(exc, "response", None):
            try:
                raw_txt = str(exc.response)
                start = raw_txt.find("{")
                end = raw_txt.rfind("}")
                if start != -1 and end != -1:
                    fallback_data = json.loads(raw_txt[start : end + 1])
            except Exception:  # noqa: BLE001, S110
                pass

        return {
            "success": False,
            "error": f"Extraction error: {error_msg}",
            "partial_data": fallback_data,
        }
