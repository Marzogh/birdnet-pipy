from unittest.mock import MagicMock, patch

import pytest
import requests


class TestHaModeDetection:
    def test_runtime_mode_native_without_token(self, monkeypatch):
        monkeypatch.delenv('SUPERVISOR_TOKEN', raising=False)
        from core.ha_mode import MODE_NATIVE, get_runtime_mode_info

        mode_info = get_runtime_mode_info(force_refresh=True)
        assert mode_info['mode'] == MODE_NATIVE
        assert mode_info['token_present'] is False

    def test_runtime_mode_ha_with_reachable_supervisor(self, monkeypatch):
        monkeypatch.setenv('SUPERVISOR_TOKEN', 'test-token')
        with patch('core.ha_mode.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            from core.ha_mode import MODE_HOME_ASSISTANT, get_runtime_mode_info

            mode_info = get_runtime_mode_info(force_refresh=True)
            assert mode_info['mode'] == MODE_HOME_ASSISTANT
            assert mode_info['supervisor_available'] is True

    def test_runtime_mode_native_on_probe_failure(self, monkeypatch):
        monkeypatch.setenv('SUPERVISOR_TOKEN', 'test-token')
        with patch('core.ha_mode.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            from core.ha_mode import MODE_NATIVE, get_runtime_mode_info

            mode_info = get_runtime_mode_info(force_refresh=True)
            assert mode_info['mode'] == MODE_NATIVE
            assert mode_info['supervisor_available'] is False


class TestSupervisorClient:
    def test_get_self_addon_info_success(self, monkeypatch):
        monkeypatch.setenv('SUPERVISOR_TOKEN', 'test-token')
        with patch('core.supervisor_client.requests.request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'result': 'ok',
                'data': {'version': '1.2.3'},
            }
            mock_request.return_value = mock_response

            from core.supervisor_client import get_self_addon_info

            result = get_self_addon_info()
            assert result['version'] == '1.2.3'

    def test_update_self_addon_falls_back_on_404(self, monkeypatch):
        monkeypatch.setenv('SUPERVISOR_TOKEN', 'test-token')

        first_404 = MagicMock()
        first_404.status_code = 404
        first_404.json.return_value = {'result': 'error', 'message': 'Not found'}

        second_ok = MagicMock()
        second_ok.status_code = 200
        second_ok.json.return_value = {'result': 'ok', 'data': {'job_id': 'abc'}}

        with patch('core.supervisor_client.requests.request', side_effect=[first_404, second_ok]) as mock_request:
            from core.supervisor_client import update_self_addon

            result = update_self_addon()
            assert result['job_id'] == 'abc'
            assert mock_request.call_count == 2

    def test_request_requires_supervisor_token(self, monkeypatch):
        monkeypatch.delenv('SUPERVISOR_TOKEN', raising=False)
        from core.supervisor_client import SupervisorClientError, get_self_addon_info

        with pytest.raises(SupervisorClientError, match='SUPERVISOR_TOKEN is not set'):
            get_self_addon_info()

    def test_request_wraps_network_error(self, monkeypatch):
        monkeypatch.setenv('SUPERVISOR_TOKEN', 'test-token')

        with patch(
            'core.supervisor_client.requests.request',
            side_effect=requests.exceptions.ConnectTimeout('timed out'),
        ):
            from core.supervisor_client import SupervisorClientError, get_self_addon_info

            with pytest.raises(SupervisorClientError, match='Supervisor request failed'):
                get_self_addon_info()
