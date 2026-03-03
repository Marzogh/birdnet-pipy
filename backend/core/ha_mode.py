"""Runtime mode detection helpers.

Determines whether the app is running inside a Home Assistant add-on by:
1. Checking for SUPERVISOR_TOKEN
2. Probing the Supervisor API endpoint
"""

from __future__ import annotations

import os
import time

import requests

from core.logging_config import get_logger
from core.supervisor_client import SUPERVISOR_BASE_URL

logger = get_logger(__name__)

MODE_NATIVE = "native"
MODE_HOME_ASSISTANT = "ha"

MODE_PROBE_TIMEOUT_SECONDS = float(os.environ.get("SUPERVISOR_PROBE_TIMEOUT_SECONDS", "2"))
MODE_CACHE_TTL_SECONDS = int(os.environ.get("SUPERVISOR_MODE_CACHE_TTL_SECONDS", "30"))

# Process-level cache. This intentionally persists across calls to reduce
# probe churn; tests should use force_refresh=True to avoid stale state.
_mode_cache = {
    "mode": MODE_NATIVE,
    "token_present": False,
    "supervisor_available": False,
    "probe_status": None,
    "probe_error": None,
    "last_probe_ts": 0.0,
}


def _probe_supervisor(token: str) -> tuple[bool, int | None, str | None]:
    """Probe Supervisor API reachability with the provided token."""
    probe_url = f"{SUPERVISOR_BASE_URL}/addons/self/info"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(probe_url, headers=headers, timeout=MODE_PROBE_TIMEOUT_SECONDS)
        # 200: fully operational. 401/403: Supervisor reachable but access denied.
        reachable = response.status_code in (200, 401, 403)
        return reachable, response.status_code, None
    except requests.exceptions.RequestException as exc:
        return False, None, str(exc)


def get_runtime_mode_info(force_refresh: bool = False) -> dict[str, object]:
    """Return cached runtime mode details."""
    now = time.time()
    if (
        not force_refresh
        and _mode_cache["last_probe_ts"]
        and now - float(_mode_cache["last_probe_ts"]) < MODE_CACHE_TTL_SECONDS
    ):
        return dict(_mode_cache)

    token = (os.environ.get("SUPERVISOR_TOKEN") or "").strip()
    token_present = bool(token)

    if not token_present:
        _mode_cache.update({
            "mode": MODE_NATIVE,
            "token_present": False,
            "supervisor_available": False,
            "probe_status": None,
            "probe_error": "SUPERVISOR_TOKEN is not set",
            "last_probe_ts": now,
        })
        return dict(_mode_cache)

    supervisor_available, probe_status, probe_error = _probe_supervisor(token)
    mode = MODE_HOME_ASSISTANT if supervisor_available else MODE_NATIVE

    _mode_cache.update({
        "mode": mode,
        "token_present": True,
        "supervisor_available": supervisor_available,
        "probe_status": probe_status,
        "probe_error": probe_error,
        "last_probe_ts": now,
    })

    if not supervisor_available:
        logger.debug("Supervisor probe failed; falling back to native mode", extra={
            "probe_error": probe_error,
            "probe_status": probe_status,
        })

    return dict(_mode_cache)


def get_runtime_mode(force_refresh: bool = False) -> str:
    """Return runtime mode string: 'ha' or 'native'."""
    return str(get_runtime_mode_info(force_refresh=force_refresh)["mode"])
