"""Audio processing — extraction, crossfade, ducking, shift-blend."""

from __future__ import annotations

from pathlib import Path

from infinite_dream.utils.ffmpeg import ffmpeg_available, run_ffmpeg


class AudioError(Exception):
    """Raised when an audio operation fails."""


def _require_ffmpeg() -> None:
    if not ffmpeg_available():
        raise AudioError(
            "ffmpeg is not installed or not on PATH. "
            "Install it (e.g. `brew install ffmpeg`) before processing audio."
        )


def _run(cmd: list[str]) -> None:
    """Run a command via :func:`run_ffmpeg` and raise :class:`AudioError` on failure."""
    try:
        # Build args from the full command: strip the leading "ffmpeg" if present
        args = cmd[1:] if cmd and cmd[0] == "ffmpeg" else cmd
        # Remove -y if present (run_ffmpeg adds it automatically)
        args = [a for a in args if a != "-y"]
        run_ffmpeg(args)
    except Exception as exc:
        raise AudioError(str(exc)) from exc


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

    # ── New methods ───────────────────────────────

    def merge_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> str:
        """Merge processed *audio_path* back into *video_path*.

        The video stream is copied as-is; the audio stream is replaced with
        the provided audio file.

        Returns *output_path* on success.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        _run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ])
        return output_path

    @staticmethod
    def generate_silence(duration_sec: float, output_path: str) -> str:
        """Generate a silent audio file of *duration_sec* seconds.

        Useful for segments that have no audio track (e.g. AI-generated video
        clips with no sound).

        Returns *output_path* on success.
        """
        _require_ffmpeg()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        _run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo:d={duration_sec}",
            "-t", str(duration_sec),
            "-acodec", "pcm_s16le",
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

        1. Extract audio from each segment video.
        2. Cross-fade consecutive audio segments using ``self.crossfade_duration``.
        3. Merge the processed audio back into the composed *video_path*.

        Returns *output_path* on success.
        """
        _require_ffmpeg()
        out_dir = Path(output_path).parent
        out_dir.mkdir(parents=True, exist_ok=True)

        if not segment_video_paths:
            # Nothing to process — just extract the main audio
            self.extract_audio(video_path, output_path)
            return output_path

        # Step 1: Extract audio from each segment
        seg_audios: list[str] = []
        for i, seg_path in enumerate(segment_video_paths):
            seg_audio = str(out_dir / f"segment_{i:03d}.wav")
            try:
                self.extract_audio(seg_path, seg_audio)
                seg_audios.append(seg_audio)
            except AudioError:
                # Segment may have no audio — generate silence as fallback
                silence_path = str(out_dir / f"segment_{i:03d}_silence.wav")
                self.generate_silence(8.0, silence_path)
                seg_audios.append(silence_path)

        # Step 2: Crossfade consecutive segments
        if len(seg_audios) == 1:
            merged_audio = seg_audios[0]
        else:
            merged_audio = seg_audios[0]
            for i in range(1, len(seg_audios)):
                next_merged = str(out_dir / f"crossfade_{i:03d}.wav")
                self.crossfade(merged_audio, seg_audios[i], self.crossfade_duration, next_merged)
                merged_audio = next_merged

        # Step 3: Merge the processed audio back into the video
        self.merge_audio_video(video_path, merged_audio, output_path)

        return output_path
