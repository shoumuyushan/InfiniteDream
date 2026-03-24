"""Core data models for InfiniteDream."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ── Script ────────────────────────────────────────


@dataclass
class Script:
    """Raw user script input."""

    id: str = field(default_factory=_new_id)
    title: str = ""
    content: str = ""
    language: str = "zh"  # "zh" | "en"
    estimated_duration_sec: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


# ── Character ─────────────────────────────────────


@dataclass
class Character:
    """Extracted character from script."""

    id: str = field(default_factory=_new_id)
    script_id: str = ""
    name: str = ""
    description: str = ""
    appearance_keywords: list[str] = field(default_factory=list)
    reference_images: list[str] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)
    age_range: str = ""


# ── Scene ─────────────────────────────────────────


@dataclass
class Scene:
    """Extracted scene/environment from script."""

    id: str = field(default_factory=_new_id)
    script_id: str = ""
    name: str = ""
    description: str = ""
    environment_keywords: list[str] = field(default_factory=list)
    reference_images: list[str] = field(default_factory=list)
    time_of_day: str = "day"  # "dawn" | "day" | "dusk" | "night"
    mood: str = "neutral"


# ── Style ─────────────────────────────────────────


class StylePreset(str, Enum):
    """Built-in style presets."""

    CINEMATIC = "cinematic"
    SWEET_ROMANCE = "sweet_romance"
    XIANXIA = "xianxia"
    CYBERPUNK = "cyberpunk"
    WAR = "war"
    ANIME = "anime"
    RETRO_FILM = "retro_film"
    DOCUMENTARY = "documentary"
    CUSTOM = "custom"


@dataclass
class Style:
    """Visual style configuration."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    preset: StylePreset = StylePreset.CINEMATIC
    description: str = ""
    visual_keywords: list[str] = field(default_factory=list)
    color_temperature: float = 5500.0  # Kelvin 2000-10000
    saturation: float = 1.0  # 0.0-2.0
    contrast: float = 1.0  # 0.0-2.0
    grain: float = 0.0  # 0.0-1.0
    lighting_direction: str = "natural"  # "natural"|"dramatic"|"soft"|"neon"
    camera_motion: str = "static"  # "static"|"handheld"|"dolly"|"crane"
    reference_images: list[str] = field(default_factory=list)
    is_preset: bool = True


# ── Script Segment ────────────────────────────────


@dataclass
class ScriptSegment:
    """A segment of the enhanced script."""

    id: str = field(default_factory=_new_id)
    sequence: int = 0
    scene_id: str = ""
    content: str = ""
    characters_present: list[str] = field(default_factory=list)  # Character IDs
    camera_direction: str = ""
    estimated_duration_sec: int = 8
    mood: str = "neutral"


@dataclass
class EnhancedScript:
    """Script after LLM enhancement."""

    id: str = field(default_factory=_new_id)
    script_id: str = ""
    segments: list[ScriptSegment] = field(default_factory=list)
    total_duration_sec: int = 0
    enhancement_level: str = "moderate"  # "light" | "moderate" | "heavy"


# ── Video Segment ─────────────────────────────────


class SegmentStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VideoSegment:
    """A video segment ready for generation."""

    id: str = field(default_factory=_new_id)
    sequence: int = 0
    script_segment_id: str = ""
    duration_sec: float = 8.0

    # Prompt components
    visual_prompt: str = ""
    character_keywords: list[str] = field(default_factory=list)
    environment_keywords: list[str] = field(default_factory=list)
    style_keywords: list[str] = field(default_factory=list)
    camera_motion: str = "static"

    # Continuity
    prev_segment_end_description: str | None = None
    next_segment_start_hint: str | None = None

    # State
    status: SegmentStatus = SegmentStatus.PENDING
    video_path: str | None = None
    retry_count: int = 0


@dataclass
class SegmentPlan:
    """Complete plan for all video segments."""

    id: str = field(default_factory=_new_id)
    enhanced_script_id: str = ""
    target_total_duration_sec: int = 0
    max_segment_duration_sec: float = 15.0
    segments: list[VideoSegment] = field(default_factory=list)


# ── Transition & B-Roll ───────────────────────────


class TransitionType(str, Enum):
    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE_BLACK = "fade_black"
    FADE_WHITE = "fade_white"
    WIPE = "wipe"


@dataclass
class Transition:
    """Transition between two video segments."""

    type: TransitionType = TransitionType.DISSOLVE
    duration_sec: float = 0.5


@dataclass
class BRoll:
    """B-roll / establishing shot inserted between segments."""

    id: str = field(default_factory=_new_id)
    insert_after_segment: int = 0  # sequence number
    visual_prompt: str = ""
    environment_keywords: list[str] = field(default_factory=list)
    style_keywords: list[str] = field(default_factory=list)
    duration_sec: float = 3.0
    video_path: str | None = None


# ── Project (Aggregate Root) ─────────────────────


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Project:
    """Top-level project containing all data for a video production."""

    id: str = field(default_factory=_new_id)
    name: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    current_stage: int = 0

    # Core data
    script: Script | None = None
    characters: list[Character] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    style: Style | None = None
    enhanced_script: EnhancedScript | None = None
    segment_plan: SegmentPlan | None = None
    transitions: list[Transition] = field(default_factory=list)
    b_rolls: list[BRoll] = field(default_factory=list)

    # Output
    output_video_path: str | None = None
    output_subtitle_path: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    # ── Helpers ──

    def get_character(self, char_id: str) -> Character | None:
        return next((c for c in self.characters if c.id == char_id), None)

    def get_scene(self, scene_id: str) -> Scene | None:
        return next((s for s in self.scenes if s.id == scene_id), None)

    def get_characters_by_name(self, name: str) -> Character | None:
        return next((c for c in self.characters if c.name == name), None)
