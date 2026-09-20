from backend.tools.web import fetch_url, is_safe_ip


def test_is_safe_ip():
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("127.0.0.1") is False
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("10.0.0.1") is False
    assert is_safe_ip("169.254.169.254") is False

def test_fetch_url_ssrf_protection():
    # Should block localhost
    assert "SSRF Protection" in fetch_url("http://127.0.0.1/test")
    assert "SSRF Protection" in fetch_url("http://localhost/test")
    # Should block cloud metadata API
    assert "SSRF Protection" in fetch_url("http://169.254.169.254/latest/meta-data")
