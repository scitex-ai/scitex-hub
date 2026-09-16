"""Small security helpers shared by HTTP-facing applications."""


def safe_log_field(value: object, *, limit: int = 512) -> str:
    """Render an untrusted value as one bounded physical log line."""
    return str(value).replace("\r", "\\r").replace("\n", "\\n")[:limit]
