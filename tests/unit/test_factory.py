"""Test adapter factory and config persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinite_dream.adapters.anthropic_llm import AnthropicLLMAdapter
from infinite_dream.adapters.factory import create_llm_adapter, create_video_adapter
from infinite_dream.adapters.kling import KlingAdapter
from infinite_dream.adapters.llm import MockLLMAdapter, OpenAILLMAdapter
from infinite_dream.adapters.minimax import MiniMaxAdapter
from infinite_dream.adapters.mock_video import MockVideoAdapter
from infinite_dream.adapters.runway import RunwayAdapter
from infinite_dream.config import AppConfig, LLMConfig, VideoAPIConfig


# ── LLM adapter factory ──────────────────────────


def test_create_llm_adapter_no_key_returns_mock():
    """没有 API key 时返回 MockLLMAdapter。"""
    config = LLMConfig(api_key="")
    adapter = create_llm_adapter(config)
    assert isinstance(adapter, MockLLMAdapter)


def test_create_llm_adapter_openai():
    """OpenAI provider 返回 OpenAILLMAdapter。"""
    config = LLMConfig(provider="openai", api_key="sk-test")
    adapter = create_llm_adapter(config)
    assert isinstance(adapter, OpenAILLMAdapter)
    assert adapter.api_key == "sk-test"
    assert adapter.model == "gpt-4o"


def test_create_llm_adapter_anthropic():
    """Anthropic provider 返回 AnthropicLLMAdapter。"""
    config = LLMConfig(provider="anthropic", api_key="sk-ant-test", model="claude-sonnet-4-20250514")
    adapter = create_llm_adapter(config)
    assert isinstance(adapter, AnthropicLLMAdapter)
    assert adapter.api_key == "sk-ant-test"
    assert adapter.model == "claude-sonnet-4-20250514"


def test_create_llm_adapter_custom_provider_uses_openai():
    """custom provider 也使用 OpenAILLMAdapter（兼容 OpenAI 接口的代理网关）。"""
    config = LLMConfig(provider="custom", api_key="sk-custom", base_url="https://my-proxy.com/v1")
    adapter = create_llm_adapter(config)
    assert isinstance(adapter, OpenAILLMAdapter)
    assert adapter.base_url == "https://my-proxy.com/v1"


def test_create_llm_adapter_custom_base_url():
    """自定义 base_url 正确传递给 OpenAI adapter。"""
    config = LLMConfig(provider="openai", api_key="sk-test", base_url="https://proxy.example.com")
    adapter = create_llm_adapter(config)
    assert isinstance(adapter, OpenAILLMAdapter)
    assert adapter.base_url == "https://proxy.example.com"


def test_create_llm_adapter_anthropic_custom_base_url():
    """自定义 base_url 正确传递给 Anthropic adapter。"""
    config = LLMConfig(provider="anthropic", api_key="sk-ant", base_url="https://ant-proxy.example.com")
    adapter = create_llm_adapter(config)
    assert isinstance(adapter, AnthropicLLMAdapter)
    assert adapter.base_url == "https://ant-proxy.example.com"


# ── Video adapter factory ─────────────────────────


def test_create_video_adapter_no_key_returns_mock():
    """没有 API key 时返回 MockVideoAdapter。"""
    config = VideoAPIConfig(api_key="")
    adapter = create_video_adapter(config)
    assert isinstance(adapter, MockVideoAdapter)


def test_create_video_adapter_kling():
    """Kling provider 返回 KlingAdapter。"""
    config = VideoAPIConfig(provider="kling", api_key="kling-key")
    adapter = create_video_adapter(config)
    assert isinstance(adapter, KlingAdapter)
    assert adapter.api_key == "kling-key"
    assert adapter.base_url == "https://api.klingai.com"


def test_create_video_adapter_minimax():
    """MiniMax provider 返回 MiniMaxAdapter。"""
    config = VideoAPIConfig(provider="minimax", api_key="mm-key")
    adapter = create_video_adapter(config)
    assert isinstance(adapter, MiniMaxAdapter)
    assert adapter.api_key == "mm-key"
    assert adapter.base_url == "https://api.minimax.chat"


def test_create_video_adapter_runway():
    """Runway provider 返回 RunwayAdapter。"""
    config = VideoAPIConfig(provider="runway", api_key="rw-key")
    adapter = create_video_adapter(config)
    assert isinstance(adapter, RunwayAdapter)
    assert adapter.api_key == "rw-key"
    assert adapter.base_url == "https://api.dev.runwayml.com"


def test_create_video_adapter_custom_base_url():
    """自定义 base_url 正确传递。"""
    config = VideoAPIConfig(provider="kling", api_key="k", base_url="https://my-proxy.com")
    adapter = create_video_adapter(config)
    assert isinstance(adapter, KlingAdapter)
    assert adapter.base_url == "https://my-proxy.com"


def test_create_video_adapter_minimax_custom_base_url():
    """MiniMax 自定义 base_url 正确传递。"""
    config = VideoAPIConfig(provider="minimax", api_key="k", base_url="https://mm-proxy.com")
    adapter = create_video_adapter(config)
    assert isinstance(adapter, MiniMaxAdapter)
    assert adapter.base_url == "https://mm-proxy.com"


# ── Config persistence ────────────────────────────


def test_config_save_and_load(tmp_path: Path):
    """配置保存和加载正确。"""
    config_file = tmp_path / "config.json"

    original = AppConfig(
        llm=LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key="sk-ant-test-key",
            base_url="https://ant-proxy.com",
            timeout_seconds=60,
        ),
        video=VideoAPIConfig(
            provider="minimax",
            api_key="mm-key-123",
            base_url="https://mm-proxy.com",
            max_concurrency=5,
            timeout_seconds=600,
            poll_interval_seconds=10,
        ),
    )
    original.save(config_file=config_file)

    # Verify the file was created
    assert config_file.exists()

    # Load it back
    loaded = AppConfig.load(config_file=config_file)

    assert loaded.llm.provider == "anthropic"
    assert loaded.llm.model == "claude-sonnet-4-20250514"
    assert loaded.llm.api_key == "sk-ant-test-key"
    assert loaded.llm.base_url == "https://ant-proxy.com"
    assert loaded.llm.timeout_seconds == 60
    assert loaded.video.provider == "minimax"
    assert loaded.video.api_key == "mm-key-123"
    assert loaded.video.base_url == "https://mm-proxy.com"
    assert loaded.video.max_concurrency == 5
    assert loaded.video.timeout_seconds == 600
    assert loaded.video.poll_interval_seconds == 10


def test_config_save_creates_parent_dirs(tmp_path: Path):
    """save() 自动创建父目录。"""
    config_file = tmp_path / "deep" / "nested" / "config.json"
    config = AppConfig()
    config.save(config_file=config_file)
    assert config_file.exists()


def test_config_load_fallback_to_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """配置文件不存在时 fallback 到环境变量。"""
    config_file = tmp_path / "nonexistent.json"
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_API_KEY", "sk-from-env")
    monkeypatch.setenv("LLM_MODEL", "claude-3-opus")

    loaded = AppConfig.load(config_file=config_file)

    assert loaded.llm.provider == "anthropic"
    assert loaded.llm.api_key == "sk-from-env"
    assert loaded.llm.model == "claude-3-opus"


def test_config_load_fallback_on_corrupt_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """配置文件损坏时 fallback 到环境变量。"""
    config_file = tmp_path / "config.json"
    config_file.write_text("not valid json {{{")

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "sk-fallback")

    loaded = AppConfig.load(config_file=config_file)
    assert loaded.llm.provider == "openai"
    assert loaded.llm.api_key == "sk-fallback"


def test_config_save_load_roundtrip_defaults(tmp_path: Path):
    """默认配置的保存/加载 roundtrip。"""
    config_file = tmp_path / "config.json"
    original = AppConfig()
    original.save(config_file=config_file)
    loaded = AppConfig.load(config_file=config_file)

    assert loaded.llm.provider == original.llm.provider
    assert loaded.llm.model == original.llm.model
    assert loaded.video.provider == original.video.provider
    assert loaded.storage.backend == original.storage.backend
    assert loaded.audio.crossfade_duration_sec == original.audio.crossfade_duration_sec


def test_config_saved_json_is_valid(tmp_path: Path):
    """保存的 JSON 文件格式正确且可读。"""
    config_file = tmp_path / "config.json"
    config = AppConfig(
        llm=LLMConfig(provider="openai", api_key="sk-test"),
    )
    config.save(config_file=config_file)

    data = json.loads(config_file.read_text())
    assert "llm" in data
    assert "video" in data
    assert "storage" in data
    assert "audio" in data
    assert data["llm"]["provider"] == "openai"
    assert data["llm"]["api_key"] == "sk-test"


# ── New config field defaults ─────────────────────


def test_llm_config_timeout_default():
    """LLMConfig timeout_seconds 默认值。"""
    llm = LLMConfig()
    assert llm.timeout_seconds == 120


def test_video_config_poll_interval_default():
    """VideoAPIConfig poll_interval_seconds 默认值。"""
    video = VideoAPIConfig()
    assert video.poll_interval_seconds == 5
