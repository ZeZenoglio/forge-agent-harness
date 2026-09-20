import ipaddress
import socket
from urllib.parse import urlparse

import httpx


def is_safe_ip(ip_str: str) -> bool:
    """Check if an IP address is a public, safe IP (not private or loopback)."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False

def fetch_url(url: str) -> str:
    """Fetch URL contents with SSRF protection."""
    parsed = urlparse(url)
    if not parsed.hostname:
        return "Error: Invalid URL"
        
    try:
        # Resolve IP to check for SSRF
        ip = socket.gethostbyname(parsed.hostname)
        if not is_safe_ip(ip):
            return "Error: Access to private or loopback IP ranges is blocked (SSRF Protection)"
    except socket.gaierror:
        return "Error: Could not resolve hostname"
        
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:  # noqa: BLE001
        return f"Error fetching URL: {e!s}"
