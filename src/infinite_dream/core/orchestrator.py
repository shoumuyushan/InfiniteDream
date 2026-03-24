"""Video generation orchestrator — concurrent segment generation with retry."""

from __future__ import annotations

import asyncio

from infinite_dream.adapters.base import VideoAPIAdapter
from infinite_dream.models import SegmentStatus, VideoSegment


class VideoOrchestrator:
    """Orchestrate concurrent video generation for all segments."""

    def __init__(
        self,
        adapter: VideoAPIAdapter,
        max_concurrency: int = 3,
        max_retries: int = 3,
    ) -> None:
        self.adapter = adapter
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = max_retries

    async def generate_all(self, segments: list[VideoSegment]) -> list[VideoSegment]:
        """Concurrently generate all segment videos.

        Updates each segment's ``status`` and ``video_path`` in-place.
        Exceptions from individual segments are captured so that one failure
        does not prevent other segments from completing.
        """
        tasks = [self._generate_one(seg) for seg in segments]
        await asyncio.gather(*tasks, return_exceptions=True)
        return segments

    async def _generate_one(self, segment: VideoSegment) -> None:
        async with self.semaphore:
            segment.status = SegmentStatus.GENERATING
            for attempt in range(self.max_retries):
                try:
                    result = await self.adapter.generate(
                        prompt=segment.visual_prompt,
                        duration=segment.duration_sec,
                        character_keywords=segment.character_keywords,
                        environment_keywords=segment.environment_keywords,
                        style_keywords=segment.style_keywords,
                    )
                    segment.video_path = result.video_path
                    segment.status = SegmentStatus.COMPLETED
                    return
                except Exception:
                    segment.retry_count += 1
                    if attempt == self.max_retries - 1:
                        segment.status = SegmentStatus.FAILED
                        raise
                    await asyncio.sleep(2**attempt)
