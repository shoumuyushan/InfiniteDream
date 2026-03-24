"""CLI entry point."""

from __future__ import annotations

import asyncio
import sys


def main() -> None:
    """CLI entry point for infinite-dream."""
    print("InfiniteDream — AI Video Production Engine")
    print("Usage: infinite-dream <command>")
    print()
    print("Commands:")
    print("  serve     Start the API server")
    print("  generate  Generate video from a script file")
    print("  version   Show version")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "version":
            print("infinite-dream 0.1.0")
        elif cmd == "serve":
            _serve()
        elif cmd == "generate":
            if len(sys.argv) < 3:
                print("Error: please provide a script file path")
                sys.exit(1)
            asyncio.run(_generate(sys.argv[2]))
        else:
            print(f"Unknown command: {cmd}")
            sys.exit(1)


def _serve() -> None:
    """Start the FastAPI server."""
    try:
        import uvicorn

        uvicorn.run("infinite_dream.main:app", host="0.0.0.0", port=8000, reload=True)
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)


async def _generate(script_path: str) -> None:
    """Generate video from a script file (CLI mode)."""
    from pathlib import Path

    path = Path(script_path)
    if not path.exists():
        print(f"Error: script file not found: {script_path}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    print(f"Loaded script: {path.name} ({len(content)} chars)")

    from infinite_dream.config import AppConfig
    from infinite_dream.core.pipeline import Pipeline
    from infinite_dream.core.stages import build_default_pipeline
    from infinite_dream.models import Project, Script

    config = AppConfig.from_env()
    project = Project(name=path.stem)
    project.script = Script(title=path.stem, content=content)

    pipeline = build_default_pipeline(config)
    result = await pipeline.run(project)

    if result.success:
        print(f"✅ Video generated: {project.output_video_path}")
    else:
        print(f"❌ Failed at stage '{result.failed_stage}': {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
