"""Audio processing — extraction, crossfade, ducking, shift-blend."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class AudioError(Exception):
    """Raised when an audio operation fails."""


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise AudioError(
            "ffmpeg is not installed or not on PATH. "
            "Install it (e.g. `brew install ffmpeg`) before processing audio."
        )


def _run(cmd: list[str]) -> None:
    """Run a command and raise :class:`AudioError` on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioError(f"Command failed (rc={result.returncode}): {result.stderr[:500]}")


class AudioMixer:
    """Audio extraction, BGM blending, cross-fade, shift-and-blend, and ducking."""

    def __init__(self, crossfade_duration: float = 2.0, duck_db: float = -12.0) -> None:
        self.crossfade_duration = crossfade_duration
        self.duck_db = duck_db

    # ── Primitives ────────────────────────────────

    def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract the audio track from *video_path* → *output_path* (e.g. .wav)."""
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        _run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            output_path,
        ])
        return output_path

    def crossfade(
        self,
        audio_a: str,
        audio_b: str,
        overlap_sec: float,
        output_path: str,
    ) -> str:
        """Cross-fade two audio files with *overlap_sec* seconds of overlap."""
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        _run([
            "ffmpeg", "-y",
            "-i", audio_a,
            "-i", audio_b,
            "-filter_complex",
            f"[0:a][1:a]acrossfade=d={overlap_sec}:c1=tri:c2=tri[outa]",
            "-map", "[outa]",
            output_path,
        ])
        return output_path

    def shift_and_blend(
        self,
        audio: str,
        shift_ms: int,
        blend_duration: float,
        output_path: str,
    ) -> str:
        """Duplicate *audio*, shift the copy by *shift_ms* ms, and blend them.

        This creates the "offset layering" effect popular in cinematic music
        scoring — the same track plays twice with a slight delay, giving a
        richer stereo feel.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        delay_sec = shift_ms / 1000.0
        _run([
            "ffmpeg", "-y",
            "-i", audio,
            "-filter_complex",
            (
                f"[0:a]acopy[orig];"
                f"[0:a]adelay={shift_ms}|{shift_ms}[delayed];"
                f"[orig][delayed]amix=inputs=2:duration=longest:"
                f"dropout_transition={blend_duration}[outa]"
            ),
            "-map", "[outa]",
            output_path,
        ])
        return output_path

    def duck_bgm(self, bgm: str, dialogue: str, output_path: str) -> str:
        """Lower *bgm* volume by ``self.duck_db`` wherever *dialogue* has audio.

        Uses FFmpeg's sidechain compressor to automatically duck the BGM.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        _run([
            "ffmpeg", "-y",
            "-i", bgm,
            "-i", dialogue,
            "-filter_complex",
            (
                f"[0:a]asplit=2[bgm1][bgm2];"
                f"[bgm1][1:a]sidechaincompress="
                f"threshold=0.02:ratio=10:attack=200:release=1000:"
                f"level_sc=1:mix=1[ducked];"
                f"[ducked]volume={self.duck_db}dB[bgm_ducked];"
                f"[bgm_ducked][1:a]amix=inputs=2:duration=longest[outa]"
            ),
            "-map", "[outa]",
            output_path,
        ])
        return output_path

    # ── Full pipeline ─────────────────────────────

    def process_full(
        self,
        video_path: str,
        segment_video_paths: list[str],
        output_path: str,
    ) -> str:
        """Run the complete audio post-processing pipeline.

        1. Extract audio from the composed *video_path*.
        2. For each segment, extract its individual audio to allow future
           per-segment processing (e.g. TTS alignment).
        3. Output the final processed audio to *output_path*.

        Currently this is a straightforward extraction.  BGM ducking,
        shift-blend, and crossfade should be driven by higher-level
        orchestration once TTS and music generation are wired.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Extract the main composed audio
        self.extract_audio(video_path, output_path)

        # Optionally extract per-segment audio for downstream use
        for i, seg_path in enumerate(segment_video_paths):
            seg_audio = str(Path(output_path).parent / f"segment_{i:03d}.wav")
            try:
                self.extract_audio(seg_path, seg_audio)
            except AudioError:
                # Non-fatal — some mock segments may have no real audio
                pass

        return output_path
