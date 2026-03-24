"""FastAPI application entry point with API routes and simple Web UI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from infinite_dream.config import AppConfig
from infinite_dream.models import (
    Project,
    Script,
    Style,
    StylePreset,
)
from infinite_dream.core.parser import ScriptParser
from infinite_dream.core.style import StyleAnalyzer
from infinite_dream.core.splitter import SegmentSplitter
from infinite_dream.core.prompt import PromptBuilder

app = FastAPI(
    title="InfiniteDream",
    description="AI-driven long-form video production engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory project store (demo mode)
_projects: dict[str, Project] = {}
_config = AppConfig.from_env()
_parser = ScriptParser()


# ── Pydantic request/response models ──


class ScriptInput(BaseModel):
    title: str = "Untitled"
    content: str
    style_preset: str = "cinematic"
    target_duration_sec: int = 60


class ProjectSummary(BaseModel):
    id: str
    name: str
    status: str
    stage: int
    characters: int
    scenes: int
    segments: int
    style: str | None


class ProviderConfig(BaseModel):
    """API provider configuration from UI."""

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: str = ""
    llm_base_url: str = ""
    video_provider: str = "kling"
    video_api_key: str = ""
    video_base_url: str = ""


# ── API Routes ──


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/config")
async def update_config(config: ProviderConfig) -> dict:
    """Update runtime configuration."""
    global _config
    _config.llm.provider = config.llm_provider
    _config.llm.model = config.llm_model
    _config.llm.api_key = config.llm_api_key
    _config.llm.base_url = config.llm_base_url or None
    _config.video.provider = config.video_provider
    _config.video.api_key = config.video_api_key
    _config.video.base_url = config.video_base_url
    return {"status": "ok", "message": "Configuration updated"}


@app.get("/api/config")
async def get_config() -> dict:
    """Get current configuration (mask secrets)."""
    return {
        "llm_provider": _config.llm.provider,
        "llm_model": _config.llm.model,
        "llm_api_key": "***" + _config.llm.api_key[-4:] if len(_config.llm.api_key) > 4 else "",
        "llm_base_url": _config.llm.base_url or "",
        "video_provider": _config.video.provider,
        "video_api_key": "***" + _config.video.api_key[-4:] if len(_config.video.api_key) > 4 else "",
        "video_base_url": _config.video.base_url,
    }


@app.get("/api/styles")
async def list_styles() -> list[dict]:
    """List all available style presets."""
    styles = []
    for preset in StylePreset:
        if preset == StylePreset.CUSTOM:
            continue
        s = StyleAnalyzer.get_preset(preset)
        styles.append({
            "id": preset.value,
            "name": s.name,
            "description": s.description,
            "keywords": s.visual_keywords,
        })
    return styles


@app.post("/api/projects")
async def create_project(input: ScriptInput) -> dict:
    """Create a new project: parse script, analyze style, split segments, build prompts."""
    # 1. Parse script
    script = _parser.parse(input.content)
    script.title = input.title

    # 2. Create project
    project = Project(name=input.title)
    project.script = script

    # 3. Style
    try:
        preset = StylePreset(input.style_preset)
    except ValueError:
        preset = StylePreset.CINEMATIC
    project.style = StyleAnalyzer.get_preset(preset)

    # 4. Mock characters & scenes extraction (no LLM key needed for demo)
    from infinite_dream.adapters.llm import MockLLMAdapter
    from infinite_dream.core.extractor import CharacterExtractor, SceneExtractor

    llm = MockLLMAdapter()
    project.characters = await CharacterExtractor(llm).extract(script)
    project.scenes = await SceneExtractor(llm).extract(script, project.characters)

    # 5. Mock enhancement
    from infinite_dream.core.enhancer import ScriptEnhancer

    project.enhanced_script = await ScriptEnhancer(llm).enhance(
        script, project.characters, project.scenes
    )

    # 6. Split segments
    splitter = SegmentSplitter()
    project.segment_plan = splitter.split(
        project.enhanced_script,
        max_segment_duration=_config.max_segment_duration_sec,
    )

    # 7. Build prompts
    builder = PromptBuilder()
    builder.build_all(project)

    project.current_stage = 6
    _projects[project.id] = project

    return _project_detail(project)


@app.get("/api/projects")
async def list_projects() -> list[ProjectSummary]:
    """List all projects."""
    return [
        ProjectSummary(
            id=p.id,
            name=p.name,
            status=p.status.value,
            stage=p.current_stage,
            characters=len(p.characters),
            scenes=len(p.scenes),
            segments=len(p.segment_plan.segments) if p.segment_plan else 0,
            style=p.style.name if p.style else None,
        )
        for p in _projects.values()
    ]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """Get full project details."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_detail(project)


