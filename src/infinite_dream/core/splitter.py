"""Segment splitter — convert enhanced script segments into a video segment plan."""

from __future__ import annotations

import math

from infinite_dream.models.project import (
    EnhancedScript,
    ScriptSegment,
    SegmentPlan,
    VideoSegment,
)


class SegmentSplitter:
    """Split an enhanced script into time-bounded video segments."""

    def split(
        self,
        enhanced: EnhancedScript,
        max_segment_duration: float = 15.0,
    ) -> SegmentPlan:
        """Create a SegmentPlan from an EnhancedScript.

        Each ScriptSegment maps to one or more VideoSegments. If a script segment
        exceeds *max_segment_duration*, it is subdivided. Adjacent segments carry
        continuity metadata (prev_segment_end_description / next_segment_start_hint).
        """
        video_segments: list[VideoSegment] = []
        seq = 1

        for script_seg in enhanced.segments:
            duration = float(script_seg.estimated_duration_sec)

            if duration <= max_segment_duration:
                vs = self._make_video_segment(script_seg, seq, duration)
                video_segments.append(vs)
                seq += 1
            else:
                # Split into roughly equal sub-segments
                n_parts = math.ceil(duration / max_segment_duration)
                part_duration = duration / n_parts
                content_lines = self._split_content(script_seg.content, n_parts)

                for part_idx in range(n_parts):
                    vs = VideoSegment(
                        sequence=seq,
                        script_segment_id=script_seg.id,
                        duration_sec=round(part_duration, 1),
                        character_keywords=[],  # Will be filled by prompt builder
                        environment_keywords=[],
                        style_keywords=[],
                        camera_motion=script_seg.camera_direction or "static",
                    )
                    # Store partial content as the visual prompt seed
                    vs.visual_prompt = content_lines[part_idx]
                    video_segments.append(vs)
                    seq += 1

        # Fill continuity links
        self._link_segments(video_segments)

        total_dur = round(sum(vs.duration_sec for vs in video_segments))

        return SegmentPlan(
            enhanced_script_id=enhanced.id,
            target_total_duration_sec=total_dur,
            max_segment_duration_sec=max_segment_duration,
            segments=video_segments,
        )

    # ── Internal helpers ─────────────────────────

    @staticmethod
    def _make_video_segment(
        script_seg: ScriptSegment,
        seq: int,
        duration: float,
    ) -> VideoSegment:
        return VideoSegment(
            sequence=seq,
            script_segment_id=script_seg.id,
            duration_sec=duration,
            visual_prompt=script_seg.content,
            camera_motion=script_seg.camera_direction or "static",
        )

    @staticmethod
    def _split_content(content: str, n_parts: int) -> list[str]:
        """Best-effort split of text content into n_parts roughly equal pieces."""
        sentences = content.replace("。", "。\n").replace(". ", ".\n").splitlines()
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= n_parts:
            # Pad with duplicates of the last sentence if needed
            while len(sentences) < n_parts:
                sentences.append(sentences[-1] if sentences else content)
            return sentences

        # Distribute sentences across parts
        parts: list[list[str]] = [[] for _ in range(n_parts)]
        per_part = len(sentences) / n_parts
        for i, sent in enumerate(sentences):
            bucket = min(int(i / per_part), n_parts - 1)
            parts[bucket].append(sent)

        return [" ".join(p) for p in parts]

    @staticmethod
    def _link_segments(segments: list[VideoSegment]) -> None:
        """Add prev/next continuity hints between adjacent segments."""
        for i, seg in enumerate(segments):
            if i > 0:
                prev = segments[i - 1]
                seg.prev_segment_end_description = (
                    prev.visual_prompt[:120] if prev.visual_prompt else None
                )
            if i < len(segments) - 1:
                nxt = segments[i + 1]
                seg.next_segment_start_hint = (
                    nxt.visual_prompt[:120] if nxt.visual_prompt else None
                )
