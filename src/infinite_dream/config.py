"""Configuration management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"  # "openai" | "anthropic"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class VideoAPIConfig:
    """Video generation API configuration."""

    provider: str = "kling"  # "kling" | "minimax" | "runway"
    api_key: str = ""
    base_url: str = ""
    max_concurrency: int = 3
    max_retries: int = 3
    timeout_seconds: int = 300


@dataclass
class StorageConfig:
    """File storage configuration."""

    backend: str = "local"  # "local" | "s3"
    local_root: str = "./output"
    s3_bucket: str = ""
    s3_prefix: str = "infinite-dream/"


@dataclass
class AudioConfig:
    """Audio processing configuration."""

    crossfade_duration_sec: float = 2.0
    bgm_duck_db: float = -12.0
    enable_bgm_shift: bool = True


@dataclass
class AppConfig:
    """Top-level application configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    video: VideoAPIConfig = field(default_factory=VideoAPIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    default_segment_duration_sec: float = 8.0
    max_segment_duration_sec: float = 15.0

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables."""
        return cls(
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "openai"),
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                api_key=os.getenv("LLM_API_KEY", ""),
                base_url=os.getenv("LLM_BASE_URL") or None,
            ),
            video=VideoAPIConfig(
                provider=os.getenv("VIDEO_PROVIDER", "kling"),
                api_key=os.getenv("VIDEO_API_KEY", ""),
                base_url=os.getenv("VIDEO_BASE_URL", ""),
                max_concurrency=int(os.getenv("VIDEO_MAX_CONCURRENCY", "3")),
            ),
            storage=StorageConfig(
                backend=os.getenv("STORAGE_BACKEND", "local"),
                local_root=os.getenv("STORAGE_LOCAL_ROOT", "./output"),
            ),
        )
