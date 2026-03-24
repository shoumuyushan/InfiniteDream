"""LLM adapter implementations — OpenAI and Mock."""

from __future__ import annotations

import json

from infinite_dream.adapters.base import LLMAdapter


class OpenAILLMAdapter(LLMAdapter):
    """OpenAI / OpenAI-compatible LLM adapter using the official SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client: object | None = None  # lazy-init

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            from openai import AsyncOpenAI  # noqa: WPS433

            kwargs: dict[str, object] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)  # type: ignore[arg-type]
        return self._client

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> str:
        client = self._get_client()
        kwargs: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        resp = await client.chat.completions.create(**kwargs)  # type: ignore[union-attr]
        return resp.choices[0].message.content or ""


# ── Mock responses for testing ────────────────────

_MOCK_CHARACTERS = json.dumps([
    {
        "name": "林晓",
        "description": "一位勇敢的年轻女考古学家，有着敏锐的观察力",
        "appearance_keywords": ["long black hair", "field jacket", "determined eyes", "leather boots"],
        "traits": ["brave", "curious", "intelligent"],
        "age_range": "25-30",
    },
    {
        "name": "赵远",
        "description": "经验丰富的探险队长，沉稳可靠",
        "appearance_keywords": ["short grey hair", "rugged face", "military vest", "compass necklace"],
        "traits": ["calm", "experienced", "protective"],
        "age_range": "40-50",
    },
    {
        "name": "小白",
        "description": "活泼的队伍向导，熟悉当地地形",
        "appearance_keywords": ["messy brown hair", "bright smile", "hiking gear", "bandana"],
        "traits": ["cheerful", "resourceful", "talkative"],
        "age_range": "20-25",
    },
])

_MOCK_SCENES = json.dumps([
    {
        "name": "古墓入口",
        "description": "隐藏在密林深处的古代墓穴入口，巨石雕刻着神秘符文",
        "environment_keywords": ["ancient ruins", "dense forest", "stone carvings", "moss-covered"],
        "time_of_day": "day",
        "mood": "mysterious",
    },
    {
        "name": "地下河",
        "description": "墓穴深处的地下暗河，水面反射着微弱的磷光",
        "environment_keywords": ["underground river", "phosphorescent glow", "stalactites", "dark cavern"],
        "time_of_day": "night",
        "mood": "tense",
    },
    {
        "name": "宝藏大厅",
        "description": "巨大的地下大厅，中央摆放着金色石棺，四周堆满古代宝物",
        "environment_keywords": ["golden sarcophagus", "treasure hall", "torch light", "ancient artifacts"],
        "time_of_day": "night",
        "mood": "awe",
    },
])

_MOCK_STYLE = json.dumps({
    "preset": "cinematic",
    "name": "Cinematic Adventure",
    "description": "An adventure-driven cinematic style with dramatic lighting and epic wide shots.",
    "visual_keywords": [
        "cinematic", "35mm film", "dramatic lighting",
        "wide establishing shots", "high contrast", "epic scale",
    ],
    "color_temperature": 5200,
    "saturation": 1.1,
    "contrast": 1.3,
    "grain": 0.15,
    "lighting_direction": "dramatic",
    "camera_motion": "dolly",
})

_MOCK_ENHANCED = json.dumps({
    "segments": [
        {
            "sequence": 1,
            "scene_name": "古墓入口",
            "content": "茂密的丛林中，林晓拨开最后一道藤蔓，古墓入口赫然出现。巨大的石门上刻满了神秘符文，在斑驳的阳光下泛着幽光。",
            "characters_present": ["林晓"],
            "camera_direction": "wide shot slowly pushing in",
            "estimated_duration_sec": 8,
            "mood": "mysterious",
        },
        {
            "sequence": 2,
            "scene_name": "古墓入口",
            "content": "赵远走上前，用手电筒照亮石门上的文字。「这些是商代的铭文，」他低声说，「这座墓比我们想象的还要古老。」",
            "characters_present": ["赵远", "林晓"],
            "camera_direction": "medium close-up",
            "estimated_duration_sec": 10,
            "mood": "serious",
        },
        {
            "sequence": 3,
            "scene_name": "地下河",
            "content": "三人沿着狭窄的通道深入墓穴，脚下的石板路逐渐被水流覆盖。地下河的水面上浮动着淡蓝色的磷光，照亮了洞穴中嶙峋的钟乳石。",
            "characters_present": ["林晓", "赵远", "小白"],
            "camera_direction": "tracking shot following the group",
            "estimated_duration_sec": 10,
            "mood": "tense",
        },
        {
            "sequence": 4,
            "scene_name": "宝藏大厅",
            "content": "穿过地下河后，他们来到了一个宏伟的大厅。金色的石棺静静地矗立在中央，四周的古代宝物在火把光芒下闪闪发光。林晓屏住呼吸，眼中满是震撼。",
            "characters_present": ["林晓", "赵远", "小白"],
            "camera_direction": "crane shot rising to reveal the hall",
            "estimated_duration_sec": 12,
            "mood": "awe",
        },
    ],
})


class MockLLMAdapter(LLMAdapter):
    """Mock LLM adapter for testing — returns predefined responses based on prompt keywords."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self._custom_responses = responses or {}

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        response_format: str | None = None,
    ) -> str:
        # Check custom responses first
        for keyword, response in self._custom_responses.items():
            if keyword in system_prompt or keyword in user_prompt:
                return response

        prompt_lower = system_prompt.lower()

        # Scene extraction (check before character — scene prompts also mention "character")
        if "scene" in prompt_lower and "extract" in prompt_lower:
            return _MOCK_SCENES

        # Character extraction
        if "character" in prompt_lower and "extract" in prompt_lower:
            return _MOCK_CHARACTERS

        # Style analysis
        if "style" in prompt_lower or "stylist" in prompt_lower:
            return _MOCK_STYLE

        # Script enhancement
        if "enhance" in prompt_lower or "screenwriter" in prompt_lower:
            return _MOCK_ENHANCED

        # Default: return a simple JSON object
        return json.dumps({"text": "Mock response", "status": "ok"})
