from unittest.mock import MagicMock, patch

from backend.tools.extraction import extract_structured


def test_extract_structured_from_text_success() -> None:
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content='{"name": "Alice", "age": 30, "company": "Acme Inc"}'
            )
        )
    ]

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "company": {"type": "string"},
        },
        "required": ["name", "age"],
    }

    input_text = "Alice is a 30-year-old software engineer working at Acme Inc."

    with patch("litellm.completion", return_value=mock_resp):
        result = extract_structured(input_data=input_text, schema=schema)

    assert result["success"] is True
    assert result["data"]["name"] == "Alice"
    assert result["data"]["age"] == 30
    assert result["data"]["company"] == "Acme Inc"
    assert result["error"] is None


def test_extract_structured_from_file(tmp_path) -> None:
    doc_file = tmp_path / "invoice.txt"
    doc_file.write_text("Invoice #1024 total $450.00 for services rendered.")

    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content='{"invoice_id": 1024, "total": 450.00}'))
    ]

    schema = {
        "type": "object",
        "properties": {
            "invoice_id": {"type": "integer"},
            "total": {"type": "number"},
        },
    }

    with patch("litellm.completion", return_value=mock_resp):
        result = extract_structured(input_data=str(doc_file), schema=schema)

    assert result["success"] is True
    assert result["data"]["invoice_id"] == 1024
    assert result["data"]["total"] == 450.00


def test_extract_structured_failure_partial() -> None:
    schema = {"type": "object", "properties": {"title": {"type": "string"}}}

    with patch("litellm.completion", side_effect=Exception("API connection timeout")):
        result = extract_structured(input_data="Sample raw text", schema=schema)

    assert result["success"] is False
    assert "API connection timeout" in result["error"]
    assert "partial_data" in result
