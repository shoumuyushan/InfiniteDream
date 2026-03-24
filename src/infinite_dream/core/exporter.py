"""Final video exporter — encode, resize, subtitle generation."""

from __future__ import annotations

from pathlib import Path

from infinite_dream.models import EnhancedScript
from infinite_dream.utils.ffmpeg import ffmpeg_available, run_ffmpeg


class ExportError(Exception):
    """Raised when export fails."""


_RESOLUTION_MAP: dict[str, tuple[int, int]] = {
    "360p": (640, 360),
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "2k": (2560, 1440),
    "4k": (3840, 2160),
}

_CODEC_MAP: dict[str, str] = {
    "h264": "libx264",
    "h265": "libx265",
    "hevc": "libx265",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1",
}


def _require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise ExportError(
            "ffmpeg is not installed or not on PATH. "
            "Install it before exporting."
        )


class Exporter:
    """Encode and export the final video, and generate SRT subtitles."""

    def export(
        self,
        video_path: str,
        output_path: str,
        format: str = "mp4",
        resolution: str = "1080p",
        fps: int = 30,
        codec: str = "h264",
    ) -> str:
        """Re-encode *video_path* to *output_path* with the given parameters.

        Returns *output_path* on success.
        """
        _require_ffmpeg()

        w, h = _RESOLUTION_MAP.get(resolution, (1920, 1080))
        vcodec = _CODEC_MAP.get(codec, "libx264")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            run_ffmpeg([
                "-i", video_path,
                "-vf", (
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
                ),
                "-r", str(fps),
                "-c:v", vcodec,
                "-preset", "medium",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-f", format,
                "-movflags", "+faststart",
                output_path,
            ])
        except Exception as exc:
            raise ExportError(str(exc)) from exc

        return output_path

    def export_preview(
        self,
        video_path: str,
        output_path: str,
    ) -> str:
        """Export a low-quality preview version (360p, low bitrate).

        This is useful for fast iteration during editing — much quicker to
        encode and smaller to transfer than a full-quality export.

        Returns *output_path* on success.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        w, h = _RESOLUTION_MAP["360p"]

        try:
            run_ffmpeg([
                "-i", video_path,
                "-vf", (
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
                ),
                "-r", "24",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "32",
                "-c:a", "aac",
                "-b:a", "64k",
                "-f", "mp4",
                "-movflags", "+faststart",
                output_path,
            ])
        except Exception as exc:
            raise ExportError(str(exc)) from exc

        return output_path

    def export_with_subtitle(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
    ) -> str:
        """Export video with subtitles burned in (hard-sub).

        Uses the ``subtitles`` video filter to render SRT text directly onto
        the video frames.

        Returns *output_path* on success.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Escape colons and backslashes for the subtitles filter path
        safe_sub = str(Path(subtitle_path).resolve()).replace("\\", "\\\\").replace(":", "\\:")

        try:
            run_ffmpeg([
                "-i", video_path,
                "-vf", f"subtitles={safe_sub}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-f", "mp4",
                "-movflags", "+faststart",
                output_path,
            ])
        except Exception as exc:
            raise ExportError(str(exc)) from exc

        return output_path

    # ── Subtitle generation ───────────────────────

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Convert seconds to SRT timestamp ``HH:MM:SS,mmm``."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def generate_subtitle(self, enhanced_script: EnhancedScript, output_path: str) -> str:
        """Generate an SRT subtitle file from an :class:`EnhancedScript`.

        Each :class:`ScriptSegment` becomes one subtitle entry, timed
        sequentially based on ``estimated_duration_sec``.  Time codes are
        computed by accumulating segment durations so they correctly reflect
        the position within the final video.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        current_time = 0.0

        for idx, seg in enumerate(enhanced_script.segments, start=1):
            start_ts = self._format_srt_time(current_time)
            end_time = current_time + seg.estimated_duration_sec
            end_ts = self._format_srt_time(end_time)

            lines.append(str(idx))
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(seg.content.strip())
            lines.append("")  # blank line separator

            current_time = end_time

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        return output_path