def _project_detail(project: Project) -> dict:
    """Build full project detail response."""
    segments_data = []
    if project.segment_plan:
        for seg in project.segment_plan.segments:
            segments_data.append({
                "sequence": seg.sequence,
                "duration_sec": seg.duration_sec,
                "visual_prompt": seg.visual_prompt,
                "character_keywords": seg.character_keywords,
                "environment_keywords": seg.environment_keywords,
                "style_keywords": seg.style_keywords,
                "camera_motion": seg.camera_motion,
                "status": seg.status.value,
            })

    return {
        "id": project.id,
        "name": project.name,
        "status": project.status.value,
        "current_stage": project.current_stage,
        "script": {
            "title": project.script.title if project.script else "",
            "language": project.script.language if project.script else "",
            "estimated_duration_sec": project.script.estimated_duration_sec if project.script else 0,
            "content_length": len(project.script.content) if project.script else 0,
        },
        "characters": [
            {
                "name": c.name,
                "description": c.description,
                "appearance_keywords": c.appearance_keywords,
                "age_range": c.age_range,
            }
            for c in project.characters
        ],
        "scenes": [
            {
                "name": s.name,
                "description": s.description,
                "environment_keywords": s.environment_keywords,
                "time_of_day": s.time_of_day,
                "mood": s.mood,
            }
            for s in project.scenes
        ],
        "style": {
            "name": project.style.name,
            "preset": project.style.preset.value,
            "visual_keywords": project.style.visual_keywords,
            "description": project.style.description,
        }
        if project.style
        else None,
        "segments": segments_data,
        "segment_count": len(segments_data),
    }


# ── Web UI ──

