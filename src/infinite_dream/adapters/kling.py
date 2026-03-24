"""Kling AI video generation API adapter."""

from __future__ import annotations

import asyncio

import httpx

from infinite_dream.adapters.base import GenerationResult, TaskStatus, VideoAPIAdapter


class KlingError(Exception):
    """Raised on Kling API errors."""


class KlingAdapter(VideoAPIAdapter):
    """Adapter for the Kling AI video generation API (https://klingai.com).

    Uses ``httpx.AsyncClient`` for async HTTP calls and polls the task
    status endpoint until completion.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.klingai.com",
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

        payload: dict = {
            "prompt": prompt,
            "duration": duration,
        }
        if character_keywords:
            payload["character_keywords"] = character_keywords
        if environment_keywords:
            payload["environment_keywords"] = environment_keywords
        if style_keywords:
            payload["style_keywords"] = style_keywords
        if reference_image:
            payload["reference_image"] = reference_image

        resp = await client.post("/v1/videos/generations", json=payload)
        if resp.status_code != 200:
            raise KlingError(f"Kling create failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        task_id: str = data["data"]["task_id"]

        # Poll until completed
        for _ in range(self.max_poll_attempts):
            status = await self.check_status(task_id)
            if status.status == "completed":
                video_url: str = status.error or ""  # re-used field for URL in raw response
                # In production, download the video to a local path here.
                return GenerationResult(
                    task_id=task_id,
                    video_path=video_url,
                    duration_sec=duration,
                )
            if status.status == "failed":
                raise KlingError(f"Task {task_id} failed: {status.error}")
            await asyncio.sleep(self.poll_interval)

        raise KlingError(f"Task {task_id} timed out after {self.max_poll_attempts} polls")

    async def check_status(self, task_id: str) -> TaskStatus:
        """Query the task status endpoint."""
        client = self._get_client()
        resp = await client.get(f"/v1/videos/generations/{task_id}")
        if resp.status_code != 200:
            raise KlingError(f"Kling status check failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json().get("data", {})
        return TaskStatus(
            task_id=task_id,
            status=data.get("status", "pending"),
            progress=float(data.get("progress", 0.0)),
            error=data.get("video_url") or data.get("error"),
        )
