"""Test configuration management."""

from infinite_dream.config import AppConfig, AudioConfig, LLMConfig, StorageConfig, VideoAPIConfig


def test_default_config():
    """AppConfig 默认值合理。"""
    cfg = AppConfig()
    # Top-level defaults
    assert cfg.default_segment_duration_sec == 8.0
    assert cfg.max_segment_duration_sec == 15.0
    # Sub-configs are created
    assert isinstance(cfg.llm, LLMConfig)
    assert isinstance(cfg.video, VideoAPIConfig)
    assert isinstance(cfg.storage, StorageConfig)
    assert isinstance(cfg.audio, AudioConfig)


def test_config_from_env(monkeypatch):
    """AppConfig.from_env() 读取环境变量。"""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-3-opus")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom.api.com")
    monkeypatch.setenv("VIDEO_PROVIDER", "minimax")
    monkeypatch.setenv("VIDEO_API_KEY", "video-key-123")
    monkeypatch.setenv("VIDEO_BASE_URL", "https://video.api.com")
    monkeypatch.setenv("VIDEO_MAX_CONCURRENCY", "5")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", "/data/output")

    cfg = AppConfig.from_env()

    assert cfg.llm.provider == "anthropic"
    assert cfg.llm.model == "claude-3-opus"
    assert cfg.llm.api_key == "sk-test-key"
    assert cfg.llm.base_url == "https://custom.api.com"
    assert cfg.video.provider == "minimax"
    assert cfg.video.api_key == "video-key-123"
    assert cfg.video.base_url == "https://video.api.com"
    assert cfg.video.max_concurrency == 5
    assert cfg.storage.backend == "s3"
    assert cfg.storage.local_root == "/data/output"


def test_config_from_env_defaults(monkeypatch):
    """AppConfig.from_env() 环境变量未设置时使用默认值。"""
    # Clear relevant env vars to ensure defaults are used
    for var in [
        "LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL",
        "VIDEO_PROVIDER", "VIDEO_API_KEY", "VIDEO_BASE_URL", "VIDEO_MAX_CONCURRENCY",
        "STORAGE_BACKEND", "STORAGE_LOCAL_ROOT",
    ]:
        monkeypatch.delenv(var, raising=False)

    cfg = AppConfig.from_env()

    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.api_key == ""
    assert cfg.llm.base_url is None
    assert cfg.video.provider == "kling"
    assert cfg.video.max_concurrency == 3
    assert cfg.storage.backend == "local"
    assert cfg.storage.local_root == "./output"


def test_llm_config_defaults():
    """LLMConfig 默认值。"""
    llm = LLMConfig()
    assert llm.provider == "openai"
    assert llm.model == "gpt-4o"
    assert llm.api_key == ""
    assert llm.base_url is None
    assert llm.max_tokens == 4096
    assert llm.temperature == 0.7


def test_video_config_defaults():
    """VideoAPIConfig 默认值。"""
    video = VideoAPIConfig()
    assert video.provider == "kling"
    assert video.api_key == ""
    assert video.base_url == ""
    assert video.max_concurrency == 3
    assert video.max_retries == 3
    assert video.timeout_seconds == 300
