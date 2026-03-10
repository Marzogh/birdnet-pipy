"""Tests for the timezone service module."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import core.timezone_service as tz_module
from core.timezone_service import get_timezone, get_timezone_str, local_now


def _mock_settings(timezone=None):
    """Return a mock settings dict with the given timezone."""
    return {'location': {'timezone': timezone}}


class TestTimezoneService:
    """Test timezone service functionality."""

    def test_returns_tz_from_config(self):
        """Test that timezone is returned from config settings."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('Europe/Berlin')):
            assert get_timezone_str() == "Europe/Berlin"

    def test_returns_utc_when_timezone_not_set(self):
        """Test that UTC is returned when timezone is not configured."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings(None)):
            assert get_timezone_str() == "UTC"

    def test_returns_utc_when_timezone_empty(self):
        """Test that UTC is returned when timezone is empty string."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('')):
            assert get_timezone_str() == "UTC"

    def test_returns_utc_when_location_missing(self):
        """Test that UTC is returned when location key is missing."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value={}):
            assert get_timezone_str() == "UTC"

    def test_get_timezone_returns_zoneinfo(self):
        """Test that get_timezone returns a ZoneInfo object."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('America/New_York')):
            tz = get_timezone()
            assert tz == ZoneInfo("America/New_York")

    def test_get_timezone_returns_utc_for_invalid_tz(self):
        """Test that invalid timezone triggers fallback to UTC."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('Invalid/Timezone')):
            tz = get_timezone()
            assert tz == ZoneInfo("UTC")

    def test_local_now_returns_naive_datetime(self):
        """Test that local_now returns a naive datetime (no tzinfo)."""
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('America/New_York')):
            now = local_now()
            assert isinstance(now, datetime)
            assert now.tzinfo is None

    def test_local_now_differs_from_utc_when_timezone_set(self):
        """Test that local_now returns time in the configured timezone, not UTC."""
        # Use a timezone with a known offset from UTC
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('Pacific/Auckland')):
            nz_now = local_now()
        with patch.object(tz_module, 'get_runtime_settings',
                          return_value=_mock_settings('UTC')):
            utc_now = local_now()
        # Auckland is UTC+12 or UTC+13 (DST), so the difference should be significant
        diff_hours = abs((nz_now - utc_now).total_seconds()) / 3600
        assert 11.5 < diff_hours < 13.5
