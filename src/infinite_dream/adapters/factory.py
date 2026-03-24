"""Adapter factory — create adapters from config."""

from __future__ import annotations

from infinite_dream.adapters.base import LLMAdapter, VideoAPIAdapter
from infinite_dream.config import LLMConfig, VideoAPIConfig


def create_llm_adapter(config: LLMConfig) -> LLMAdapter:
    """Create LLM adapter based on config.

    Returns a mock adapter when no API key is configured, otherwise
    selects the real adapter based on ``config.provider``.
    """
    if not config.api_key:
        from infinite_dream.adapters.llm import MockLLMAdapter

        return MockLLMAdapter()

    if config.provider == "anthropic":
        from infinite_dream.adapters.anthropic_llm import AnthropicLLMAdapter

        return AnthropicLLMAdapter(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
        )
    else:  # openai or custom
        from infinite_dream.adapters.llm import OpenAILLMAdapter

        return OpenAILLMAdapter(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
        )


def create_video_adapter(config: VideoAPIConfig) -> VideoAPIAdapter:
    """Create video adapter based on config.

    Returns a mock adapter when no API key is configured, otherwise
    selects the real adapter based on ``config.provider``.
    """
    if not config.api_key:
        from infinite_dream.adapters.mock_video import MockVideoAdapter

        return MockVideoAdapter()

    if config.provider == "minimax":
        from infinite_dream.adapters.minimax import MiniMaxAdapter

        return MiniMaxAdapter(
            api_key=config.api_key,
            base_url=config.base_url or "https://api.minimax.chat",
        )
    elif config.provider == "runway":
        from infinite_dream.adapters.runway import RunwayAdapter

        return RunwayAdapter(
            api_key=config.api_key,
            base_url=config.base_url or "https://api.dev.runwayml.com",
        )
    else:  # kling (default)
        from infinite_dream.adapters.kling import KlingAdapter

        return KlingAdapter(
            api_key=config.api_key,
            base_url=config.base_url or "https://api.klingai.com",
        )
