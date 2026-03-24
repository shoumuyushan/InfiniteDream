"""Configuration management."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = Path.home() / ".infinite-dream" / "config.json"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"  # "openai" | "anthropic" | "custom"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 120


@dataclass
class VideoAPIConfig:
    """Video generation API configuration."""

    provider: str = "kling"  # "kling" | "minimax" | "runway"
    api_key: str = ""
    base_url: str = ""
    max_concurrency: int = 3
    max_retries: int = 3
    timeout_seconds: int = 300
    poll_interval_seconds: int = 5


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
                timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
            ),
            video=VideoAPIConfig(
                provider=os.getenv("VIDEO_PROVIDER", "kling"),
                api_key=os.getenv("VIDEO_API_KEY", ""),
                base_url=os.getenv("VIDEO_BASE_URL", ""),
                max_concurrency=int(os.getenv("VIDEO_MAX_CONCURRENCY", "3")),
                timeout_seconds=int(os.getenv("VIDEO_TIMEOUT_SECONDS", "300")),
                poll_interval_seconds=int(os.getenv("VIDEO_POLL_INTERVAL_SECONDS", "5")),
            ),
            storage=StorageConfig(
                backend=os.getenv("STORAGE_BACKEND", "local"),
                local_root=os.getenv("STORAGE_LOCAL_ROOT", "./output"),
            ),
        )

    def save(self, config_file: Path | None = None) -> None:
        """Save config to disk."""
        path = config_file or CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "api_key": self.llm.api_key,
                "base_url": self.llm.base_url or "",
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
                "timeout_seconds": self.llm.timeout_seconds,
            },
            "video": {
                "provider": self.video.provider,
                "api_key": self.video.api_key,
                "base_url": self.video.base_url,
                "max_concurrency": self.video.max_concurrency,
                "max_retries": self.video.max_retries,
                "timeout_seconds": self.video.timeout_seconds,
                "poll_interval_seconds": self.video.poll_interval_seconds,
            },
            "storage": {
                "backend": self.storage.backend,
                "local_root": self.storage.local_root,
            },
            "audio": {
                "crossfade_duration_sec": self.audio.crossfade_duration_sec,
                "bgm_duck_db": self.audio.bgm_duck_db,
                "enable_bgm_shift": self.audio.enable_bgm_shift,
            },
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, config_file: Path | None = None) -> AppConfig:
        """Load config from disk, falling back to env vars, then defaults."""
        path = config_file or CONFIG_FILE
        if path.exists():
            try:
                data = json.loads(path.read_text())
                llm_data = {k: v for k, v in data.get("llm", {}).items() if v != ""}
                video_data = {k: v for k, v in data.get("video", {}).items() if v != ""}
                storage_data = {k: v for k, v in data.get("storage", {}).items() if v != ""}
                audio_data = {k: v for k, v in data.get("audio", {}).items() if v != ""}

                # Handle base_url: None is valid for LLM, empty string should become None
                if "base_url" not in llm_data:
                    llm_data["base_url"] = None

                return cls(
                    llm=LLMConfig(**llm_data),
                    video=VideoAPIConfig(**video_data),
                    storage=StorageConfig(**storage_data),
                    audio=AudioConfig(**audio_data),
                )
            except Exception:
                pass
        return cls.from_env()
