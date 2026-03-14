"""Tests for the POST /api/stream/test endpoint."""
import subprocess
from unittest.mock import MagicMock, patch


class TestStreamTestEndpoint:
    """Tests for stream URL testing API."""

    def test_missing_url(self, api_client):
        resp = api_client.post('/api/stream/test', json={'type': 'http_stream'})
        assert resp.status_code == 400
        assert 'No URL' in resp.json['error']

    def test_empty_url(self, api_client):
        resp = api_client.post('/api/stream/test', json={'url': '', 'type': 'http_stream'})
        assert resp.status_code == 400

    def test_invalid_type(self, api_client):
        resp = api_client.post('/api/stream/test', json={'url': 'http://example.com/stream', 'type': 'invalid'})
        assert resp.status_code == 400
        assert 'Invalid type' in resp.json['error']

    def test_invalid_http_url_format(self, api_client):
        resp = api_client.post('/api/stream/test', json={'url': 'ftp://bad', 'type': 'http_stream'})
        assert resp.status_code == 200
        assert resp.json['success'] is False
        assert 'Invalid URL format' in resp.json['message']

    def test_invalid_rtsp_url_format(self, api_client):
        resp = api_client.post('/api/stream/test', json={'url': 'http://wrong', 'type': 'rtsp'})
        assert resp.status_code == 200
        assert resp.json['success'] is False
        assert 'Invalid URL format' in resp.json['message']

    @patch('core.audio_manager.subprocess.Popen')
    def test_http_stream_success(self, mock_popen, api_client):
        """Successful HTTP stream probe returns success=true."""
        mock_curl = MagicMock()
        mock_curl.stdout = MagicMock()
        mock_curl.wait.return_value = 0

        mock_ffmpeg = MagicMock()
        mock_ffmpeg.communicate.return_value = (b'', b'')
        mock_ffmpeg.returncode = 0

        mock_popen.side_effect = [mock_curl, mock_ffmpeg]

        resp = api_client.post('/api/stream/test', json={
            'url': 'http://example.com:8888/stream.mp3',
            'type': 'http_stream',
        })
        assert resp.status_code == 200
        assert resp.json['success'] is True

    @patch('core.audio_manager.subprocess.Popen')
    def test_http_stream_failure(self, mock_popen, api_client):
        """Failed HTTP stream probe returns success=false with error message."""
        mock_curl = MagicMock()
        mock_curl.stdout = MagicMock()
        mock_curl.wait.return_value = 0

        mock_ffmpeg = MagicMock()
        mock_ffmpeg.communicate.return_value = (b'', b'Connection refused\n')
        mock_ffmpeg.returncode = 1

        mock_popen.side_effect = [mock_curl, mock_ffmpeg]

        resp = api_client.post('/api/stream/test', json={
            'url': 'http://example.com:8888/stream.mp3',
            'type': 'http_stream',
        })
        assert resp.status_code == 200
        assert resp.json['success'] is False
        assert 'probe failed' in resp.json['message']

    @patch('core.audio_manager.subprocess.run')
    def test_rtsp_stream_success(self, mock_run, api_client):
        """Successful RTSP probe returns success=true."""
        mock_run.return_value = MagicMock(returncode=0, stderr='')

        resp = api_client.post('/api/stream/test', json={
            'url': 'rtsp://192.168.1.100:554/stream',
            'type': 'rtsp',
        })
        assert resp.status_code == 200
        assert resp.json['success'] is True

    @patch('core.audio_manager.subprocess.Popen')
    def test_http_stream_timeout(self, mock_popen, api_client):
        """Timeout during HTTP stream probe returns appropriate message."""
        mock_curl = MagicMock()
        mock_curl.stdout = MagicMock()

        mock_ffmpeg = MagicMock()
        mock_ffmpeg.communicate.side_effect = subprocess.TimeoutExpired(cmd='ffmpeg', timeout=10)
        mock_ffmpeg.kill.return_value = None
        mock_ffmpeg.wait.return_value = None

        mock_curl.kill.return_value = None
        mock_curl.wait.return_value = None

        mock_popen.side_effect = [mock_curl, mock_ffmpeg]

        resp = api_client.post('/api/stream/test', json={
            'url': 'http://example.com:8888/stream.mp3',
            'type': 'http_stream',
        })
        assert resp.status_code == 200
        assert resp.json['success'] is False
        assert 'timed out' in resp.json['message']
