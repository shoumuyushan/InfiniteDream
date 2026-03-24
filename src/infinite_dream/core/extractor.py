"""Character and scene extractors — LLM-powered."""

from __future__ import annotations

import json
from typing import Any

from infinite_dream.adapters.base import LLMAdapter
from infinite_dream.models.project import Character, Scene, Script


class CharacterExtractor:
    """Use an LLM to extract characters from a script."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def extract(self, script: Script) -> list[Character]:
        system_prompt = (
            "You are a professional screenplay analyst. "
            "Extract all named characters from the script below. "
            "Return ONLY a JSON array of objects with the following keys: "
            '"name", "description", "appearance_keywords" (list of strings), '
            '"traits" (list of strings), "age_range" (string like "20-30").\n'
            "Do NOT include any markdown formatting or code fences."
        )

        user_prompt = f"Script ({script.language}):\n\n{script.content}"

        response = await self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            response_format="json",
        )

        characters_data = self._parse_json_array(response)
        return [self._to_character(item, script.id) for item in characters_data]

    @staticmethod
    def _to_character(data: dict[str, Any], script_id: str) -> Character:
        return Character(
            script_id=script_id,
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            appearance_keywords=data.get("appearance_keywords", []),
            traits=data.get("traits", []),
            age_range=data.get("age_range", ""),
        )

    @staticmethod
    def _parse_json_array(text: str) -> list[dict[str, Any]]:
        """Robustly parse a JSON array from LLM output."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        parsed = json.loads(text)
        if isinstance(parsed, dict):
            # Some LLMs wrap in {"characters": [...]}
            for key in ("characters", "data", "result", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]  # type: ignore[no-any-return]
            return [parsed]
        if isinstance(parsed, list):
            return parsed  # type: ignore[no-any-return]
        raise ValueError(f"Expected JSON array, got {type(parsed)}")


class SceneExtractor:
    """Use an LLM to extract scenes from a script."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def extract(self, script: Script, characters: list[Character]) -> list[Scene]:
        character_names = ", ".join(c.name for c in characters) or "N/A"

        system_prompt = (
            "You are a professional screenplay analyst. "
            "Extract all distinct scenes/locations from the script below. "
            "Known characters: " + character_names + ". "
            "Return ONLY a JSON array of objects with the following keys: "
            '"name", "description", "environment_keywords" (list of strings), '
            '"time_of_day" (one of "dawn","day","dusk","night"), '
            '"mood" (string describing the emotional tone).\n'
            "Do NOT include any markdown formatting or code fences."
        )

        user_prompt = f"Script ({script.language}):\n\n{script.content}"

        response = await self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            response_format="json",
        )

        scenes_data = self._parse_json_array(response)
        return [self._to_scene(item, script.id) for item in scenes_data]

    @staticmethod
    def _to_scene(data: dict[str, Any], script_id: str) -> Scene:
        return Scene(
            script_id=script_id,
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            environment_keywords=data.get("environment_keywords", []),
            time_of_day=data.get("time_of_day", "day"),
            mood=data.get("mood", "neutral"),
        )

    @staticmethod
    def _parse_json_array(text: str) -> list[dict[str, Any]]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for key in ("scenes", "data", "result", "items"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]  # type: ignore[no-any-return]
            return [parsed]
        if isinstance(parsed, list):
            return parsed  # type: ignore[no-any-return]
        raise ValueError(f"Expected JSON array, got {type(parsed)}")
