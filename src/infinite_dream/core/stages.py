"""Pipeline stages — wrap core modules into the Stage interface."""

from __future__ import annotations

from infinite_dream.adapters.base import LLMAdapter
from infinite_dream.adapters.factory import create_llm_adapter, create_video_adapter
from infinite_dream.config import AppConfig
from infinite_dream.core.enhancer import ScriptEnhancer
from infinite_dream.core.extractor import CharacterExtractor, SceneExtractor
from infinite_dream.core.parser import ScriptParser
from infinite_dream.core.pipeline import Pipeline, Stage
from infinite_dream.core.prompt import PromptBuilder
from infinite_dream.core.splitter import SegmentSplitter
from infinite_dream.core.style import StyleAnalyzer
from infinite_dream.models.project import Project


# ── Stage implementations ─────────────────────────


class ScriptParseStage(Stage):
    """Parse the raw script text into a Script object."""

    @property
    def name(self) -> str:
        return "Script Parsing"

    async def execute(self, project: Project) -> None:
        if project.script is None:
            raise ValueError("Project has no script to parse")
        raw_text = project.script.content
        parser = ScriptParser()
        parsed = parser.parse(raw_text, title=project.script.title)
        # Update existing script in-place
        project.script.language = parsed.language
        project.script.estimated_duration_sec = parsed.estimated_duration_sec

    def can_skip(self, project: Project) -> bool:
        return (
            project.script is not None
            and project.script.estimated_duration_sec > 0
        )


class CharacterExtractionStage(Stage):
    """Extract characters from the script using an LLM."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    @property
    def name(self) -> str:
        return "Character Extraction"

    async def execute(self, project: Project) -> None:
        if project.script is None:
            raise ValueError("Project has no script")
        extractor = CharacterExtractor(self.llm)
        project.characters = await extractor.extract(project.script)

    def can_skip(self, project: Project) -> bool:
        return len(project.characters) > 0


class SceneExtractionStage(Stage):
    """Extract scenes from the script using an LLM."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    @property
    def name(self) -> str:
        return "Scene Extraction"

    async def execute(self, project: Project) -> None:
        if project.script is None:
            raise ValueError("Project has no script")
        extractor = SceneExtractor(self.llm)
        project.scenes = await extractor.extract(project.script, project.characters)

    def can_skip(self, project: Project) -> bool:
        return len(project.scenes) > 0


class StyleAnalysisStage(Stage):
    """Analyze the script and determine the visual style."""

    def __init__(self, llm: LLMAdapter) -> None:
        self.llm = llm

    @property
    def name(self) -> str:
        return "Style Analysis"

    async def execute(self, project: Project) -> None:
        if project.script is None:
            raise ValueError("Project has no script")
        analyzer = StyleAnalyzer(self.llm)
        project.style = await analyzer.analyze(project.script)

    def can_skip(self, project: Project) -> bool:
        return project.style is not None


class ScriptEnhancementStage(Stage):
    """Enhance the script with expanded prose and camera directions."""

    def __init__(self, llm: LLMAdapter, level: str = "moderate") -> None:
        self.llm = llm
        self.level = level

    @property
    def name(self) -> str:
        return "Script Enhancement"

    async def execute(self, project: Project) -> None:
        if project.script is None:
            raise ValueError("Project has no script")
        enhancer = ScriptEnhancer(self.llm)
        project.enhanced_script = await enhancer.enhance(
            project.script,
            project.characters,
            project.scenes,
            level=self.level,
        )

    def can_skip(self, project: Project) -> bool:
        return project.enhanced_script is not None


class SegmentSplitStage(Stage):
    """Split enhanced script into video segments."""

    def __init__(self, max_segment_duration: float = 15.0) -> None:
        self.max_segment_duration = max_segment_duration

    @property
    def name(self) -> str:
        return "Segment Splitting"

    async def execute(self, project: Project) -> None:
        if project.enhanced_script is None:
            raise ValueError("Project has no enhanced script")
        splitter = SegmentSplitter()
        project.segment_plan = splitter.split(
            project.enhanced_script,
            max_segment_duration=self.max_segment_duration,
        )

    def can_skip(self, project: Project) -> bool:
        return project.segment_plan is not None and len(project.segment_plan.segments) > 0


class PromptBuildStage(Stage):
    """Build generation prompts for all video segments."""

    @property
    def name(self) -> str:
        return "Prompt Building"

    async def execute(self, project: Project) -> None:
        if project.segment_plan is None:
            raise ValueError("Project has no segment plan")
        builder = PromptBuilder()
        builder.build_all(project)

    def can_skip(self, project: Project) -> bool:
        # Re-run prompt building every time for freshness
        return False


# ── Default pipeline builder ─────────────────────


def build_default_pipeline(config: AppConfig) -> Pipeline:
    """Construct a Pipeline with all text-processing stages.

    Uses the provided AppConfig to select and configure adapters via the
    adapter factory, which automatically falls back to mock adapters when
    no API key is configured.
    """
    llm = create_llm_adapter(config.llm)
    _video = create_video_adapter(config.video)  # noqa: F841 — used in later phases

    stages: list[Stage] = [
        ScriptParseStage(),
        CharacterExtractionStage(llm),
        SceneExtractionStage(llm),
        StyleAnalysisStage(llm),
        ScriptEnhancementStage(llm, level="moderate"),
        SegmentSplitStage(max_segment_duration=config.max_segment_duration_sec),
        PromptBuildStage(),
    ]

    return Pipeline(stages=stages)
