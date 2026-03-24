"""Test pipeline engine."""

import pytest

from infinite_dream.core.pipeline import Pipeline, PipelineResult, Stage
from infinite_dream.models import Project


# ── Test Stage implementations ────────────────────


class SuccessStage(Stage):
    """Stage that always succeeds and modifies the project."""

    @property
    def name(self) -> str:
        return "success"

    async def execute(self, project: Project) -> None:
        project.name = "modified"


class FailStage(Stage):
    """Stage that always raises an error."""

    @property
    def name(self) -> str:
        return "fail"

    async def execute(self, project: Project) -> None:
        raise RuntimeError("boom")


class SkippableStage(Stage):
    """Stage that is always skippable."""

    @property
    def name(self) -> str:
        return "skippable"

    async def execute(self, project: Project) -> None:
        project.name = "should-not-reach"

    def can_skip(self, project: Project) -> bool:
        return True


class TrackingStage(Stage):
    """Stage that tracks execution order."""

    def __init__(self, label: str, tracker: list[str]):
        self._label = label
        self._tracker = tracker

    @property
    def name(self) -> str:
        return self._label

    async def execute(self, project: Project) -> None:
        self._tracker.append(self._label)


# ── Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_runs_stages_in_order():
    """Pipeline 按顺序执行所有 stage。"""
    tracker: list[str] = []
    pipeline = Pipeline(stages=[
        TrackingStage("first", tracker),
        TrackingStage("second", tracker),
        TrackingStage("third", tracker),
    ])
    project = Project(name="test")
    result = await pipeline.run(project)

    assert tracker == ["first", "second", "third"]
    assert result.completed_stages == ["first", "second", "third"]
    assert result.success is True


@pytest.mark.asyncio
async def test_pipeline_stops_on_failure():
    """Pipeline 遇到失败停止并记录错误。"""
    tracker: list[str] = []
    pipeline = Pipeline(stages=[
        TrackingStage("stage-1", tracker),
        FailStage(),
        TrackingStage("stage-3", tracker),
    ])
    project = Project(name="test")
    result = await pipeline.run(project)

    # Only first stage should have run
    assert tracker == ["stage-1"]
    assert result.success is False
    assert result.failed_stage == "fail"
    assert result.error == "boom"
    # stage-3 should NOT appear
    assert "stage-3" not in result.completed_stages


@pytest.mark.asyncio
async def test_pipeline_skips_skippable_stages():
    """可跳过的 stage 被跳过。"""
    pipeline = Pipeline(stages=[
        SuccessStage(),
        SkippableStage(),
    ])
    project = Project(name="original")
    result = await pipeline.run(project)

    assert result.success is True
    assert "skippable (skipped)" in result.completed_stages
    # SuccessStage modifies the name, but SkippableStage should NOT
    assert project.name == "modified"


@pytest.mark.asyncio
async def test_pipeline_from_stage():
    """Pipeline 可以从指定 stage 开始。"""
    tracker: list[str] = []
    pipeline = Pipeline(stages=[
        TrackingStage("first", tracker),
        TrackingStage("second", tracker),
        TrackingStage("third", tracker),
    ])
    project = Project(name="test")
    result = await pipeline.run(project, from_stage=1)

    # Only second and third should run
    assert tracker == ["second", "third"]
    assert result.completed_stages == ["second", "third"]
    assert result.success is True


@pytest.mark.asyncio
async def test_pipeline_result_success():
    """成功时 result.success 为 True。"""
    pipeline = Pipeline(stages=[SuccessStage()])
    project = Project(name="test")
    result = await pipeline.run(project)

    assert result.success is True
    assert result.failed_stage is None
    assert result.error is None
    assert result.completed_stages == ["success"]


@pytest.mark.asyncio
async def test_pipeline_result_failure():
    """失败时 result 记录 failed_stage 和 error。"""
    pipeline = Pipeline(stages=[FailStage()])
    project = Project(name="test")
    result = await pipeline.run(project)

    assert result.success is False
    assert result.failed_stage == "fail"
    assert result.error == "boom"
    assert result.completed_stages == []


@pytest.mark.asyncio
async def test_empty_pipeline():
    """空 pipeline 也能成功运行。"""
    pipeline = Pipeline()
    project = Project(name="test")
    result = await pipeline.run(project)

    assert result.success is True
    assert result.completed_stages == []
    assert result.failed_stage is None
    assert result.error is None


@pytest.mark.asyncio
async def test_pipeline_add_stage():
    """Pipeline.add_stage() 正确添加 stage。"""
    pipeline = Pipeline()
    pipeline.add_stage(SuccessStage())
    assert len(pipeline.stages) == 1

    project = Project(name="test")
    result = await pipeline.run(project)
    assert result.success is True
    assert project.name == "modified"


@pytest.mark.asyncio
async def test_pipeline_rerun_from():
    """Pipeline.rerun_from() 从指定 stage 重跑。"""
    tracker: list[str] = []
    pipeline = Pipeline(stages=[
        TrackingStage("a", tracker),
        TrackingStage("b", tracker),
        TrackingStage("c", tracker),
    ])
    project = Project(name="test")
    result = await pipeline.rerun_from(project, stage_index=2)

    assert tracker == ["c"]
    assert result.success is True
    assert result.completed_stages == ["c"]


@pytest.mark.asyncio
async def test_pipeline_current_stage_tracking():
    """Pipeline 执行时更新 project.current_stage。"""
    pipeline = Pipeline(stages=[SuccessStage()])
    project = Project(name="test")
    assert project.current_stage == 0

    await pipeline.run(project)
    assert project.current_stage == 0  # index 0 was last executed


@pytest.mark.asyncio
async def test_pipeline_result_dataclass():
    """PipelineResult 默认值正确。"""
    result = PipelineResult()
    assert result.completed_stages == []
    assert result.failed_stage is None
    assert result.error is None
    assert result.success is True