WEB_UI_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>InfiniteDream — AI 视频生产引擎</title>
<style>
  :root { --bg: #0d1117; --bg-1: #161b22; --bg-2: #21262d; --border: #30363d; --text: #e6edf3; --text-2: #8b949e; --accent: #58a6ff; --green: #3fb950; --yellow: #d29922; --red: #f85149; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
  .container { max-width: 960px; margin: 0 auto; padding: 24px; }
  h1 { font-size: 28px; margin-bottom: 8px; }
  h1 span { color: var(--accent); }
  .subtitle { color: var(--text-2); margin-bottom: 24px; font-size: 14px; }
  .card { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 16px; }
  .card h2 { font-size: 16px; margin-bottom: 12px; color: var(--accent); }
  .card h3 { font-size: 14px; margin: 12px 0 6px; color: var(--text-2); text-transform: uppercase; letter-spacing: 0.05em; }
  textarea { width: 100%; height: 200px; background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); padding: 12px; font-size: 14px; resize: vertical; font-family: inherit; }
  input, select { background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); padding: 8px 12px; font-size: 14px; }
  .form-row { display: flex; gap: 12px; margin: 12px 0; align-items: end; flex-wrap: wrap; }
  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .form-group label { font-size: 12px; color: var(--text-2); }
  .btn { background: var(--accent); color: #fff; border: none; border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }
  .btn:hover { opacity: 0.85; }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-lg { font-size: 16px; padding: 12px 32px; }
  .tag { display: inline-block; background: var(--bg-2); border: 1px solid var(--border); border-radius: 4px; padding: 2px 8px; font-size: 12px; margin: 2px; }
  .tag.accent { border-color: var(--accent); color: var(--accent); }
  .result { display: none; }
  .result.visible { display: block; }
  .character-card, .scene-card, .segment-card { background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin: 8px 0; }
  .character-card .name, .scene-card .name { font-weight: 600; font-size: 15px; margin-bottom: 4px; }
  .character-card .desc, .scene-card .desc { font-size: 13px; color: var(--text-2); margin-bottom: 6px; }
  .segment-card { position: relative; }
  .segment-card .seq { position: absolute; right: 12px; top: 12px; background: var(--accent); color: #fff; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
  .segment-card .prompt { font-size: 13px; color: var(--text); white-space: pre-wrap; word-break: break-all; background: var(--bg); border-radius: 4px; padding: 8px; margin-top: 8px; font-family: 'SF Mono', Menlo, monospace; line-height: 1.5; }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; }
  .stat { background: var(--bg-2); border-radius: 6px; padding: 12px 16px; min-width: 120px; }
  .stat .num { font-size: 24px; font-weight: 700; color: var(--accent); }
  .stat .label { font-size: 12px; color: var(--text-2); }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; margin-left: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-text { color: var(--text-2); font-size: 14px; }
</style>
</head>
<body>
<div class="container">
  <h1>🎬 <span>InfiniteDream</span></h1>
  <div class="subtitle">AI 驱动的长视频自动化生产引擎 — 从剧本到成片</div>

  <div class="card" id="input-card">
    <h2>📝 输入剧本</h2>
    <textarea id="script-input" placeholder="在这里输入你的剧本...&#10;&#10;例如：&#10;第一章：月下相遇&#10;夜晚，竹林中，月光如水。&#10;林婉儿独自行走在竹林小路上，白色汉服随风飘动..."></textarea>
    <div class="form-row">
      <div class="form-group">
        <label>项目名称</label>
        <input id="title-input" type="text" value="我的视频" placeholder="项目名称" />
      </div>
      <div class="form-group">
        <label>视觉风格</label>
        <select id="style-select">
          <option value="cinematic">🎥 写实电影</option>
          <option value="sweet_romance">💕 甜宠</option>
          <option value="xianxia">🏔️ 仙侠</option>
          <option value="cyberpunk">🌃 赛博朋克</option>
          <option value="war">⚔️ 战争</option>
          <option value="anime">🎨 日系动画</option>
          <option value="retro_film">📽️ 复古胶片</option>
          <option value="documentary">📹 纪录片</option>
        </select>
      </div>
      <button class="btn btn-lg" id="generate-btn" onclick="generate()">🚀 开始生成</button>
    </div>
  </div>

  <div id="loading" style="display:none" class="card">
    <span class="loading-text">正在分析剧本、提取角色、生成分段...</span><span class="spinner"></span>
  </div>

  <div id="result" class="result">
    <div class="card">
      <h2>📊 项目概览</h2>
      <div class="stats" id="stats"></div>
    </div>

    <div class="card">
      <h2>🎭 提取的角色</h2>
      <div id="characters"></div>
    </div>

    <div class="card">
      <h2>🏞️ 提取的场景</h2>
      <div id="scenes"></div>
    </div>

    <div class="card">
      <h2>🎨 视觉风格</h2>
      <div id="style-info"></div>
    </div>

    <div class="card">
      <h2>🎬 分段视频计划 <span id="segment-count" style="color:var(--text-2);font-size:14px"></span></h2>
      <p style="font-size:13px;color:var(--text-2);margin-bottom:12px">每个分段将带着一致性关键词（角色+环境+风格）调用视频 AI 生成</p>
      <div id="segments"></div>
    </div>
  </div>
</div>

<script>
async function generate() {
  const btn = document.getElementById('generate-btn');
  const loading = document.getElementById('loading');
  const result = document.getElementById('result');
  const content = document.getElementById('script-input').value.trim();
  if (!content) { alert('请输入剧本内容'); return; }

  btn.disabled = true;
  loading.style.display = 'block';
  result.classList.remove('visible');

  try {
    const resp = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: document.getElementById('title-input').value || '我的视频',
        content: content,
        style_preset: document.getElementById('style-select').value,
      }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    renderResult(data);
    result.classList.add('visible');
  } catch (e) {
    alert('生成失败: ' + e.message);
  } finally {
    btn.disabled = false;
    loading.style.display = 'none';
  }
}

