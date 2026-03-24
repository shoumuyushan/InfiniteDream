"""Video compositor — stitch segments with transitions and B-roll."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from infinite_dream.models import BRoll, Transition, TransitionType, VideoSegment
from infinite_dream.utils.ffmpeg import ffmpeg_available, run_ffmpeg


class CompositorError(Exception):
    """Raised when composition fails."""


class Compositor:
    """Stitch segment videos together, adding transitions and B-roll."""

    # ── FFmpeg availability check ─────────────────

    @staticmethod
    def _check_ffmpeg() -> None:
        """Verify ffmpeg is available; raise :class:`CompositorError` if not."""
        if not ffmpeg_available():
            raise CompositorError(
                "ffmpeg is not installed or not on PATH. "
                "Install it (e.g. `brew install ffmpeg`) before composing."
            )

    # ── Transition selection ──────────────────────

    def select_transition(
        self,
        prev_scene_id: str | None,
        next_scene_id: str | None,
    ) -> Transition:
        """Choose a transition based on scene continuity.

        * Same scene → dissolve 0.5 s
        * Different scene (or unknown) → fade-to-black 1.0 s
        """
        if prev_scene_id and next_scene_id and prev_scene_id == next_scene_id:
            return Transition(type=TransitionType.DISSOLVE, duration_sec=0.5)
        return Transition(type=TransitionType.FADE_BLACK, duration_sec=1.0)

    # ── Simple concat (FFmpeg concat demuxer) ─────

    def concat_simple(self, video_paths: list[str], output_path: str) -> str:
        """Concatenate *video_paths* sequentially using FFmpeg concat demuxer.

        No transitions — just straight cuts.  This is the fastest method and
        works well when all inputs share the same codec / resolution.

        Returns the *output_path* on success.
        """
        self._check_ffmpeg()

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if not video_paths:
            raise CompositorError("No video paths provided for concatenation")

        if len(video_paths) == 1:
            # Single file — just copy
            import shutil as _shutil
            _shutil.copy2(video_paths[0], output_path)
            return output_path

        # Write a temporary concat list file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="concat_"
        ) as fh:
            for vp in video_paths:
                # Escape single quotes for the concat demuxer
                safe = str(Path(vp).resolve()).replace("'", "'\\''")
                fh.write(f"file '{safe}'\n")
            list_path = fh.name

        try:
            run_ffmpeg([
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                str(out),
            ])
        except Exception as exc:
            raise CompositorError(str(exc)) from exc
        finally:
            Path(list_path).unlink(missing_ok=True)

        return output_path

    # ── FFmpeg filter construction ────────────────

    def build_ffmpeg_filter(
        self,
        segment_count: int,
        transitions: list[Transition],
    ) -> str:
        """Build an FFmpeg ``filter_complex`` string for *segment_count* inputs.

        Each consecutive pair is joined by the corresponding transition.
        If there are fewer transitions than gaps the remaining joins default to
        a simple concat (cut).
        """
        if segment_count <= 0:
            return ""
        if segment_count == 1:
            return "[0:v][0:a]concat=n=1:v=1:a=1[outv][outa]"

        parts: list[str] = []
        prev_v = "[0:v]"
        prev_a = "[0:a]"

        for i in range(1, segment_count):
            trans = transitions[i - 1] if i - 1 < len(transitions) else Transition()
            cur_v = f"[{i}:v]"
            cur_a = f"[{i}:a]"
            out_v = f"[v{i}]"
            out_a = f"[a{i}]"

            dur = trans.duration_sec

            if trans.type == TransitionType.CUT:
                # Simple concat
                parts.append(
                    f"{prev_v}{cur_v}concat=n=2:v=1:a=0{out_v};"
                    f"{prev_a}{cur_a}concat=n=2:v=0:a=1{out_a}"
                )
            elif trans.type == TransitionType.DISSOLVE:
                parts.append(
                    f"{prev_v}{cur_v}xfade=transition=dissolve:duration={dur}:offset=0{out_v};"
                    f"{prev_a}{cur_a}acrossfade=d={dur}{out_a}"
                )
            elif trans.type == TransitionType.FADE_BLACK:
                parts.append(
                    f"{prev_v}{cur_v}xfade=transition=fade:duration={dur}:offset=0{out_v};"
                    f"{prev_a}{cur_a}acrossfade=d={dur}{out_a}"
                )
            elif trans.type == TransitionType.FADE_WHITE:
                parts.append(
                    f"{prev_v}{cur_v}xfade=transition=fadewhite:duration={dur}:offset=0{out_v};"
                    f"{prev_a}{cur_a}acrossfade=d={dur}{out_a}"
                )
            elif trans.type == TransitionType.WIPE:
                parts.append(
                    f"{prev_v}{cur_v}xfade=transition=wipeleft:duration={dur}:offset=0{out_v};"
                    f"{prev_a}{cur_a}acrossfade=d={dur}{out_a}"
                )
            else:
                # fallback: cut
                parts.append(
                    f"{prev_v}{cur_v}concat=n=2:v=1:a=0{out_v};"
                    f"{prev_a}{cur_a}concat=n=2:v=0:a=1{out_a}"
                )

            prev_v = out_v
            prev_a = out_a

        # Map final labels to output
        filter_str = ";".join(parts)
        filter_str += f";{prev_v}copy[outv];{prev_a}acopy[outa]"
        return filter_str

    # ── Compose ───────────────────────────────────

    def compose(
        self,
        segments: list[VideoSegment],
        transitions: list[Transition],
        b_rolls: list[BRoll],
        output_path: str,
    ) -> str:
        """Stitch *segments* together with *transitions* and *b_rolls*.

        If there are no transitions and no B-roll, falls back to
        :meth:`concat_simple` for a fast stream-copy concatenation.

        Uses ``ffmpeg`` via subprocess.  Raises :class:`CompositorError` if
        ffmpeg is not installed or the command fails.

        Returns the *output_path* on success.
        """
        self._check_ffmpeg()

        # Collect video paths in sequence order
        sorted_segments = sorted(segments, key=lambda s: s.sequence)

        # Validate all segments have video paths
        for seg in sorted_segments:
            if seg.video_path is None:
                raise CompositorError(
                    f"Segment {seg.id} (seq {seg.sequence}) has no video_path"
                )

        video_paths = [seg.video_path for seg in sorted_segments]  # type: ignore[misc]

        # Simple case: no transitions and no B-roll → fast concat
        if not transitions and not b_rolls:
            return self.concat_simple(video_paths, output_path)

        # Complex case: transitions and/or B-roll
        ordered_paths: list[str] = []
        ordered_transitions: list[Transition] = []
        broll_map: dict[int, list[BRoll]] = {}
        for br in b_rolls:
            broll_map.setdefault(br.insert_after_segment, []).append(br)

        for seg in sorted_segments:
            ordered_paths.append(seg.video_path)  # type: ignore[arg-type]

            # Append B-roll clips after this segment
            for br in broll_map.get(seg.sequence, []):
                if br.video_path:
                    # Transition into B-roll: dissolve
                    ordered_transitions.append(
                        Transition(type=TransitionType.DISSOLVE, duration_sec=0.5)
                    )
                    ordered_paths.append(br.video_path)

            # Transition to next main segment
            idx = len(ordered_paths) - 1  # current position
            if seg.sequence < len(segments):
                t_idx = seg.sequence - sorted_segments[0].sequence
                if t_idx < len(transitions):
                    ordered_transitions.append(transitions[t_idx])
                else:
                    ordered_transitions.append(Transition())

        # Build ffmpeg command
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if len(ordered_paths) == 1:
            # Single input — just copy
            cmd = [
                "ffmpeg", "-y",
                "-i", ordered_paths[0],
                "-c", "copy",
                str(out),
            ]
        else:
            filter_complex = self.build_ffmpeg_filter(len(ordered_paths), ordered_transitions)
            cmd = ["ffmpeg", "-y"]
            for p in ordered_paths:
                cmd.extend(["-i", p])
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-c:a", "aac",
                str(out),
            ])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise CompositorError(
                f"ffmpeg failed (rc={result.returncode}): {result.stderr[:500]}"
            )

        return output_path
