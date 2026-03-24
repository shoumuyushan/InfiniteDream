"""MiniMax / 海螺 video generation API adapter."""

from __future__ import annotations

import asyncio

import httpx

from infinite_dream.adapters.base import GenerationResult, TaskStatus, VideoAPIAdapter


class MiniMaxError(Exception):
    """Raised on MiniMax API errors."""


class MiniMaxAdapter(VideoAPIAdapter):
    """Adapter for the MiniMax video generation API (https://api.minimax.chat).

    Uses ``httpx.AsyncClient`` for async HTTP calls and polls the task
    status endpoint until completion.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.minimax.chat",
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
            "model": "video-01",
            "prompt": prompt,
        }
        if reference_image:
            payload["first_frame_image"] = reference_image

        resp = await client.post("/v1/video_generation", json=payload)
        if resp.status_code != 200:
            raise MiniMaxError(f"MiniMax create failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        task_id: str = data.get("task_id", "")
        if not task_id:
            raise MiniMaxError(f"MiniMax response missing task_id: {resp.text[:300]}")

        # Poll until completed
        for _ in range(self.max_poll_attempts):
            status = await self.check_status(task_id)
            if status.status == "completed":
                video_url: str = status.error or ""  # re-used field for URL
                return GenerationResult(
                    task_id=task_id,
                    video_path=video_url,
                    duration_sec=duration,
                )
            if status.status == "failed":
                raise MiniMaxError(f"Task {task_id} failed: {status.error}")
            await asyncio.sleep(self.poll_interval)

        raise MiniMaxError(f"Task {task_id} timed out after {self.max_poll_attempts} polls")

    async def check_status(self, task_id: str) -> TaskStatus:
        """Query the task status endpoint."""
        client = self._get_client()
        resp = await client.get(f"/v1/query/video_generation", params={"task_id": task_id})
        if resp.status_code != 200:
            raise MiniMaxError(f"MiniMax status check failed ({resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        status_str = data.get("status", "pending")

        # Map MiniMax status to our status
        status_map = {
            "Queueing": "pending",
            "Processing": "running",
            "Success": "completed",
            "Fail": "failed",
        }
        normalized = status_map.get(status_str, status_str)

        video_url = None
        file_id = data.get("file_id")
        if file_id:
            video_url = f"{self.base_url}/v1/files/retrieve?file_id={file_id}"

        return TaskStatus(
            task_id=task_id,
            status=normalized,
            progress=1.0 if normalized == "completed" else 0.5 if normalized == "running" else 0.0,
            error=video_url or data.get("base_resp", {}).get("status_msg"),
        )
