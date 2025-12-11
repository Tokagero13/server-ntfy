"""URL validation utilities."""
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """
    Normalize domain to full URL with HTTPS by default.
    HTTP fallback is handled in endpoint checking.
    """
    url = url.strip()

    if url.startswith(('http://', 'https://')):
        return url

    return f'https://{url}'


def validate_url(url: str) -> bool:
    """Validate URL or domain with port support."""
    try:
        normalized = normalize_url(url)
        result = urlparse(normalized)

        if not all([result.scheme, result.netloc]):
            return False

        if result.scheme not in ["http", "https"]:
            return False

        netloc = result.netloc
        if ':' in netloc:
            hostname, port_str = netloc.rsplit(':', 1)
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    return False
            except ValueError:
                return False
        else:
            hostname = netloc

        # IPv4 validation
        if _is_valid_ipv4(hostname):
            return True
        elif hostname == 'localhost':
            return True
        elif '.' in hostname:
            parts = hostname.split('.')
            for part in parts:
                if not part or not all(c.isalnum() or c == '-' for c in part):
                    return False
                if part.startswith('-') or part.endswith('-'):
                    return False
            return True
        else:
            return False

    except Exception:
        return False


def _is_valid_ipv4(ip: str) -> bool:
    """Check if string is a valid IPv4 address."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        for part in parts:
            num = int(part)
            if not (0 <= num <= 255):
                return False
        return True
    except ValueError:
        return False
