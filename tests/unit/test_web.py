from unittest.mock import MagicMock, patch

from backend.tools.web import _strip_html, fetch_url, is_safe_ip, web_search


def test_is_safe_ip() -> None:
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("127.0.0.1") is False
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("10.0.0.1") is False
    assert is_safe_ip("169.254.169.254") is False


def test_fetch_url_ssrf_protection() -> None:
    # Should block localhost
    assert "SSRF Protection" in fetch_url("http://127.0.0.1/test")
    assert "SSRF Protection" in fetch_url("http://localhost/test")
    # Should block cloud metadata API
    assert "SSRF Protection" in fetch_url("http://169.254.169.254/latest/meta-data")


def test_strip_html() -> None:
    raw = "<html><head><script>alert(1)</script></head><body><h1>Title</h1><p>Hello &amp; world!</p></body></html>"
    cleaned = _strip_html(raw)
    assert "Title Hello & world!" in cleaned
    assert "alert" not in cleaned
    assert "<h1>" not in cleaned


def test_fetch_url_allow_deny_list() -> None:
    # Denied domain
    res = fetch_url("https://malicious.example.com/page", deny_list=["example.com"])
    assert "not permitted" in res

    # Allowed domain
    res_allow = fetch_url("https://forbidden.com/page", allow_list=["example.org"])
    assert "not permitted" in res_allow


def test_web_search_mocked() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Agent Platform",
                "content": "A modular, model-agnostic agent platform.",
                "url": "https://example.com/agent",
            },
            {
                "title": "Blocked Page",
                "content": "Should be filtered out",
                "url": "https://blocked.com/page",
            },
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.get", return_value=mock_response):
        results = web_search(
            query="agent platform",
            num_results=5,
            searxng_url="http://searxng:8080",
            deny_list=["blocked.com"],
        )

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["title"] == "Agent Platform"
        assert results[0]["snippet"] == "A modular, model-agnostic agent platform."
        assert results[0]["url"] == "https://example.com/agent"
