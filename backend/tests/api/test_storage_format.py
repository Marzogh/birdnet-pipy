"""The API publishes confirmed jobs only; all host metadata is synthetic."""
import json
import time
from unittest.mock import Mock

import pytest


@pytest.fixture
def formatter(api_client, tmp_path, monkeypatch):
    import core.auth as auth
    import core.storage_discovery as discovery
    import core.storage_format as jobs
    monkeypatch.setattr(jobs, 'FLAGS', tmp_path)
    monkeypatch.setattr(auth, 'is_auth_enabled', lambda: True)
    monkeypatch.setattr(auth, 'is_authenticated', lambda: True)
    monkeypatch.setattr(discovery, 'get_storage_devices', lambda: {'state': 'available', 'devices': [
        {'path': '/dev/sda', 'device_id': 'synthetic', 'name': 'BIRDSTORE', 'size_bytes': 500000000000,
         'preparation_eligible': True}]})
    (tmp_path / 'storage-format-status.json').write_text(json.dumps(
        {'state': 'idle', 'ready': True, 'updated_at': time.time()}))
    return jobs, {'path': '/dev/sda', 'device_id': 'synthetic', 'confirmation': 'BIRDSTORE'}


def test_confirmed_request_is_queued_without_commands_and_blocks_other_writes(api_client, formatter, monkeypatch):
    jobs, payload = formatter
    monkeypatch.setattr('subprocess.run', Mock(side_effect=AssertionError('No host commands from API')))
    response = api_client.post('/api/system/storage/format', json=payload)
    assert response.status_code == 202
    job = json.loads((jobs.FLAGS / 'storage-format-request.json').read_text())
    assert job['device_id'] == 'synthetic'
    assert job['confirmation'] == 'BIRDSTORE'
    assert api_client.get('/api/system/storage/format-status').json['id'] == job['id']
    assert api_client.post('/api/system/storage/format', json=payload).status_code == 409
    assert api_client.post('/api/system/restart', json={}).status_code == 409


def test_auth_disabled_installation_cannot_format(api_client, formatter, monkeypatch):
    _, payload = formatter
    monkeypatch.setattr('core.auth.is_auth_enabled', lambda: False)
    response = api_client.post('/api/system/storage/format', json=payload)
    assert response.status_code == 403
    assert 'sign in' in response.json['error']


def test_unavailable_helper_or_wrong_confirmation_cannot_queue(api_client, formatter):
    jobs, payload = formatter
    assert api_client.post('/api/system/storage/format', json=dict(payload, confirmation='wrong')).status_code == 400
    (jobs.FLAGS / 'storage-format-status.json').unlink()
    assert api_client.post('/api/system/storage/format', json=payload).status_code == 503
    assert not jobs.format_pending()
