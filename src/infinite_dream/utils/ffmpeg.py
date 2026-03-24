"""FFmpeg utility functions."""

from __future__ import annotations

import shutil
import subprocess


class FFmpegError(Exception):
    """Raised when an FFmpeg operation fails."""


def ffmpeg_available() -> bool:
    """Check if ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None


def ffprobe_available() -> bool:
    """Check if ffprobe is available in PATH."""
    return shutil.which("ffprobe") is not None


def run_ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run ffmpeg with given args, raise on failure.

    Automatically adds ``-y -hide_banner -loglevel error`` before user args.
    """
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise FFmpegError(
            f"ffmpeg failed (rc={result.returncode}): {result.stderr[:500]}"
        )
    return result


def get_duration(file_path: str) -> float:
    """Get duration of a media file in seconds using ffprobe.

    Raises :class:`FFmpegError` if ffprobe is not available or fails.
    """
    if not ffprobe_available():
        raise FFmpegError("ffprobe is not installed or not on PATH.")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(
            f"ffprobe failed (rc={result.returncode}): {result.stderr[:500]}"
        )
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise FFmpegError(f"Could not parse duration from ffprobe output: {result.stdout!r}") from exc
