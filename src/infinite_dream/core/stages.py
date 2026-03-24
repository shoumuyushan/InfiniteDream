"""Pipeline stages — wrap core modules into the Stage interface."""

from __future__ import annotations

import logging

from infinite_dream.adapters.base import LLMAdapter
from infinite_dream.adapters.factory import create_llm_adapter, create_video_adapter
from infinite_dream.config import AppConfig
from infinite_dream.core.audio import AudioMixer
from infinite_dream.core.compositor import Compositor
from infinite_dream.core.enhancer import ScriptEnhancer
from infinite_dream.core.exporter import Exporter
from infinite_dream.core.extractor import CharacterExtractor, SceneExtractor
from infinite_dream.core.parser import ScriptParser
from infinite_dream.core.pipeline import Pipeline, Stage
from infinite_dream.core.prompt import PromptBuilder
from infinite_dream.core.splitter import SegmentSplitter
from infinite_dream.core.style import StyleAnalyzer
from infinite_dream.models import SegmentStatus
from infinite_dream.models.project import Project

logger = logging.getLogger(__name__)


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


# ── Post-production stages ────────────────────────


class VideoGenerationStage(Stage):
    """Stage 7: 调用视频 AI 生成分段视频.

    Iterates through the segment plan and calls the video generation adapter
    for each segment that is still pending.  In the current implementation
    the actual generation is delegated to an external adapter (e.g. Kling);
    this stage simply drives the loop and updates segment statuses.
    """

    @property
    def name(self) -> str:
        return "Video Generation"

    async def execute(self, project: Project) -> None:
        if project.segment_plan is None:
            raise ValueError("Project has no segment plan")

        for seg in project.segment_plan.segments:
            if seg.status == SegmentStatus.COMPLETED and seg.video_path:
                continue
            # Mark as generating — actual AI call would go here via adapter
            seg.status = SegmentStatus.GENERATING
            logger.info("Generating video for segment %s (seq %d)", seg.id, seg.sequence)
            # Placeholder: real implementation calls video adapter
            # adapter.generate(seg) → sets seg.video_path
            # For now we leave status as GENERATING; a real adapter would
            # set it to COMPLETED with a video_path.

    def can_skip(self, project: Project) -> bool:
        if project.segment_plan is None:
            return False
        return all(
            seg.status == SegmentStatus.COMPLETED and seg.video_path
            for seg in project.segment_plan.segments
        )


class CompositionStage(Stage):
    """Stage 8: 拼接视频 + 转场.

    Uses :class:`Compositor` to stitch all segment videos together,
    applying transitions and inserting B-roll where specified.
    """

    def __init__(self, output_dir: str = "/tmp/id-output") -> None:
        self.output_dir = output_dir

    @property
    def name(self) -> str:
        return "Composition"

    async def execute(self, project: Project) -> None:
        if project.segment_plan is None:
            raise ValueError("Project has no segment plan")

        from pathlib import Path

        output_path = str(Path(self.output_dir) / f"{project.id}_composed.mp4")

        compositor = Compositor()
        project.output_video_path = compositor.compose(
            segments=project.segment_plan.segments,
            transitions=project.transitions,
            b_rolls=project.b_rolls,
            output_path=output_path,
        )

    def can_skip(self, project: Project) -> bool:
        return project.output_video_path is not None


class AudioProcessingStage(Stage):
    """Stage 9: 音频后处理.

    Runs :class:`AudioMixer.process_full` to extract per-segment audio,
    crossfade between segments, and merge the result back into the video.
    """

    def __init__(
        self,
        crossfade_duration: float = 2.0,
        output_dir: str = "/tmp/id-output",
    ) -> None:
        self.crossfade_duration = crossfade_duration
        self.output_dir = output_dir

    @property
    def name(self) -> str:
        return "Audio Processing"

    async def execute(self, project: Project) -> None:
        if project.output_video_path is None:
            raise ValueError("Project has no composed video to process audio for")
        if project.segment_plan is None:
            raise ValueError("Project has no segment plan")

        from pathlib import Path

        output_path = str(Path(self.output_dir) / f"{project.id}_audio.mp4")
        seg_paths = [
            seg.video_path
            for seg in project.segment_plan.segments
            if seg.video_path
        ]

        mixer = AudioMixer(crossfade_duration=self.crossfade_duration)
        project.output_video_path = mixer.process_full(
            video_path=project.output_video_path,
            segment_video_paths=seg_paths,
            output_path=output_path,
        )

    def can_skip(self, project: Project) -> bool:
        # Always reprocess audio when run
        return False


class ExportStage(Stage):
    """Stage 10: 最终导出.

    Uses :class:`Exporter` to produce the final encoded video and SRT
    subtitles.
    """

    def __init__(
        self,
        resolution: str = "1080p",
        codec: str = "h264",
        output_dir: str = "/tmp/id-output",
    ) -> None:
        self.resolution = resolution
        self.codec = codec
        self.output_dir = output_dir

    @property
    def name(self) -> str:
        return "Export"

    async def execute(self, project: Project) -> None:
        if project.output_video_path is None:
            raise ValueError("Project has no video to export")

        from pathlib import Path

        out_dir = Path(self.output_dir)
        final_path = str(out_dir / f"{project.id}_final.mp4")
        subtitle_path = str(out_dir / f"{project.id}.srt")

        exporter = Exporter()
        project.output_video_path = exporter.export(
            video_path=project.output_video_path,
            output_path=final_path,
            resolution=self.resolution,
            codec=self.codec,
        )

        # Generate subtitles if enhanced script is available
        if project.enhanced_script is not None:
            project.output_subtitle_path = exporter.generate_subtitle(
                enhanced_script=project.enhanced_script,
                output_path=subtitle_path,
            )

    def can_skip(self, project: Project) -> bool:
        # Always re-export
        return False


# ── Default pipeline builder ─────────────────────


def build_default_pipeline(config: AppConfig) -> Pipeline:
    """Construct a Pipeline with all text-processing and post-production stages.

    Uses the provided AppConfig to select and configure adapters via the
    adapter factory, which automatically falls back to mock adapters when
    no API key is configured.
    """
    llm = create_llm_adapter(config.llm)
    _video = create_video_adapter(config.video)  # noqa: F841 — used in later phases

    stages: list[Stage] = [
        # Text processing stages (1-7)
        ScriptParseStage(),
        CharacterExtractionStage(llm),
        SceneExtractionStage(llm),
        StyleAnalysisStage(llm),
        ScriptEnhancementStage(llm, level="moderate"),
        SegmentSplitStage(max_segment_duration=config.max_segment_duration_sec),
        PromptBuildStage(),
        # Post-production stages (7-10)
        VideoGenerationStage(),
        CompositionStage(),
        AudioProcessingStage(),
        ExportStage(),
    ]

    return Pipeline(stages=stages)
