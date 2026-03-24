"""Anthropic Claude LLM adapter."""

from __future__ import annotations

from infinite_dream.adapters.base import LLMAdapter


class AnthropicLLMAdapter(LLMAdapter):
    """Anthropic Claude adapter using the anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client: object | None = None  # lazy-init

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            from anthropic import AsyncAnthropic  # noqa: WPS433

            kwargs: dict[str, object] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncAnthropic(**kwargs)  # type: ignore[arg-type]
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
        message = await client.messages.create(  # type: ignore[union-attr]
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text  # type: ignore[union-attr]
