"""Runway Gen-3/4 video generation API adapter."""

from __future__ import annotations

import asyncio

import httpx

from infinite_dream.adapters.base import GenerationResult, TaskStatus, VideoAPIAdapter


class RunwayError(Exception):
    """Raised on Runway API errors."""


class RunwayAdapter(VideoAPIAdapter):
    """Adapter for the Runway video generation API (https://api.dev.runwayml.com).

    Uses ``httpx.AsyncClient`` for async HTTP calls and polls the task
    status endpoint until completion.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.dev.runwayml.com",
        poll_interval: float = 5.0,
        max_poll_attempts: int = 120,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts
        self._client: httpx.AsyncClient | None = None

    # ── HTTP client lifecycle ─────────────────────

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Runway-Version": "2024-11-06",
                },
                timeout=httpx.Timeout(30.0, read=120.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── VideoAPIAdapter interface ─────────────────

    async def generate(
        self,
        prompt: str,
        duration: float,
        character_keywords: list[str] | None = None,
        environment_keywords: list[str] | None = None,
        style_keywords: list[str] | None = None,
        reference_image: str | None = None,
    ) -> GenerationResult:
        """Submit a generation task and poll until done."""
        client = self._get_client()

        # Map duration to Runway's supported durations (5 or 10 seconds)
        runway_duration = 5 if duration <= 7.5 else 10

        payload: dict = {
            "model": "gen4_turbo",
            "promptText": prompt,
            "duration": runway_duration,
            "ratio": "1280:768",
        }
        if reference_image:
            payload["promptImage"] = reference_image

        resp = await client.post("/v1/image_to_video", json=payload)
        if resp.status_code not in (200, 201):
            raise RunwayError(f"Runway create failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        task_id: str = data.get("id", "")
        if not task_id:
            raise RunwayError(f"Runway response missing task id: {resp.text[:300]}")

        # Poll until completed
        for _ in range(self.max_poll_attempts):
            status = await self.check_status(task_id)
            if status.status == "completed":
                video_url: str = status.error or ""  # re-used field for URL
                return GenerationResult(
                    task_id=task_id,
                    video_path=video_url,
                    duration_sec=float(runway_duration),
                )
            if status.status == "failed":
                raise RunwayError(f"Task {task_id} failed: {status.error}")
            await asyncio.sleep(self.poll_interval)

        raise RunwayError(f"Task {task_id} timed out after {self.max_poll_attempts} polls")

    async def check_status(self, task_id: str) -> TaskStatus:
        """Query the task status endpoint."""
        client = self._get_client()
        resp = await client.get(f"/v1/tasks/{task_id}")
        if resp.status_code != 200:
            raise RunwayError(f"Runway status check failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        status_str = data.get("status", "PENDING")

        # Map Runway status to our status
        status_map = {
            "PENDING": "pending",
            "RUNNING": "running",
            "THROTTLED": "pending",
            "SUCCEEDED": "completed",
            "FAILED": "failed",
            "CANCELLED": "failed",
        }
        normalized = status_map.get(status_str, status_str.lower())

        # Extract video URL from output if completed
        video_url = None
        output = data.get("output")
        if isinstance(output, list) and output:
            video_url = output[0]
        elif isinstance(output, str):
            video_url = output

        progress = data.get("progress", 0.0)

        return TaskStatus(
            task_id=task_id,
            status=normalized,
            progress=float(progress) if progress else (1.0 if normalized == "completed" else 0.0),
            error=video_url or data.get("failure") or data.get("failureCode"),
        )
