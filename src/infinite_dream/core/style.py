"""Style analyzer — LLM-powered style detection and preset management."""

from __future__ import annotations

import json
from typing import Any

from infinite_dream.adapters.base import LLMAdapter
from infinite_dream.models.project import Script, Style, StylePreset


# ── Preset definitions ────────────────────────────

_PRESET_STYLES: dict[StylePreset, Style] = {
    StylePreset.CINEMATIC: Style(
        name="Cinematic",
        preset=StylePreset.CINEMATIC,
        description="Classic cinema look with rich contrast and naturalistic lighting.",
        visual_keywords=[
            "cinematic",
            "35mm film",
            "shallow depth of field",
            "natural lighting",
            "high contrast",
            "anamorphic lens flare",
            "film grain",
            "wide aspect ratio",
        ],
        color_temperature=5200.0,
        saturation=1.1,
        contrast=1.3,
        grain=0.2,
        lighting_direction="dramatic",
        camera_motion="dolly",
        is_preset=True,
    ),
    StylePreset.SWEET_ROMANCE: Style(
        name="Sweet Romance",
        preset=StylePreset.SWEET_ROMANCE,
        description="Warm, dreamy aesthetic with soft tones perfect for love stories.",
        visual_keywords=[
            "soft warm tones",
            "dreamy bokeh",
            "golden hour lighting",
            "pastel colors",
            "soft focus",
            "romantic atmosphere",
            "lens halo",
            "gentle color grading",
        ],
        color_temperature=6500.0,
        saturation=0.9,
        contrast=0.8,
        grain=0.05,
        lighting_direction="soft",
        camera_motion="dolly",
        is_preset=True,
    ),
    StylePreset.XIANXIA: Style(
        name="Xianxia / Chinese Fantasy",
        preset=StylePreset.XIANXIA,
        description="Ethereal Chinese fantasy aesthetic with ink-painting influences.",
        visual_keywords=[
            "Chinese ink painting",
            "ethereal mist",
            "flowing robes",
            "mystical mountains",
            "floating particles",
            "jade green tones",
            "silk textures",
            "celestial glow",
            "ancient architecture",
        ],
        color_temperature=5000.0,
        saturation=0.85,
        contrast=1.1,
        grain=0.0,
        lighting_direction="soft",
        camera_motion="crane",
        is_preset=True,
    ),
    StylePreset.CYBERPUNK: Style(
        name="Cyberpunk",
        preset=StylePreset.CYBERPUNK,
        description="Neon-drenched futuristic dystopia with high-tech visuals.",
        visual_keywords=[
            "neon lights",
            "cyberpunk cityscape",
            "holographic displays",
            "rain-slicked streets",
            "futuristic technology",
            "dark alleyways",
            "purple and cyan color palette",
            "volumetric fog",
            "LED signage",
        ],
        color_temperature=4000.0,
        saturation=1.4,
        contrast=1.5,
        grain=0.1,
        lighting_direction="neon",
        camera_motion="handheld",
        is_preset=True,
    ),
    StylePreset.WAR: Style(
        name="War / Military",
        preset=StylePreset.WAR,
        description="Gritty, desaturated war aesthetic with documentary-like realism.",
        visual_keywords=[
            "desaturated colors",
            "gritty texture",
            "smoke and dust",
            "handheld camera",
            "war-torn environment",
            "muted earth tones",
            "harsh shadows",
            "debris particles",
        ],
        color_temperature=4800.0,
        saturation=0.6,
        contrast=1.4,
        grain=0.4,
        lighting_direction="dramatic",
        camera_motion="handheld",
        is_preset=True,
    ),
    StylePreset.ANIME: Style(
        name="Anime / Animation",
        preset=StylePreset.ANIME,
        description="Japanese animation style with vibrant colors and clean lines.",
        visual_keywords=[
            "anime style",
            "cel shading",
            "vibrant colors",
            "clean outlines",
            "expressive characters",
            "dynamic action lines",
            "sakura petals",
            "vivid sky gradient",
        ],
        color_temperature=5500.0,
        saturation=1.3,
        contrast=1.2,
        grain=0.0,
        lighting_direction="natural",
        camera_motion="static",
        is_preset=True,
    ),
    StylePreset.RETRO_FILM: Style(
        name="Retro Film",
        preset=StylePreset.RETRO_FILM,
        description="Vintage film look with heavy grain, faded colors, and warm tint.",
        visual_keywords=[
            "vintage film",
            "Kodak Portra",
            "faded colors",
            "light leaks",
            "heavy grain",
            "vignette",
            "warm color cast",
            "scratched film texture",
            "4:3 aspect ratio",
        ],
        color_temperature=6000.0,
        saturation=0.7,
        contrast=0.9,
        grain=0.6,
        lighting_direction="natural",
        camera_motion="static",
        is_preset=True,
    ),
    StylePreset.DOCUMENTARY: Style(
        name="Documentary",
        preset=StylePreset.DOCUMENTARY,
        description="Clean, realistic documentary style emphasising clarity and authenticity.",
        visual_keywords=[
            "documentary style",
            "natural lighting",
            "neutral color grading",
            "interview framing",
            "shallow depth of field",
            "eye-level camera",
            "authentic textures",
            "steady cam",
        ],
        color_temperature=5500.0,
        saturation=1.0,
        contrast=1.0,
        grain=0.1,
        lighting_direction="natural",
        camera_motion="handheld",
        is_preset=True,
    ),
}


