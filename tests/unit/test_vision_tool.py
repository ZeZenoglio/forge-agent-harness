from unittest.mock import MagicMock, patch

from backend.tools.vision import _encode_image_to_data_url, analyze_image


def test_encode_image_to_data_url() -> None:
    data_url, meta = _encode_image_to_data_url(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    assert data_url.startswith("data:image/png;base64,")
    assert meta["source"] == "base64"


def test_analyze_image_mocked() -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "This is a red square."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("litellm.completion", return_value=mock_response):
        result = analyze_image(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        assert result["success"] is True
        assert result["description"] == "This is a red square."
        assert result["metadata"]["source"] == "base64"
