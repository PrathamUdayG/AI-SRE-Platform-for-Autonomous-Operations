from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current time in UTC with timezone info."""
    return datetime.now(timezone.utc)