class StyleAnalyzer:
    """Analyze a script's style and return a recommended Style."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    async def analyze(self, script: Script) -> Style:
        """Use LLM to determine the best style for a script."""
        preset_names = ", ".join(p.value for p in StylePreset if p != StylePreset.CUSTOM)

        system_prompt = (
            "You are a professional film director and visual stylist. "
            "Analyze the script below and recommend a visual style.\n"
            f"Available presets: {preset_names}\n"
            "Return ONLY a JSON object with these keys:\n"
            '  "preset": one of the preset names above, or "custom" if none fit,\n'
            '  "name": a short style name,\n'
            '  "description": why this style fits the script,\n'
            '  "visual_keywords": list of 5-8 visual keywords,\n'
            '  "color_temperature": number 2000-10000,\n'
            '  "saturation": number 0.0-2.0,\n'
            '  "contrast": number 0.0-2.0,\n'
            '  "grain": number 0.0-1.0,\n'
            '  "lighting_direction": "natural"|"dramatic"|"soft"|"neon",\n'
            '  "camera_motion": "static"|"handheld"|"dolly"|"crane"\n'
            "Do NOT include any markdown formatting or code fences."
        )

        user_prompt = f"Script ({script.language}):\n\n{script.content}"

        response = await self.llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            response_format="json",
        )

        data = self._parse_json_object(response)
        return self._to_style(data)

    @staticmethod
    def get_preset(preset: StylePreset) -> Style:
        """Return a built-in preset style."""
        if preset == StylePreset.CUSTOM:
            return Style(
                name="Custom",
                preset=StylePreset.CUSTOM,
                description="User-defined custom style.",
                is_preset=False,
            )
        style = _PRESET_STYLES.get(preset)
        if style is None:
            raise ValueError(f"Unknown preset: {preset}")
        # Return a copy so callers can't mutate the global
        return Style(
            name=style.name,
            preset=style.preset,
            description=style.description,
            visual_keywords=list(style.visual_keywords),
            color_temperature=style.color_temperature,
            saturation=style.saturation,
            contrast=style.contrast,
            grain=style.grain,
            lighting_direction=style.lighting_direction,
            camera_motion=style.camera_motion,
            reference_images=list(style.reference_images),
            is_preset=style.is_preset,
        )

    # ── Internal helpers ─────────────────────────

    def _to_style(self, data: dict[str, Any]) -> Style:
        preset_str = data.get("preset", "custom")
        try:
            preset = StylePreset(preset_str)
        except ValueError:
            preset = StylePreset.CUSTOM

        # If it matches a known preset, start from that and overlay LLM suggestions
        if preset != StylePreset.CUSTOM and preset in _PRESET_STYLES:
            style = self.get_preset(preset)
            # Override with any LLM-provided keywords
            if data.get("visual_keywords"):
                style.visual_keywords = data["visual_keywords"]
            if data.get("description"):
                style.description = data["description"]
            return style

        return Style(
            name=data.get("name", "Custom"),
            preset=preset,
            description=data.get("description", ""),
            visual_keywords=data.get("visual_keywords", []),
            color_temperature=float(data.get("color_temperature", 5500)),
            saturation=float(data.get("saturation", 1.0)),
            contrast=float(data.get("contrast", 1.0)),
            grain=float(data.get("grain", 0.0)),
            lighting_direction=data.get("lighting_direction", "natural"),
            camera_motion=data.get("camera_motion", "static"),
            is_preset=False,
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
