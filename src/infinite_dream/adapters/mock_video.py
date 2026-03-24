"""Mock video adapter for testing — no real API calls."""

from __future__ import annotations

from pathlib import Path

from infinite_dream.adapters.base import GenerationResult, TaskStatus, VideoAPIAdapter


class MockVideoAdapter(VideoAPIAdapter):
    """Drop-in mock that creates empty placeholder files instead of calling an API."""

    def __init__(self, output_dir: str = "/tmp") -> None:
        self.output_dir = output_dir
        self.call_count = 0

    async def generate(
        self,
        prompt: str,
        duration: float,
        character_keywords: list[str] | None = None,
        environment_keywords: list[str] | None = None,
        style_keywords: list[str] | None = None,
        reference_image: str | None = None,
    ) -> GenerationResult:
        self.call_count += 1
        path = f"{self.output_dir}/mock_segment_{self.call_count}.mp4"
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).touch()
        return GenerationResult(
            task_id=f"mock-{self.call_count}",
            video_path=path,
            duration_sec=duration,
        )

    async def check_status(self, task_id: str) -> TaskStatus:
        return TaskStatus(
            task_id=task_id,
            status="completed",
            progress=1.0,
        )
