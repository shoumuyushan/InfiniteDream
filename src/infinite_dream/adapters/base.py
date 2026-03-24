"""Abstract base classes for external service adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationResult:
    """Result from a video generation API call."""

    task_id: str
    video_path: str
    duration_sec: float
    width: int = 1280
    height: int = 720


class TaskStatus:
    """Status of an async generation task."""

    def __init__(self, task_id: str, status: str, progress: float = 0.0, error: str | None = None):
        self.task_id = task_id
        self.status = status  # "pending" | "running" | "completed" | "failed"
        self.progress = progress
        self.error = error

    @property
    def is_done(self) -> bool:
        return self.status in ("completed", "failed")


class VideoAPIAdapter(ABC):
    """Abstract interface for video generation APIs."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration: float,
        character_keywords: list[str] | None = None,
        environment_keywords: list[str] | None = None,
        style_keywords: list[str] | None = None,
        reference_image: str | None = None,
    ) -> GenerationResult:
        """Submit a video generation request and return result."""
        ...

    @abstractmethod
    async def check_status(self, task_id: str) -> TaskStatus:
        """Check the status of an async generation task."""
        ...


class LLMAdapter(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: str | None = None,  # "json" | None
    ) -> str:
        """Send a completion request and return the response text."""
        ...


class MusicAdapter(ABC):
    """Abstract interface for music/audio generation APIs."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration_sec: float,
        style: str | None = None,
    ) -> str:
        """Generate music and return the audio file path."""
        ...
