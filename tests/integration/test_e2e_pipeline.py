"""End-to-end pipeline test using mocks."""

import pathlib

import pytest

from infinite_dream.core.pipeline import Pipeline, Stage
from infinite_dream.models import (
    Character,
    EnhancedScript,
    Project,
    ProjectStatus,
    Scene,
    Script,
    ScriptSegment,
    SegmentPlan,
    Style,
    StylePreset,
    VideoSegment,
)


FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"

SAMPLE_SCRIPT_ZH = """
第一章：月下相遇

夜晚，竹林中，月光如水。
林婉儿独自行走在竹林小路上，白色汉服随风飘动。
远处传来笛声，她停下脚步，循声望去。

叶凌风倚坐在竹枝上，吹着一支翠竹笛。
两人目光相遇。

叶凌风：「深夜独行，姑娘不怕迷路？」
林婉儿：「竹林虽深，心中有路。」

第二章：比武切磋

清晨，练武场上。
叶凌风与林婉儿持剑对峙。
两人交手数十回合，剑光闪烁。
最终叶凌风手中长剑飞出，林婉儿剑指其咽喉。

林婉儿：「承让。」
叶凌风（微笑）：「下次不会再让了。」
"""

SAMPLE_SCRIPT_EN = """
Chapter 1: The Encounter

Night. A bamboo forest bathed in moonlight.
Sarah walks alone through the narrow path, her white dress flowing in the wind.
A flute melody drifts from somewhere ahead. She stops and looks.

James sits on a bamboo branch, playing a jade flute.
Their eyes meet.

James: "Walking alone at night? Aren't you afraid of getting lost?"
Sarah: "The forest may be deep, but I know my way."
"""


# ── Mock Stages (simulating real pipeline stages without LLM) ──


class MockParserStage(Stage):
    """Mock parser that extracts characters and scenes from script content."""

    @property
    def name(self) -> str:
        return "script_parser"

    async def execute(self, project: Project) -> None:
        assert project.script is not None, "Project must have a script"
        content = project.script.content

        # Simple heuristic parser: find character names from dialogue
        # Chinese format: Name：「...」  or  Name（...）：「...」
        # English format: Name: "..."
        characters_found: dict[str, Character] = {}
        scenes_found: list[Scene] = []

        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Detect chapters as scenes
            if line.startswith("第") and "章" in line:
                scene_name = line.split("：", 1)[-1] if "：" in line else line
                scenes_found.append(Scene(
                    script_id=project.script.id,
                    name=scene_name,
                ))
            elif line.startswith("Chapter"):
                scene_name = line.split(": ", 1)[-1] if ": " in line else line
                scenes_found.append(Scene(
                    script_id=project.script.id,
                    name=scene_name,
                ))

            # Detect Chinese dialogue
            if "：" in line and "「" in line:
                name = line.split("：")[0].strip()
                # Remove annotations like （微笑）
                if "（" in name:
                    name = name.split("（")[0].strip()
                if name and name not in characters_found:
                    characters_found[name] = Character(
                        script_id=project.script.id,
                        name=name,
                    )

            # Detect English dialogue
            if ": \"" in line:
                name = line.split(":")[0].strip()
                if name and name not in characters_found:
                    characters_found[name] = Character(
                        script_id=project.script.id,
                        name=name,
                    )

        project.characters = list(characters_found.values())
        project.scenes = scenes_found


