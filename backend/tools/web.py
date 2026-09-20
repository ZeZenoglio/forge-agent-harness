import html
import ipaddress
import os
import re
import socket
from urllib.parse import quote_plus, urlparse

import httpx


def is_safe_ip(ip_str: str) -> bool:
    """Check if an IP address is a public, safe IP (not private or loopback)."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False


def _is_url_allowed(
    url: str,
    allow_list: list[str] | None = None,
    deny_list: list[str] | None = None,
) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    if deny_list:
        for denied in deny_list:
            if hostname == denied.lower() or hostname.endswith(f".{denied.lower()}"):
                return False

    if allow_list:
        return any(
            hostname == allowed.lower() or hostname.endswith(f".{allowed.lower()}")
            for allowed in allow_list
        )

    return True


def _strip_html(raw_html: str) -> str:
    """Strip HTML tags and unescape entities to return clean text."""
    # Remove script and style elements
    cleaned = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE
    )
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Unescape HTML entities
    cleaned = html.unescape(cleaned)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def fetch_url(
    url: str,
    max_chars: int = 10000,
    allow_list: list[str] | None = None,
    deny_list: list[str] | None = None,
) -> str:
    """Fetch URL contents with SSRF protection, allow/deny filtering, and HTML cleanup."""
    parsed = urlparse(url)
    if not parsed.hostname:
        return "Error: Invalid URL"

    if not _is_url_allowed(url, allow_list=allow_list, deny_list=deny_list):
        return "Error: URL is not permitted by domain policy"

    try:
        # Resolve IP to check for SSRF
        ip = socket.gethostbyname(parsed.hostname)
        if not is_safe_ip(ip):
            return "Error: Access to private or loopback IP ranges is blocked (SSRF Protection)"
    except socket.gaierror:
        return "Error: Could not resolve hostname"

    try:
        headers = {
            "User-Agent": "JOHarness/1.0 (https://github.com/ZeZenoglio/forge-agent-harness; agent@joharness.org)"
        }
        with httpx.Client(
            follow_redirects=True, timeout=10.0, headers=headers
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            text_content = _strip_html(response.text)
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars] + "... [truncated]"
            return text_content
    except Exception as e:  # noqa: BLE001
        return f"Error fetching URL: {e!s}"


def web_search(
    query: str,
    num_results: int = 5,
    searxng_url: str | None = None,
    allow_list: list[str] | None = None,
    deny_list: list[str] | None = None,
) -> list[dict[str, str]] | dict[str, str]:
    """Search the web via self-hosted SearXNG JSON API aggregating Google, Bing, DuckDuckGo."""
    endpoint = searxng_url or os.getenv("SEARXNG_URL")
    if not endpoint:
        try:
            socket.gethostbyname("searxng")
            endpoint = "http://searxng:8080"
        except socket.gaierror:
            endpoint = "http://localhost:8080"
    elif "searxng:8080" in endpoint:
        try:
            socket.gethostbyname("searxng")
        except socket.gaierror:
            endpoint = endpoint.replace("searxng:8080", "localhost:8080")

    encoded_query = quote_plus(query)
    target_url = f"{endpoint}/search?q={encoded_query}&format=json&engines=google,bing,duckduckgo"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(target_url)
            resp.raise_for_status()
            data = resp.json()

        raw_results = data.get("results", [])
        filtered_results: list[dict[str, str]] = []

        for item in raw_results:
            item_url = item.get("url", "")
            if not _is_url_allowed(
                item_url, allow_list=allow_list, deny_list=deny_list
            ):
                continue

            filtered_results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "url": item_url,
                }
            )

            if len(filtered_results) >= num_results:
                break

        return filtered_results
    except Exception as e:  # noqa: BLE001
        return {"error": f"Search failed: {e!s}"}
