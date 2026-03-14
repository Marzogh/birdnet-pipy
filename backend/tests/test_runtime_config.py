"""Tests for runtime setting change classification."""

from core.runtime_config import classify_setting_changes


class TestClassifySettingChanges:
    def test_model_switch_requires_full_restart(self):
        plan = classify_setting_changes(
            ["model.type"],
            old_settings={"model": {"type": "birdnet"}},
            new_settings={"model": {"type": "birdnet_v3"}}
        )

        assert plan["full_restart_required"] is True
        assert "model.type" in plan["full_restart_paths"]

    def test_audio_overlap_is_component_restart_only(self):
        plan = classify_setting_changes(
            ["audio.overlap"],
            old_settings={"audio": {"recording_mode": "pulseaudio", "overlap": 0.0}},
            new_settings={"audio": {"recording_mode": "pulseaudio", "overlap": 1.0}}
        )

        assert plan["full_restart_required"] is False
        assert "audio.overlap" in plan["component_restarts"]

    def test_recording_mode_switch_to_rtsp_requires_full_restart(self):
        plan = classify_setting_changes(
            ["audio.recording_mode"],
            old_settings={"audio": {"recording_mode": "pulseaudio"}},
            new_settings={"audio": {"recording_mode": "rtsp"}}
        )

        assert plan["full_restart_required"] is True
        assert "audio.recording_mode" in plan["full_restart_paths"]

    def test_recording_mode_switch_away_from_rtsp_requires_full_restart(self):
        plan = classify_setting_changes(
            ["audio.recording_mode"],
            old_settings={"audio": {"recording_mode": "rtsp"}},
            new_settings={"audio": {"recording_mode": "pulseaudio"}}
        )

        assert plan["full_restart_required"] is True
        assert "audio.recording_mode" in plan["full_restart_paths"]

    def test_rtsp_url_change_requires_full_restart_when_rtsp_mode_active(self):
        plan = classify_setting_changes(
            ["audio.rtsp_url"],
            old_settings={"audio": {"recording_mode": "rtsp", "rtsp_url": "rtsp://old"}},
            new_settings={"audio": {"recording_mode": "rtsp", "rtsp_url": "rtsp://new"}}
        )

        assert plan["full_restart_required"] is True
        assert "audio.rtsp_url" in plan["full_restart_paths"]

    def test_rtsp_url_change_is_component_restart_when_not_in_rtsp_mode(self):
        plan = classify_setting_changes(
            ["audio.rtsp_url"],
            old_settings={"audio": {"recording_mode": "pulseaudio", "rtsp_url": "rtsp://old"}},
            new_settings={"audio": {"recording_mode": "pulseaudio", "rtsp_url": "rtsp://new"}}
        )

        assert plan["full_restart_required"] is False
        assert "audio.rtsp_url" in plan["component_restarts"]

    def test_location_change_requires_full_restart(self):
        plan = classify_setting_changes(["location.latitude", "location.longitude"])

        assert plan["full_restart_required"] is True
        assert "location.latitude" in plan["full_restart_paths"]
        assert "location.longitude" in plan["full_restart_paths"]