class MockSplitterStage(Stage):
    """Mock splitter that creates segments from scenes."""

    @property
    def name(self) -> str:
        return "script_splitter"

    async def execute(self, project: Project) -> None:
        assert project.script is not None
        segments: list[ScriptSegment] = []

        # Split content into non-empty paragraphs as segments
        paragraphs = [p.strip() for p in project.script.content.strip().split("\n\n") if p.strip()]

        for i, para in enumerate(paragraphs):
            seg = ScriptSegment(
                sequence=i,
                scene_id=project.scenes[min(i, len(project.scenes) - 1)].id if project.scenes else "",
                content=para,
                estimated_duration_sec=max(5, len(para) // 10),
            )
            segments.append(seg)

        project.enhanced_script = EnhancedScript(
            script_id=project.script.id,
            segments=segments,
            total_duration_sec=sum(s.estimated_duration_sec for s in segments),
        )


class MockPromptBuilderStage(Stage):
    """Mock prompt builder that creates video segments from enhanced script."""

    @property
    def name(self) -> str:
        return "prompt_builder"

    async def execute(self, project: Project) -> None:
        assert project.enhanced_script is not None
        video_segments: list[VideoSegment] = []

        for seg in project.enhanced_script.segments:
            vs = VideoSegment(
                sequence=seg.sequence,
                script_segment_id=seg.id,
                duration_sec=float(seg.estimated_duration_sec),
                visual_prompt=seg.content[:100],
            )
            video_segments.append(vs)

        project.segment_plan = SegmentPlan(
            enhanced_script_id=project.enhanced_script.id,
            target_total_duration_sec=project.enhanced_script.total_duration_sec,
            segments=video_segments,
        )


# ── Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_project_creation():
    """创建 Project 和 Script 并验证。"""
    script = Script(title="月下传奇", content=SAMPLE_SCRIPT_ZH, language="zh")
    project = Project(name="月下传奇", script=script)

    assert project.name == "月下传奇"
    assert project.status == ProjectStatus.DRAFT
    assert project.script is not None
    assert project.script.title == "月下传奇"
    assert project.script.language == "zh"
    assert len(project.script.content) > 0
    assert project.characters == []
    assert project.scenes == []


@pytest.mark.asyncio
async def test_e2e_simple_pipeline():
    """简单 pipeline（不需要 LLM 的 stages）能跑完。"""
    script = Script(title="Test", content=SAMPLE_SCRIPT_ZH, language="zh")
    project = Project(name="Test", script=script)

    pipeline = Pipeline(stages=[
        MockParserStage(),
        MockSplitterStage(),
        MockPromptBuilderStage(),
    ])

    result = await pipeline.run(project)

    assert result.success is True
    assert len(result.completed_stages) == 3
    assert result.completed_stages == ["script_parser", "script_splitter", "prompt_builder"]

    # Verify parsing happened
    assert len(project.characters) > 0
    assert len(project.scenes) > 0

    # Verify splitting happened
    assert project.enhanced_script is not None
    assert len(project.enhanced_script.segments) > 0

    # Verify prompt building happened
    assert project.segment_plan is not None
    assert len(project.segment_plan.segments) > 0


@pytest.mark.asyncio
async def test_e2e_sample_script_zh():
    """中文示例剧本能正确解析。"""
    script = Script(title="月下传奇", content=SAMPLE_SCRIPT_ZH, language="zh")
    project = Project(name="月下传奇", script=script)

    pipeline = Pipeline(stages=[
        MockParserStage(),
        MockSplitterStage(),
        MockPromptBuilderStage(),
    ])

    result = await pipeline.run(project)
    assert result.success is True

    # Check characters extracted
    char_names = {c.name for c in project.characters}
    assert "叶凌风" in char_names
    assert "林婉儿" in char_names

    # Check scenes extracted
    scene_names = {s.name for s in project.scenes}
    assert "月下相遇" in scene_names
    assert "比武切磋" in scene_names

    # Check enhanced script
    assert project.enhanced_script is not None
    assert project.enhanced_script.total_duration_sec > 0

    # Check segment plan
    assert project.segment_plan is not None
    assert len(project.segment_plan.segments) > 0
    for seg in project.segment_plan.segments:
        assert seg.visual_prompt != ""


@pytest.mark.asyncio
async def test_e2e_sample_script_en():
    """英文示例剧本能正确解析。"""
    script = Script(title="The Encounter", content=SAMPLE_SCRIPT_EN, language="en")
    project = Project(name="The Encounter", script=script)

    pipeline = Pipeline(stages=[
        MockParserStage(),
        MockSplitterStage(),
        MockPromptBuilderStage(),
    ])

    result = await pipeline.run(project)
    assert result.success is True

    # Check characters extracted
    char_names = {c.name for c in project.characters}
    assert "James" in char_names
    assert "Sarah" in char_names

    # Check scenes extracted
    assert len(project.scenes) > 0
    scene_names = {s.name for s in project.scenes}
    assert "The Encounter" in scene_names

    # Check full pipeline output
    assert project.enhanced_script is not None
    assert project.segment_plan is not None
    assert len(project.segment_plan.segments) > 0


@pytest.mark.asyncio
async def test_e2e_pipeline_with_style():
    """Pipeline 可以带 Style 运行。"""
    script = Script(title="Test", content=SAMPLE_SCRIPT_ZH, language="zh")
    style = Style(name="仙侠风", preset=StylePreset.XIANXIA)
    project = Project(name="Test", script=script, style=style)

    pipeline = Pipeline(stages=[
        MockParserStage(),
        MockSplitterStage(),
        MockPromptBuilderStage(),
    ])

    result = await pipeline.run(project)
    assert result.success is True
    assert project.style is not None
    assert project.style.preset == StylePreset.XIANXIA


@pytest.mark.asyncio
async def test_e2e_fixture_files_exist():
    """Fixture 文件存在并且内容非空。"""
    zh_file = FIXTURES_DIR / "sample_script_zh.txt"
    en_file = FIXTURES_DIR / "sample_script_en.txt"

    assert zh_file.exists(), f"Missing fixture: {zh_file}"
    assert en_file.exists(), f"Missing fixture: {en_file}"

    zh_content = zh_file.read_text(encoding="utf-8")
    en_content = en_file.read_text(encoding="utf-8")

    assert len(zh_content) > 50
    assert len(en_content) > 50
    assert "林婉儿" in zh_content
    assert "Sarah" in en_content
