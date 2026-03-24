"""Test all data models."""

import uuid
from datetime import datetime

from infinite_dream.models import (
    BRoll,
    Character,
    EnhancedScript,
    Project,
    ProjectStatus,
    Scene,
    Script,
    ScriptSegment,
    SegmentPlan,
    SegmentStatus,
    Style,
    StylePreset,
    Transition,
    TransitionType,
    VideoSegment,
)


# ── Script ────────────────────────────────────────


def test_script_creation():
    """Script 创建时自动生成 ID 和时间戳。"""
    s = Script(title="Test", content="Hello world")
    # ID should be a valid UUID
    uuid.UUID(s.id)
    assert s.title == "Test"
    assert s.content == "Hello world"
    assert s.language == "zh"
    assert s.estimated_duration_sec == 0
    assert isinstance(s.created_at, datetime)
    assert isinstance(s.updated_at, datetime)

    # Two scripts get different IDs
    s2 = Script()
    assert s.id != s2.id


# ── Character ─────────────────────────────────────


def test_character_creation():
    """Character 所有字段有合理默认值。"""
    c = Character(name="林婉儿")
    uuid.UUID(c.id)
    assert c.name == "林婉儿"
    assert c.script_id == ""
    assert c.description == ""
    assert c.appearance_keywords == []
    assert c.reference_images == []
    assert c.traits == []
    assert c.age_range == ""


# ── Scene ─────────────────────────────────────────


def test_scene_creation():
    """Scene 所有字段有合理默认值。"""
    sc = Scene(name="竹林")
    uuid.UUID(sc.id)
    assert sc.name == "竹林"
    assert sc.script_id == ""
    assert sc.description == ""
    assert sc.environment_keywords == []
    assert sc.reference_images == []
    assert sc.time_of_day == "day"
    assert sc.mood == "neutral"


# ── StylePreset ───────────────────────────────────


def test_style_preset_enum():
    """StylePreset 枚举包含所有预设值。"""
    expected = {
        "CINEMATIC",
        "SWEET_ROMANCE",
        "XIANXIA",
        "CYBERPUNK",
        "WAR",
        "ANIME",
        "RETRO_FILM",
        "DOCUMENTARY",
        "CUSTOM",
    }
    actual = {p.name for p in StylePreset}
    assert actual == expected

    # Verify string values
    assert StylePreset.CINEMATIC.value == "cinematic"
    assert StylePreset.XIANXIA.value == "xianxia"
    assert StylePreset.CUSTOM.value == "custom"


# ── Style ─────────────────────────────────────────


def test_style_creation_with_preset():
    """Style 可以用预设创建。"""
    style = Style(name="仙侠风", preset=StylePreset.XIANXIA)
    uuid.UUID(style.id)
    assert style.name == "仙侠风"
    assert style.preset == StylePreset.XIANXIA
    assert style.color_temperature == 5500.0
    assert style.saturation == 1.0
    assert style.contrast == 1.0
    assert style.grain == 0.0
    assert style.lighting_direction == "natural"
    assert style.camera_motion == "static"
    assert style.is_preset is True


# ── VideoSegment ──────────────────────────────────


def test_video_segment_default_status():
    """VideoSegment 默认状态为 PENDING。"""
    vs = VideoSegment()
    assert vs.status == SegmentStatus.PENDING
    assert vs.video_path is None
    assert vs.retry_count == 0
    assert vs.duration_sec == 8.0
    assert vs.camera_motion == "static"
    assert vs.prev_segment_end_description is None
    assert vs.next_segment_start_hint is None


# ── SegmentPlan ───────────────────────────────────


def test_segment_plan_creation():
    """SegmentPlan 可以正确创建和包含 segments。"""
    seg1 = VideoSegment(sequence=0, visual_prompt="A bamboo forest")
    seg2 = VideoSegment(sequence=1, visual_prompt="Two swordsmen fighting")
    plan = SegmentPlan(
        enhanced_script_id="es-123",
        target_total_duration_sec=120,
        max_segment_duration_sec=15.0,
        segments=[seg1, seg2],
    )
    uuid.UUID(plan.id)
    assert plan.enhanced_script_id == "es-123"
    assert plan.target_total_duration_sec == 120
    assert len(plan.segments) == 2
    assert plan.segments[0].visual_prompt == "A bamboo forest"
    assert plan.segments[1].sequence == 1


# ── Project helpers ───────────────────────────────


def test_project_get_character():
    """Project.get_character() 按 ID 查找角色。"""
    c1 = Character(name="林婉儿")
    c2 = Character(name="叶凌风")
    proj = Project(name="Test", characters=[c1, c2])
    assert proj.get_character(c1.id) is c1
    assert proj.get_character(c2.id) is c2


def test_project_get_character_not_found():
    """找不到角色时返回 None。"""
    proj = Project(name="Test", characters=[Character(name="A")])
    assert proj.get_character("non-existent-id") is None


def test_project_get_scene():
    """Project.get_scene() 按 ID 查找场景。"""
    s1 = Scene(name="竹林")
    s2 = Scene(name="练武场")
    proj = Project(name="Test", scenes=[s1, s2])
    assert proj.get_scene(s1.id) is s1
    assert proj.get_scene(s2.id) is s2
    assert proj.get_scene("missing") is None


def test_project_get_characters_by_name():
    """Project.get_characters_by_name() 按名称查找。"""
    c1 = Character(name="林婉儿")
    c2 = Character(name="叶凌风")
    proj = Project(name="Test", characters=[c1, c2])
    assert proj.get_characters_by_name("林婉儿") is c1
    assert proj.get_characters_by_name("叶凌风") is c2
    assert proj.get_characters_by_name("不存在") is None


# ── TransitionType ────────────────────────────────


def test_transition_type_enum():
    """TransitionType 枚举值正确。"""
    expected_values = {"cut", "dissolve", "fade_black", "fade_white", "wipe"}
    actual_values = {t.value for t in TransitionType}
    assert actual_values == expected_values

    # Verify specific mappings
    assert TransitionType.CUT.value == "cut"
    assert TransitionType.DISSOLVE.value == "dissolve"
    assert TransitionType.FADE_BLACK.value == "fade_black"


# ── EnhancedScript ────────────────────────────────


def test_enhanced_script_with_segments():
    """EnhancedScript 可以包含多个 ScriptSegment。"""
    seg1 = ScriptSegment(sequence=0, content="月下相遇", estimated_duration_sec=10)
    seg2 = ScriptSegment(sequence=1, content="比武切磋", estimated_duration_sec=15)
    es = EnhancedScript(
        script_id="script-1",
        segments=[seg1, seg2],
        total_duration_sec=25,
        enhancement_level="heavy",
    )
    uuid.UUID(es.id)
    assert es.script_id == "script-1"
    assert len(es.segments) == 2
    assert es.segments[0].content == "月下相遇"
    assert es.segments[1].estimated_duration_sec == 15
    assert es.total_duration_sec == 25
    assert es.enhancement_level == "heavy"

    # Script segment defaults
    seg = ScriptSegment()
    assert seg.sequence == 0
    assert seg.scene_id == ""
    assert seg.characters_present == []
    assert seg.camera_direction == ""
    assert seg.estimated_duration_sec == 8
    assert seg.mood == "neutral"
