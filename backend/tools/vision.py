"""Image interpretation tool using multimodal models via LiteLLM (REQ-030).

Accepts image paths or base64 data, calls a multimodal vision model,
and includes image metadata in the Langfuse trace.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import litellm


def _encode_image_to_data_url(image_input: str) -> tuple[str, dict[str, Any]]:
    """Convert a file path or raw base64 string to a valid data URL and metadata."""
    if image_input.startswith("data:image/"):
        return image_input, {"type": "data_url", "length": len(image_input)}

    path = Path(image_input)
    if path.is_file():
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "image/jpeg"
        content_bytes = path.read_bytes()
        b64 = base64.b64encode(content_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"
        metadata = {
            "source": "file",
            "file_name": path.name,
            "mime_type": mime_type,
            "size_bytes": len(content_bytes),
        }
        return data_url, metadata

    # Assume raw base64 string
    mime_type = "image/png"
    data_url = f"data:{mime_type};base64,{image_input}"
    metadata = {
        "source": "base64",
        "mime_type": mime_type,
        "length": len(image_input),
    }
    return data_url, metadata


def analyze_image(
    image_input: str,
    prompt: str = "Describe what is in this image in detail.",
    model: str | None = None,
    api_base: str | None = None,
) -> dict[str, Any]:
    """Analyze and describe an image using a multimodal LLM via LiteLLM."""
    target_model = model or os.getenv("VISION_MODEL", "default-agent")
    litellm_base = api_base or os.getenv("LITELLM_BASE_URL", "http://localhost:4000")

    try:
        data_url, meta = _encode_image_to_data_url(image_input)
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Failed to load image: {e!s}",
            "description": "",
        }

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    try:
        response = litellm.completion(
            model=target_model,
            messages=messages,
            api_base=litellm_base,
            metadata={"image_meta": meta, "tool": "analyze_image"},
        )
        content = response.choices[0].message.content or ""
        return {
            "success": True,
            "description": content,
            "model_used": target_model,
            "metadata": meta,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "error": f"Vision model inference failed: {e!s}",
            "description": "",
            "metadata": meta,
        }