function renderResult(data) {
  // Stats
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="num">${data.characters.length}</div><div class="label">角色</div></div>
    <div class="stat"><div class="num">${data.scenes.length}</div><div class="label">场景</div></div>
    <div class="stat"><div class="num">${data.segment_count}</div><div class="label">视频分段</div></div>
    <div class="stat"><div class="num">${data.script.estimated_duration_sec}s</div><div class="label">预估时长</div></div>
    <div class="stat"><div class="num">${data.script.language === 'zh' ? '中文' : 'English'}</div><div class="label">语言</div></div>
  `;

  // Characters
  document.getElementById('characters').innerHTML = data.characters.map(c => `
    <div class="character-card">
      <div class="name">🎭 ${esc(c.name)} ${c.age_range ? '<span style="color:var(--text-2);font-size:12px">(' + esc(c.age_range) + ')</span>' : ''}</div>
      <div class="desc">${esc(c.description)}</div>
      <div>${(c.appearance_keywords || []).map(k => '<span class="tag accent">' + esc(k) + '</span>').join('')}</div>
    </div>
  `).join('') || '<div style="color:var(--text-2)">未提取到角色</div>';

  // Scenes
  document.getElementById('scenes').innerHTML = data.scenes.map(s => `
    <div class="scene-card">
      <div class="name">🏞️ ${esc(s.name)} <span class="tag">${esc(s.time_of_day)}</span> <span class="tag">${esc(s.mood)}</span></div>
      <div class="desc">${esc(s.description)}</div>
      <div>${(s.environment_keywords || []).map(k => '<span class="tag accent">' + esc(k) + '</span>').join('')}</div>
    </div>
  `).join('') || '<div style="color:var(--text-2)">未提取到场景</div>';

  // Style
  const st = data.style;
  document.getElementById('style-info').innerHTML = st ? `
    <div class="scene-card">
      <div class="name">🎨 ${esc(st.name)}</div>
      <div class="desc">${esc(st.description)}</div>
      <div>${(st.visual_keywords || []).map(k => '<span class="tag accent">' + esc(k) + '</span>').join('')}</div>
    </div>
  ` : '';

  // Segments
  document.getElementById('segment-count').textContent = `(${data.segment_count} 段)`;
  document.getElementById('segments').innerHTML = data.segments.map(s => `
    <div class="segment-card">
      <div class="seq">${s.sequence + 1}</div>
      <div style="font-size:13px;color:var(--text-2);margin-bottom:4px">
        ⏱ ${s.duration_sec}s · 🎥 ${esc(s.camera_motion)} · ${s.status === 'pending' ? '⏳ 待生成' : '✅ ' + s.status}
      </div>
      <div style="margin:4px 0">${(s.character_keywords || []).map(k => '<span class="tag">' + esc(k) + '</span>').join('')}</div>
      <div class="prompt">${esc(s.visual_prompt)}</div>
    </div>
  `).join('') || '<div style="color:var(--text-2)">无分段</div>';
}

function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def web_ui() -> str:
    """Serve the Web UI."""
    return WEB_UI_HTML
