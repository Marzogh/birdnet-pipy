"""Timezone service - reads from config file, not TZ env var."""

from datetime import datetime
from zoneinfo import ZoneInfo

from core.logging_config import get_logger
from core.runtime_config import get_runtime_settings

logger = get_logger(__name__)

_UTC = ZoneInfo("UTC")


def get_timezone_str() -> str:
    """Get timezone name from config file, or 'UTC' if not set."""
    settings = get_runtime_settings()
    return settings.get('location', {}).get('timezone') or 'UTC'


def get_timezone() -> ZoneInfo:
    """Get current timezone as ZoneInfo object."""
    tz_str = get_timezone_str()
    try:
        return ZoneInfo(tz_str)
    except Exception:
        logger.warning(f"Invalid timezone '{tz_str}', using UTC")
        return _UTC


def local_now() -> datetime:
    """Get current local time based on configured timezone.

    Returns a naive datetime in the user's local timezone.
    Uses UTC from the OS, then converts — no dependency on TZ env var.
    """
    tz = get_timezone()
    return datetime.now(tz).replace(tzinfo=None)
