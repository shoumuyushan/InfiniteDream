"""Test adapter base classes and contracts."""

import pytest

from infinite_dream.adapters.base import (
    GenerationResult,
    LLMAdapter,
    MusicAdapter,
    TaskStatus,
    VideoAPIAdapter,
)


# ── TaskStatus ────────────────────────────────────


def test_task_status_pending():
    """Pending task is not done."""
    ts = TaskStatus(task_id="t1", status="pending")
    assert ts.is_done is False
    assert ts.progress == 0.0
    assert ts.error is None


def test_task_status_running():
    """Running task is not done."""
    ts = TaskStatus(task_id="t2", status="running", progress=0.5)
    assert ts.is_done is False
    assert ts.progress == 0.5


def test_task_status_completed():
    """Completed task is done."""
    ts = TaskStatus(task_id="t3", status="completed", progress=1.0)
    assert ts.is_done is True


def test_task_status_failed():
    """Failed task is done with error."""
    ts = TaskStatus(task_id="t4", status="failed", error="timeout")
    assert ts.is_done is True
    assert ts.error == "timeout"


# ── GenerationResult ──────────────────────────────


def test_generation_result():
    """GenerationResult holds all fields with defaults."""
    gr = GenerationResult(task_id="g1", video_path="/out/v.mp4", duration_sec=8.0)
    assert gr.task_id == "g1"
    assert gr.video_path == "/out/v.mp4"
    assert gr.duration_sec == 8.0
    assert gr.width == 1280
    assert gr.height == 720


def test_generation_result_custom_resolution():
    """GenerationResult can store custom resolution."""
    gr = GenerationResult(task_id="g2", video_path="/out.mp4", duration_sec=5.0, width=1920, height=1080)
    assert gr.width == 1920
    assert gr.height == 1080


# ── Concrete adapter implementations for contract testing ──


class FakeVideoAdapter(VideoAPIAdapter):
    """Minimal concrete VideoAPIAdapter for testing the interface."""

    async def generate(
        self,
        prompt: str,
        duration: float,
        character_keywords: list[str] | None = None,
        environment_keywords: list[str] | None = None,
        style_keywords: list[str] | None = None,
        reference_image: str | None = None,
    ) -> GenerationResult:
        return GenerationResult(
            task_id="fake-task",
            video_path="/tmp/fake.mp4",
            duration_sec=duration,
        )

    async def check_status(self, task_id: str) -> TaskStatus:
        return TaskStatus(task_id=task_id, status="completed", progress=1.0)


class FakeLLMAdapter(LLMAdapter):
    """Minimal concrete LLMAdapter for testing the interface."""

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> str:
        return f"Response to: {user_prompt[:50]}"


class FakeMusicAdapter(MusicAdapter):
    """Minimal concrete MusicAdapter for testing the interface."""

    async def generate(
        self,
        prompt: str,
        duration_sec: float,
        style: str | None = None,
    ) -> str:
        return "/tmp/fake_music.mp3"


# ── VideoAPIAdapter contract ──────────────────────


@pytest.mark.asyncio
async def test_video_adapter_generate():
    """VideoAPIAdapter.generate() returns GenerationResult."""
    adapter = FakeVideoAdapter()
    result = await adapter.generate(prompt="A bamboo forest at night", duration=8.0)
    assert isinstance(result, GenerationResult)
    assert result.task_id == "fake-task"
    assert result.duration_sec == 8.0


@pytest.mark.asyncio
async def test_video_adapter_check_status():
    """VideoAPIAdapter.check_status() returns TaskStatus."""
    adapter = FakeVideoAdapter()
    status = await adapter.check_status("fake-task")
    assert isinstance(status, TaskStatus)
    assert status.is_done is True
    assert status.status == "completed"


# ── LLMAdapter contract ──────────────────────────


@pytest.mark.asyncio
async def test_llm_adapter_complete():
    """LLMAdapter.complete() returns a string."""
    adapter = FakeLLMAdapter()
    result = await adapter.complete(
        system_prompt="You are a helpful assistant.",
        user_prompt="Describe a bamboo forest.",
    )
    assert isinstance(result, str)
    assert "Describe a bamboo forest" in result


# ── MusicAdapter contract ─────────────────────────


@pytest.mark.asyncio
async def test_music_adapter_generate():
    """MusicAdapter.generate() returns a file path."""
    adapter = FakeMusicAdapter()
    path = await adapter.generate(prompt="Peaceful Chinese flute", duration_sec=30.0)
    assert isinstance(path, str)
    assert path.endswith(".mp3")


# ── Abstract classes cannot be instantiated ───────


def test_video_adapter_is_abstract():
    """VideoAPIAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        VideoAPIAdapter()  # type: ignore[abstract]


def test_llm_adapter_is_abstract():
    """LLMAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMAdapter()  # type: ignore[abstract]


def test_music_adapter_is_abstract():
    """MusicAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        MusicAdapter()  # type: ignore[abstract]
