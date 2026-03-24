"""Tests for post-production modules."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from infinite_dream.core.audio import AudioMixer
from infinite_dream.core.compositor import Compositor, CompositorError
from infinite_dream.core.exporter import Exporter, _RESOLUTION_MAP
from infinite_dream.models import (
    EnhancedScript,
    ScriptSegment,
    Transition,
    TransitionType,
)
from infinite_dream.utils.ffmpeg import ffmpeg_available


# ── Compositor tests ──────────────────────────────


def test_compositor_select_transition_same_scene():
    """同场景返回 dissolve."""
    c = Compositor()
    t = c.select_transition("scene-1", "scene-1")
    assert t.type == TransitionType.DISSOLVE
    assert t.duration_sec == 0.5


def test_compositor_select_transition_different_scene():
    """不同场景返回 fade_black."""
    c = Compositor()
    t = c.select_transition("scene-1", "scene-2")
    assert t.type == TransitionType.FADE_BLACK
    assert t.duration_sec == 1.0


def test_compositor_select_transition_none_scene():
    """未知场景（None）返回 fade_black."""
    c = Compositor()
    t = c.select_transition(None, "scene-1")
    assert t.type == TransitionType.FADE_BLACK

    t2 = c.select_transition("scene-1", None)
    assert t2.type == TransitionType.FADE_BLACK

    t3 = c.select_transition(None, None)
    assert t3.type == TransitionType.FADE_BLACK


def test_compositor_concat_simple_builds_command():
    """验证 concat_simple 命令构建正确（mock subprocess）."""
    c = Compositor()

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    with (
        patch("infinite_dream.utils.ffmpeg.ffmpeg_available", return_value=True),
        patch("infinite_dream.utils.ffmpeg.subprocess.run", return_value=mock_result) as mock_run,
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.unlink"),
    ):
        c.concat_simple(["/tmp/a.mp4", "/tmp/b.mp4"], "/tmp/out.mp4")

        # run_ffmpeg should have been called once
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args[0]
        assert "-f" in call_args
        assert "concat" in call_args


def test_compositor_concat_simple_empty_raises():
    """空列表应该抛出 CompositorError."""
    c = Compositor()
    with (
        patch("infinite_dream.utils.ffmpeg.ffmpeg_available", return_value=True),
    ):
        with pytest.raises(CompositorError, match="No video paths"):
            c.concat_simple([], "/tmp/out.mp4")


# ── AudioMixer tests ─────────────────────────────


def test_audio_mixer_init():
    """AudioMixer 初始化参数正确."""
    mixer = AudioMixer(crossfade_duration=1.5, duck_db=-8.0)
    assert mixer.crossfade_duration == 1.5
    assert mixer.duck_db == -8.0


def test_audio_mixer_default_init():
    """AudioMixer 默认参数."""
    mixer = AudioMixer()
    assert mixer.crossfade_duration == 2.0
    assert mixer.duck_db == -12.0


# ── Exporter tests ────────────────────────────────


def test_exporter_resolution_mapping():
    """分辨率字符串映射正确."""
    assert _RESOLUTION_MAP["360p"] == (640, 360)
    assert _RESOLUTION_MAP["480p"] == (854, 480)
    assert _RESOLUTION_MAP["720p"] == (1280, 720)
    assert _RESOLUTION_MAP["1080p"] == (1920, 1080)
    assert _RESOLUTION_MAP["2k"] == (2560, 1440)
    assert _RESOLUTION_MAP["4k"] == (3840, 2160)


def test_exporter_generate_subtitle():
    """字幕生成格式正确."""
    exporter = Exporter()
    script = EnhancedScript(
        segments=[
            ScriptSegment(sequence=1, content="Hello world", estimated_duration_sec=5),
            ScriptSegment(sequence=2, content="Goodbye world", estimated_duration_sec=3),
        ],
        total_duration_sec=8,
    )
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        output_path = f.name

    try:
        result = exporter.generate_subtitle(script, output_path)
        assert result == output_path

        content = Path(output_path).read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # First entry
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:05,000"
        assert lines[2] == "Hello world"

        # Second entry
        assert lines[4] == "2"
        assert lines[5] == "00:00:05,000 --> 00:00:08,000"
        assert lines[6] == "Goodbye world"
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_exporter_generate_subtitle_timecode():
    """时间码累加正确 — 包含超过 60 秒和小数."""
    exporter = Exporter()
    script = EnhancedScript(
        segments=[
            ScriptSegment(sequence=1, content="Part 1", estimated_duration_sec=65),
            ScriptSegment(sequence=2, content="Part 2", estimated_duration_sec=10),
            ScriptSegment(sequence=3, content="Part 3", estimated_duration_sec=3700),
        ],
        total_duration_sec=3775,
    )
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        output_path = f.name

    try:
        exporter.generate_subtitle(script, output_path)
        content = Path(output_path).read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # Segment 1: 0:00 → 1:05
        assert lines[1] == "00:00:00,000 --> 00:01:05,000"

        # Segment 2: 1:05 → 1:15
        assert lines[5] == "00:01:05,000 --> 00:01:15,000"

        # Segment 3: 1:15 → 1:02:55 (75 + 3700 = 3775 sec = 1h 2m 55s)
        assert lines[9] == "00:01:15,000 --> 01:02:55,000"
    finally:
        Path(output_path).unlink(missing_ok=True)


def test_exporter_format_srt_time():
    """SRT 时间格式化辅助方法."""
    assert Exporter._format_srt_time(0.0) == "00:00:00,000"
    assert Exporter._format_srt_time(1.5) == "00:00:01,500"
    assert Exporter._format_srt_time(61.0) == "00:01:01,000"
    assert Exporter._format_srt_time(3661.123) == "01:01:01,123"


# ── FFmpeg utility tests ─────────────────────────


def test_ffmpeg_available():
    """ffmpeg 可用性检测."""
    with patch("infinite_dream.utils.ffmpeg.shutil.which", return_value="/usr/bin/ffmpeg"):
        assert ffmpeg_available() is True

    with patch("infinite_dream.utils.ffmpeg.shutil.which", return_value=None):
        assert ffmpeg_available() is False
