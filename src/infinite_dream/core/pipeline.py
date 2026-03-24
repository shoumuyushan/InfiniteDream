"""Pipeline engine — DAG-based video production pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from infinite_dream.models.project import Project


class Stage(ABC):
    """Abstract pipeline stage."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable stage name."""
        ...

    @abstractmethod
    async def execute(self, project: Project) -> None:
        """Execute this stage, mutating the project in place."""
        ...

    def can_skip(self, project: Project) -> bool:
        """Return True if this stage can be skipped (already done)."""
        return False


@dataclass
class PipelineResult:
    """Result of a pipeline run."""

    completed_stages: list[str] = field(default_factory=list)
    failed_stage: str | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.failed_stage is None


class Pipeline:
    """Video production pipeline — runs stages in sequence with checkpointing."""

    def __init__(self, stages: list[Stage] | None = None):
        self.stages: list[Stage] = stages or []

    def add_stage(self, stage: Stage) -> None:
        self.stages.append(stage)

    async def run(self, project: Project, from_stage: int = 0) -> PipelineResult:
        """Run the pipeline from a given stage index."""
        result = PipelineResult()

        for i, stage in enumerate(self.stages[from_stage:], start=from_stage):
            if stage.can_skip(project):
                result.completed_stages.append(f"{stage.name} (skipped)")
                continue

            try:
                project.current_stage = i
                await stage.execute(project)
                result.completed_stages.append(stage.name)
            except Exception as exc:
                result.failed_stage = stage.name
                result.error = str(exc)
                break

        return result

    async def rerun_from(self, project: Project, stage_index: int) -> PipelineResult:
        """Re-run from a specific stage (for non-destructive editing)."""
        return await self.run(project, from_stage=stage_index)
