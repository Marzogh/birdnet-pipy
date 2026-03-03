"""Minimal Home Assistant Supervisor API client."""

from __future__ import annotations

import os
from typing import Any

import requests

from core.logging_config import get_logger

logger = get_logger(__name__)

SUPERVISOR_BASE_URL = os.environ.get("SUPERVISOR_BASE_URL", "http://supervisor").rstrip("/")
SUPERVISOR_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("SUPERVISOR_REQUEST_TIMEOUT_SECONDS", "15"))


class SupervisorClientError(RuntimeError):
    """Supervisor API request failure."""

    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _get_supervisor_token() -> str:
    token = (os.environ.get("SUPERVISOR_TOKEN") or "").strip()
    if not token:
        raise SupervisorClientError("SUPERVISOR_TOKEN is not set")
    return token


def _parse_response_payload(response: requests.Response) -> Any:
    try:
        payload = response.json()
    except ValueError:
        return {}

    if isinstance(payload, dict):
        if payload.get("result") == "error":
            message = payload.get("message", "Supervisor API returned error")
            if 200 <= response.status_code < 300:
                logger.warning(
                    "Supervisor API returned logical error despite HTTP success",
                    extra={"status_code": response.status_code, "message": message},
                )
            raise SupervisorClientError(message, status_code=response.status_code, payload=payload)
        if "data" in payload:
            return payload["data"]

    return payload


def _request_supervisor(method: str, path: str) -> Any:
    token = _get_supervisor_token()
    url = f"{SUPERVISOR_BASE_URL}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=SUPERVISOR_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException as exc:
        raise SupervisorClientError(f"Supervisor request failed: {exc}") from exc

    if response.status_code >= 400:
        payload = None
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        raise SupervisorClientError(
            f"Supervisor API returned status {response.status_code}",
            status_code=response.status_code,
            payload=payload,
        )

    return _parse_response_payload(response)


def get_self_addon_info() -> dict[str, Any]:
    """Return metadata for the running add-on."""
    payload = _request_supervisor("GET", "/addons/self/info")
    return payload if isinstance(payload, dict) else {}


def restart_self_addon() -> Any:
    """Request Home Assistant Supervisor to restart this add-on."""
    return _request_supervisor("POST", "/addons/self/restart")


def update_self_addon() -> Any:
    """Request Home Assistant Supervisor to update this add-on."""
    try:
        return _request_supervisor("POST", "/store/addons/self/update")
    except SupervisorClientError as exc:
        # Compatibility fallback for older Supervisor API variants.
        if exc.status_code == 404:
            return _request_supervisor("POST", "/addons/self/update")
        raise
