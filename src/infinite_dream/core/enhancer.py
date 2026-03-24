"""Script enhancer — LLM-powered script expansion and cinematography annotation."""

from __future__ import annotations

import json
from typing import Any

from infinite_dream.adapters.base import LLMAdapter
from infinite_dream.models.project import (
    Character,
    EnhancedScript,
    Scene,
    Script,
    ScriptSegment,
)


class ScriptEnhancer:
    """Enhance a raw script with expanded prose, dialogue, and camera directions."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def enhance(
        self,
        script: Script,
        characters: list[Character],
        scenes: list[Scene],
        level: str = "moderate",
    ) -> EnhancedScript:
        """Enhance the script, returning an EnhancedScript with segments."""
        char_info = "\n".join(
            f"- {c.name}: {c.description} (traits: {', '.join(c.traits)})"
            for c in characters
        ) or "N/A"

        scene_info = "\n".join(
            f"- {s.name}: {s.description} (mood: {s.mood}, time: {s.time_of_day})"
            for s in scenes
        ) or "N/A"

        level_guidance = self._level_guidance(level)

        system_prompt = (
            "You are a professional screenwriter and cinematographer. "
            "Enhance the script below by expanding descriptions, adding vivid dialogue, "
            "and annotating camera directions for each segment.\n\n"
            f"Enhancement level: {level} — {level_guidance}\n\n"
            f"Characters:\n{char_info}\n\n"
            f"Scenes:\n{scene_info}\n\n"
            "Return ONLY a JSON object with these keys:\n"
            '  "segments": array of objects, each with:\n'
            '    "sequence": integer starting from 1,\n'
            '    "scene_name": name of the scene this segment belongs to,\n'
            '    "content": enhanced text content for this segment,\n'
            '    "characters_present": list of character names,\n'
            '    "camera_direction": camera instruction (e.g. "close-up", "wide shot", "pan left"),\n'
            '    "estimated_duration_sec": integer seconds (5-15),\n'
            '    "mood": emotional tone of this segment\n'
            "Do NOT include any markdown formatting or code fences."
        )

        user_prompt = f"Script ({script.language}):\n\n{script.content}"

        response = await self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            response_format="json",
        )

        data = self._parse_json_object(response)
        return self._to_enhanced_script(data, script, characters, scenes, level)

    # ── Internal helpers ─────────────────────────

    @staticmethod
    def _level_guidance(level: str) -> str:
        guidance = {
            "light": (
                "Minimal changes. Keep the original structure, only polish language "
                "and add basic camera directions."
            ),
            "moderate": (
                "Moderate expansion. Flesh out descriptions, add natural dialogue, "
                "and annotate with varied camera angles. Keep the story faithful."
            ),
            "heavy": (
                "Extensive rewrite. Dramatically expand scenes with rich sensory detail, "
                "create multi-turn dialogue, add subtext, and use advanced cinematography "
                "(dolly zooms, match cuts, etc.)."
            ),
        }
        return guidance.get(level, guidance["moderate"])

    def _to_enhanced_script(
        self,
        data: dict[str, Any],
        script: Script,
        characters: list[Character],
        scenes: list[Scene],
        level: str,
    ) -> EnhancedScript:
        segments_data = data.get("segments", [])
        segments: list[ScriptSegment] = []

        # Build lookup maps
        char_by_name = {c.name: c for c in characters}
        scene_by_name = {s.name: s for s in scenes}

        total_duration = 0

        for seg_data in segments_data:
            # Resolve character IDs
            char_names = seg_data.get("characters_present", [])
            char_ids = [
                char_by_name[n].id for n in char_names if n in char_by_name
            ]

            # Resolve scene ID
            scene_name = seg_data.get("scene_name", "")
            scene_id = scene_by_name[scene_name].id if scene_name in scene_by_name else ""

            duration = int(seg_data.get("estimated_duration_sec", 8))
            total_duration += duration

            segments.append(
                ScriptSegment(
                    sequence=int(seg_data.get("sequence", len(segments) + 1)),
                    scene_id=scene_id,
                    content=seg_data.get("content", ""),
                    characters_present=char_ids,
                    camera_direction=seg_data.get("camera_direction", ""),
                    estimated_duration_sec=duration,
                    mood=seg_data.get("mood", "neutral"),
                )
            )

        return EnhancedScript(
            script_id=script.id,
            segments=segments,
            total_duration_sec=total_duration,
            enhancement_level=level,
        )

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed  # type: ignore[no-any-return]
        raise ValueError(f"Expected JSON object, got {type(parsed)}")
