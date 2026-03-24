"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="InfiniteDream",
    description="AI-driven long-form video production engine",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
