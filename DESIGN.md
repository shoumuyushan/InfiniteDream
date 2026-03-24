# InfiniteDream — 设计文档

> 从剧本到长视频的一站式 AI 生产引擎

---

## 一、产品设计

### 1.1 产品定位

**InfiniteDream** 是一款 AI 驱动的长视频自动化生产工具。用户输入剧本文本，系统自动完成角色提取、场景生成、风格设定、剧本优化、分段视频生成、拼接与后期处理，最终输出一部风格一致、角色统一的完整长视频。

核心价值主张：**「一个剧本，一键出片」**

### 1.2 目标用户

| 用户类型 | 典型场景 | 核心诉求 |
|---------|---------|---------|
| 自媒体创作者 | 短剧/解说/动画 | 高频出片，降低制作门槛 |
| 微短剧制作方 | 批量生产竖屏短剧 | 角色一致性，规模化产出 |
| 影视工作室 | 前期分镜预览 | 快速验证创意，节约实拍成本 |
| 营销机构 | 品牌系列广告 | 风格统一，快速迭代 |
| 教育机构 | 剧情化教学视频 | 场景复原，批量制作 |

### 1.3 核心用户旅程

```
用户输入剧本
    ↓
[Step 1] 角色与场景提取 ← 用户可编辑/自定义
    ↓
[Step 2] 风格识别与选择 ← 内置预设 + 用户调整
    ↓
[Step 3] 剧本优化（扩写/对白/节奏）
    ↓
[Step 4] 按时长分段切割
    ↓
[Step 5] 分段视频生成 ← 注入角色/环境/风格关键词
    ↓
[Step 6] 视频拼接 + 转场 + 空镜头
    ↓
[Step 7] 音频处理（BGM融合、错位拼接）
    ↓
[Step 8] 导出成片
```

### 1.4 产品原则

1. **一致性优先** — 角色外貌、环境氛围、视觉风格在所有分段中保持统一
2. **渐进式控制** — 默认全自动，每一步都允许用户介入微调
3. **非破坏性编辑** — 修改任一步骤可增量重新生成，无需从头开始
4. **所见即所得** — 每一步产出可预览，不是黑盒

---

## 二、功能设计

### 2.1 功能模块总览

```
┌─────────────────────────────────────────────────────┐
│                   InfiniteDream                      │
├──────────┬──────────┬──────────┬─────────────────────┤
│  输入层   │  处理层   │  生成层   │      输出层          │
├──────────┼──────────┼──────────┼─────────────────────┤
│ 剧本输入  │ 角色提取  │ 分段视频  │ 视频拼接             │
│ 角色编辑  │ 场景提取  │   生成   │ 转场/空镜头           │
│ 风格选择  │ 风格分析  │ 音频生成  │ 音频融合             │
│ 参数配置  │ 剧本优化  │          │ 导出                 │
│          │ 分段切割  │          │                     │
└──────────┴──────────┴──────────┴─────────────────────┘
```

### 2.2 模块详细设计

#### M1: 剧本输入（Script Input）

**功能描述**：接收用户剧本文本，支持任意长度。

- 输入方式：文本框直接输入、文件上传（.txt / .md / .docx / .fountain）、粘贴
- 支持多语言（中文、英文为主）
- 字数统计、预估时长显示
- 历史剧本管理（草稿箱）

**数据模型**：
```
Script {
  id: UUID
  title: String
  content: String          // 原始剧本文本
  language: "zh" | "en"
  estimated_duration_sec: u32
  created_at: DateTime
  updated_at: DateTime
}
```

#### M2: 角色与场景提取（Character & Scene Extraction）

**功能描述**：LLM 分析剧本，自动识别核心角色和场景环境。

- 角色提取：姓名、外貌描述、性格特征、服装、年龄
- 场景提取：地点、时间、氛围、关键物件
- 角色关系图谱（可视化）
- 用户可自定义：修改描述、上传参考图、添加/删除角色

**数据模型**：
```
Character {
  id: UUID
  script_id: UUID
  name: String
  description: String      // LLM生成的外貌描述
  appearance_keywords: Vec<String>  // 用于视频生成的关键词
  reference_images: Vec<ImageRef>   // 用户上传的参考图
  traits: Vec<String>      // 性格特征
  age_range: String
}

Scene {
  id: UUID
  script_id: UUID
  name: String
  description: String
  environment_keywords: Vec<String>  // 环境关键词
  reference_images: Vec<ImageRef>
  time_of_day: String      // "dawn" | "day" | "dusk" | "night"
  mood: String             // "tense" | "romantic" | "peaceful" ...
}
```

**LLM Prompt 策略**：
```
系统提示：你是一个专业的影视编剧助手。分析以下剧本，提取：
1. 所有角色（含外貌、服装、年龄、性格的详细描述）
2. 所有场景（含地点、时间、氛围、关键物件）
3. 角色之间的关系

输出格式：JSON
约束：外貌描述要具体到可用于AI图像生成的程度
```

#### M3: 风格识别与选择（Style Detection & Selection）

**功能描述**：自动识别剧本风格，提供预设风格库供用户选择或微调。

- 自动风格分析：LLM 基于剧本内容、语调、题材判断风格
- 预置风格库：
  - **写实电影**：高对比度、自然光影、35mm 电影质感
  - **甜宠**：柔和暖色调、梦幻滤镜、浅景深
  - **仙侠**：水墨风、飘逸粒子、云雾缭绕
  - **赛博朋克**：霓虹灯、雨夜、高饱和度蓝紫
  - **战争**：冷色调、硝烟、手持摇晃感
  - **日系动画**：赛璐璐风、明亮色彩、大眼角色
  - **复古胶片**：颗粒感、褪色、暗角
  - **纪录片**：自然色调、稳定画面、字幕叠加
- 自定义风格：用户可上传风格参考图、调节参数
- 风格参数维度：色温、饱和度、对比度、颗粒感、光影方向、镜头运动偏好

**数据模型**：
```
Style {
  id: UUID
  name: String
  description: String
  visual_keywords: Vec<String>     // 注入到视频生成prompt的关键词
  color_temperature: f32           // 色温 2000K-10000K
  saturation: f32                  // 0.0-2.0
  contrast: f32                    // 0.0-2.0
  grain: f32                       // 0.0-1.0
  lighting_direction: String       // "natural" | "dramatic" | "soft" | "neon"
  camera_motion: String            // "static" | "handheld" | "dolly" | "crane"
  reference_images: Vec<ImageRef>
  is_preset: bool
}
```

#### M4: 剧本优化（Script Enhancement）

**功能描述**：LLM 对剧本进行专业化优化。

- **扩展**：将简短大纲扩写为完整场景描述
- **对白生成**：为无对白的叙述段落自动生成符合角色性格的对白
- **节奏调优**：分析叙事节奏，在平淡处增加冲突、在高潮处延长
- **镜头语言标注**：自动添加镜头指示（特写、全景、推拉等）
- **Diff 预览**：优化前后对比，用户可逐条接受/拒绝修改

**数据模型**：
```
EnhancedScript {
  id: UUID
  script_id: UUID
  segments: Vec<ScriptSegment>
  total_duration_sec: u32
  enhancement_level: "light" | "moderate" | "heavy"
}

ScriptSegment {
  id: UUID
  sequence: u32
  scene_id: UUID
  content: String              // 场景描述 + 对白
  characters_present: Vec<UUID> // 出场角色ID
  camera_direction: String     // 镜头指示
  estimated_duration_sec: u32
  mood: String
}
```

#### M5: 分段切割（Segment Splitting）

**功能描述**：按指定目标时长将剧本切割为可独立生成的视频段。

- 输入：目标总时长、单段时长上限（受视频AI接口限制，通常 5-15 秒）
- 切割策略：
  - 按场景/段落自然分割
  - 确保每段有完整的叙事单元
  - 保留段间上下文（前一段的末帧描述 → 下一段的首帧提示）
- 段间衔接元数据：记录相邻段共享的角色、场景、动作连续性
- 用户可手动调整分割点

**数据模型**：
```
SegmentPlan {
  id: UUID
  enhanced_script_id: UUID
  target_total_duration_sec: u32
  max_segment_duration_sec: u32
  segments: Vec<VideoSegment>
}

VideoSegment {
  id: UUID
  sequence: u32
  script_segment_id: UUID
  duration_sec: f32
  
  // 生成 prompt 相关
  visual_prompt: String           // 视觉描述
  character_keywords: Vec<String> // 角色一致性关键词
  environment_keywords: Vec<String> // 环境一致性关键词
  style_keywords: Vec<String>     // 风格一致性关键词
  camera_motion: String           // 镜头运动
  
  // 衔接元数据
  prev_segment_end_description: Option<String>  // 上一段结尾画面描述
  next_segment_start_hint: Option<String>        // 下一段开头画面提示
  
  // 生成状态
  status: "pending" | "generating" | "completed" | "failed"
  video_path: Option<String>
  retry_count: u32
}
```

#### M6: 分段视频生成（Video Generation）

**功能描述**：调用视频 AI 接口，为每个分段生成视频片段。

- 核心策略：**每段 prompt 注入全局一致性关键词**
  - 角色关键词：`[Character: 林婉儿, 20岁女性, 长发及腰, 白色汉服, 柳叶眉]`
  - 环境关键词：`[Scene: 月下竹林, 雾气弥漫, 萤火虫, 石桥]`
  - 风格关键词：`[Style: 仙侠水墨风, 低饱和, 柔和光影, 飘逸粒子]`
- 支持多视频 AI 后端（适配器模式）：
  - Kling（可灵）
  - MiniMax（海螺）
  - Runway Gen-3/4
  - Pika
  - 自部署模型（CogVideoX 等）
- 并发控制：根据 API 配额自动调节并发数
- 失败重试 + 质量检测（可选：用视觉模型评分）
- 进度实时展示

**Prompt 模板**：
```
[Global Style] {style_keywords}
[Characters] {character_keywords_of_this_segment}
[Environment] {environment_keywords}
[Previous Frame Context] {prev_segment_end_description}
[Action] {visual_prompt}
[Camera] {camera_motion}
```

#### M7: 视频拼接与后期（Post-Production）

**功能描述**：将分段视频组装为完整长视频，添加转场和空镜头。

- **拼接**：按序列号顺序拼接所有分段视频
- **转场**：
  - 自动选择转场类型：淡入淡出、溶解、推拉、闪白、切黑
  - 基于场景变化程度选择：同场景用溶解，换场景用切黑+淡入
  - 转场时长可配置（默认 0.5-1.5 秒）
- **空镜头**：
  - 在场景切换处自动插入空镜头（环境远景、特写物件等）
  - 空镜头也通过视频 AI 生成，使用场景环境关键词
  - 用户可选择是否启用、可手动指定
- **字幕**：自动生成时间轴字幕（基于剧本对白）

#### M8: 音频处理（Audio Processing）

**功能描述**：提取、处理并融合分段间的音频。

- **BGM 生成**：调用音乐 AI（如 Suno / Udio）基于风格和情绪生成 BGM
- **音频提取**：从每个分段视频提取音轨
- **音频融合**：
  - 分段间 BGM 交叉淡化（crossfade）
  - 音乐复制 + 错位拼接：取前段末尾音乐复制到下段开头，形成连续感
  - 音量包络自动调节（对白处降低 BGM）
- **音效**：根据画面内容添加环境音效（可选）
- 使用 FFmpeg 进行底层音视频处理

#### M9: 导出（Export）

**功能描述**：输出最终视频文件。

- 输出格式：MP4（H.264/H.265）、MOV、WebM
- 分辨率：720p / 1080p / 4K
- 帧率：24fps / 30fps / 60fps
- 码率可配置
- 同时导出：字幕文件（SRT）、项目文件（可重新编辑）
- 导出预览：低质量快速预览 → 高质量最终渲染

---

## 三、架构设计

### 3.1 技术选型

| 层级 | 技术选择 | 理由 |
|------|---------|------|
| 语言 | Python | AI/ML 生态最成熟，FFmpeg 绑定完善 |
| Web 框架 | FastAPI | 异步高性能，适合长任务 + WebSocket |
| 前端 | React + TypeScript | 复杂交互 UI（时间轴编辑器） |
| 任务队列 | Celery + Redis | 视频生成任务异步执行、进度追踪 |
| 存储 | PostgreSQL + S3/MinIO | 项目元数据 + 视频/图片资产 |
| 音视频处理 | FFmpeg (ffmpeg-python) | 转码、拼接、转场、音频处理 |
| LLM | OpenAI GPT-4o / Claude | 剧本分析、角色提取、风格识别 |
| 视频 AI | 可灵/MiniMax/Runway (适配器) | 分段视频生成 |
| 音乐 AI | Suno / Udio API | BGM 生成 |

### 3.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ 剧本编辑  │ │ 角色管理  │ │ 风格面板  │ │ 时间轴预览/编辑   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                     API Layer (FastAPI)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ /scripts │ │ /projects│ │ /generate│ │ /ws/progress     │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Core Pipeline Engine                          │
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │ ScriptParser │──▶│ Extractor   │──▶│ StyleAnalyzer       │   │
│  │ (剧本解析)   │   │ (角色/场景)  │   │ (风格识别)          │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
│         │                                       │               │
│         ▼                                       ▼               │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │ Enhancer    │──▶│ Splitter    │──▶│ PromptBuilder       │   │
│  │ (剧本优化)   │   │ (分段切割)   │   │ (Prompt组装+关键词)  │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
│                                              │                  │
│                                              ▼                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Video Generation Orchestrator               │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │    │
│  │  │ Kling    │  │ MiniMax  │  │ Runway   │  ...adapters │    │
│  │  └──────────┘  └──────────┘  └──────────┘              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │ Compositor  │──▶│ AudioMixer  │──▶│ Exporter            │   │
│  │ (拼接/转场)  │   │ (音频处理)   │   │ (导出)              │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Infrastructure Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │PostgreSQL│  │  Redis   │  │S3/MinIO  │  │ Celery Workers│   │
│  │ (元数据)  │  │ (队列)   │  │ (资产)   │  │ (任务执行)    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 核心模块设计

#### 3.3.1 Pipeline Engine（流水线引擎）

整个视频生产流程抽象为一条有向无环图（DAG）流水线：

```python
# 流水线定义
class Pipeline:
    """视频生产流水线"""
    
    def __init__(self, project: Project):
        self.project = project
        self.stages = [
            ScriptParseStage(),
            CharacterExtractionStage(),
            SceneExtractionStage(),
            StyleAnalysisStage(),
            ScriptEnhancementStage(),
            SegmentSplitStage(),
            PromptBuildStage(),
            VideoGenerationStage(),    # 可并行
            CompositionStage(),
            AudioProcessingStage(),
            ExportStage(),
        ]
    
    async def run(self, from_stage: int = 0):
        """从指定阶段开始执行（支持中断续跑）"""
        for i, stage in enumerate(self.stages[from_stage:], start=from_stage):
            self.project.current_stage = i
            await stage.execute(self.project)
            await self.save_checkpoint(i)
    
    async def rerun_from(self, stage: int):
        """从某个阶段重跑（非破坏性编辑）"""
        await self.invalidate_downstream(stage)
        await self.run(from_stage=stage)
```

每个 Stage 是独立的处理单元：
```python
class Stage(ABC):
    @abstractmethod
    async def execute(self, project: Project) -> None: ...
    
    @abstractmethod
    def can_skip(self, project: Project) -> bool: ...
```

#### 3.3.2 Video Generation Orchestrator（视频生成编排器）

```python
class VideoOrchestrator:
    """管理分段视频的并发生成"""
    
    def __init__(self, adapter: VideoAPIAdapter, max_concurrency: int = 3):
        self.adapter = adapter
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = 3
    
    async def generate_all(self, segments: list[VideoSegment]) -> list[str]:
        """并发生成所有分段视频，返回视频文件路径列表"""
        tasks = [self._generate_one(seg) for seg in segments]
        return await asyncio.gather(*tasks)
    
    async def _generate_one(self, segment: VideoSegment) -> str:
        async with self.semaphore:
            for attempt in range(self.max_retries):
                try:
                    result = await self.adapter.generate(
                        prompt=segment.visual_prompt,
                        duration=segment.duration_sec,
                        character_keywords=segment.character_keywords,
                        environment_keywords=segment.environment_keywords,
                        style_keywords=segment.style_keywords,
                    )
                    return result.video_path
                except (APIError, TimeoutError) as e:
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
```

#### 3.3.3 Video API Adapter（视频 AI 适配器）

```python
class VideoAPIAdapter(ABC):
    """视频生成API抽象接口"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        duration: float,
        character_keywords: list[str],
        environment_keywords: list[str],
        style_keywords: list[str],
        reference_image: Optional[str] = None,
    ) -> GenerationResult: ...
    
    @abstractmethod
    async def check_status(self, task_id: str) -> TaskStatus: ...


class KlingAdapter(VideoAPIAdapter):
    """可灵视频API适配器"""
    ...

class MiniMaxAdapter(VideoAPIAdapter):
    """MiniMax/海螺视频API适配器"""
    ...

class RunwayAdapter(VideoAPIAdapter):
    """Runway Gen-3/4 适配器"""
    ...
```

#### 3.3.4 Prompt Builder（提示词组装器）

确保一致性的核心模块：

```python
class PromptBuilder:
    """为每个分段构建注入一致性关键词的完整 prompt"""
    
    def build(self, segment: VideoSegment, project: Project) -> str:
        parts = []
        
        # 全局风格
        style = project.style
        parts.append(f"[Style] {', '.join(style.visual_keywords)}")
        parts.append(f"[Lighting] {style.lighting_direction}")
        parts.append(f"[Camera] {style.camera_motion}")
        
        # 角色一致性关键词
        for char_id in segment.characters_present:
            char = project.get_character(char_id)
            parts.append(
                f"[Character: {char.name}] {', '.join(char.appearance_keywords)}"
            )
        
        # 环境一致性关键词
        scene = project.get_scene(segment.scene_id)
        parts.append(f"[Environment] {', '.join(scene.environment_keywords)}")
        
        # 上下文衔接
        if segment.prev_segment_end_description:
            parts.append(
                f"[Continue from] {segment.prev_segment_end_description}"
            )
        
        # 当前段的具体动作描述
        parts.append(f"[Action] {segment.visual_prompt}")
        
        return "\n".join(parts)
```

#### 3.3.5 Compositor（合成器）

```python
class Compositor:
    """视频拼接、转场、空镜头处理"""
    
    def compose(
        self,
        segments: list[RenderedSegment],
        transitions: list[Transition],
        b_rolls: list[BRoll],
    ) -> str:
        """
        1. 按序列号排列分段视频
        2. 在场景切换处插入空镜头
        3. 添加转场效果
        4. 输出拼接后的视频文件路径
        """
        # 使用 FFmpeg filter_complex 实现
        ...
    
    def select_transition(
        self, prev_segment: VideoSegment, next_segment: VideoSegment
    ) -> Transition:
        """基于场景变化程度自动选择转场类型"""
        if prev_segment.scene_id == next_segment.scene_id:
            return Transition(type="dissolve", duration=0.5)
        else:
            return Transition(type="fade_black", duration=1.0)
```

#### 3.3.6 AudioMixer（音频混合器）

```python
class AudioMixer:
    """音频提取、BGM融合、错位拼接"""
    
    def process(self, video_path: str, segments: list[RenderedSegment]) -> str:
        """
        1. 提取各段音频
        2. BGM 交叉淡化
        3. 音乐复制+错位：取前段末尾N秒音乐，复制到下段开头，做crossfade
        4. 对白处自动降低BGM音量
        5. 合并输出
        """
        ...
    
    def crossfade_bgm(
        self, audio_a: str, audio_b: str, overlap_sec: float = 2.0
    ) -> str:
        """两段音频交叉淡化"""
        # FFmpeg acrossfade filter
        ...
    
    def shift_and_blend(
        self, audio: str, shift_ms: int, blend_duration_sec: float
    ) -> str:
        """音乐复制+错位拼接，实现分段间 BGM 自然过渡"""
        # 取前段末尾 N 秒音乐 → 复制到下段开头 → crossfade 融合
        ...
    
    def duck_bgm_under_dialogue(
        self, bgm: str, dialogue: str, duck_db: float = -12.0
    ) -> str:
        """对白处自动降低 BGM 音量（侧链压缩/ducking）"""
        # FFmpeg sidechaincompress filter
        ...
```

### 3.4 项目目录结构

```
InfiniteDream/
├── DESIGN.md                    # 本文档
├── README.md                    # 项目介绍
├── pyproject.toml               # Python 项目配置
├── docker-compose.yml           # 本地开发环境
│
├── src/
│   └── infinite_dream/
│       ├── __init__.py
│       ├── main.py              # FastAPI 入口
│       ├── config.py            # 配置管理
│       │
│       ├── api/                 # HTTP API 层
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── scripts.py   # 剧本 CRUD
│       │   │   ├── projects.py  # 项目管理
│       │   │   ├── generate.py  # 生成控制
│       │   │   └── assets.py    # 资产上传/下载
│       │   └── websocket.py     # 进度推送
│       │
│       ├── core/                # 核心业务逻辑
│       │   ├── __init__.py
│       │   ├── pipeline.py      # 流水线引擎
│       │   ├── parser.py        # 剧本解析
│       │   ├── extractor.py     # 角色/场景提取
│       │   ├── style.py         # 风格分析
│       │   ├── enhancer.py      # 剧本优化
│       │   ├── splitter.py      # 分段切割
│       │   ├── prompt.py        # Prompt 组装
│       │   ├── orchestrator.py  # 视频生成编排
│       │   ├── compositor.py    # 视频拼接/转场
│       │   ├── audio.py         # 音频处理
│       │   └── exporter.py      # 导出
│       │
│       ├── adapters/            # 外部服务适配器
│       │   ├── __init__.py
│       │   ├── base.py          # 适配器抽象基类
│       │   ├── kling.py         # 可灵 API
│       │   ├── minimax.py       # MiniMax/海螺
│       │   ├── runway.py        # Runway
│       │   ├── llm.py           # LLM 适配器（GPT-4o/Claude）
│       │   └── music.py         # 音乐 AI 适配器
│       │
│       ├── models/              # 数据模型
│       │   ├── __init__.py
│       │   ├── script.py        # Script, EnhancedScript
│       │   ├── character.py     # Character
│       │   ├── scene.py         # Scene
│       │   ├── style.py         # Style
│       │   ├── segment.py       # VideoSegment, SegmentPlan
│       │   └── project.py       # Project（聚合根）
│       │
│       ├── db/                  # 数据库
│       │   ├── __init__.py
│       │   ├── session.py       # SQLAlchemy session
│       │   └── migrations/      # Alembic 迁移
│       │
│       └── utils/               # 工具函数
│           ├── __init__.py
│           ├── ffmpeg.py        # FFmpeg 封装
│           └── storage.py       # S3/本地文件存储
│
├── tests/
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── fixtures/                # 测试数据（示例剧本等）
│
└── frontend/                    # React 前端（后续阶段）
    ├── package.json
    └── src/
```

### 3.5 数据流

```
               输入                    处理                      输出
          ┌──────────┐         ┌────────────────┐        ┌──────────────┐
          │          │         │                │        │              │
 用户剧本 ──▶│ Script   │────────▶│  LLM 分析      │───────▶│ Characters[] │
          │          │         │  (GPT-4o)      │        │ Scenes[]     │
          └──────────┘         └────────────────┘        │ Style        │
                                                         └──────┬───────┘
                                                                │
                                                         ┌──────▼───────┐
                                                         │ EnhancedScript│
                                                         │ (优化后剧本)   │
                                                         └──────┬───────┘
                                                                │
                                                         ┌──────▼───────┐
                                                         │ SegmentPlan  │
                                                         │ N个分段       │
                                                         └──────┬───────┘
                                                                │
                               ┌────────────────┐               │
                               │                │        ┌──────▼───────┐
              每段注入一致性关键词 │  Video AI API  │◀───────│ PromptBuilder │
              (角色+环境+风格)   │  (可灵/MiniMax) │        │ (组装Prompt)  │
                               └───────┬────────┘        └──────────────┘
                                       │
                                       │ N 个分段视频
                                       │
                               ┌───────▼────────┐
                               │  Compositor    │
                               │  + AudioMixer  │──────▶ 最终长视频 .mp4
                               │  + Exporter    │
                               └────────────────┘
```

### 3.6 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 一致性保障方式 | Prompt 关键词注入 | 不依赖特定模型能力，通用性最强；后续可叠加 LoRA/IP-Adapter |
| 视频 AI 集成 | 适配器模式 | 视频 AI 市场变化快，需要快速切换/对比不同供应商 |
| 流水线执行 | 异步 DAG + 检查点 | 支持中断续跑、从任意阶段重跑、非破坏性编辑 |
| 音视频处理 | FFmpeg | 工业标准，性能好，功能全，免费 |
| 并发策略 | Semaphore 限流 | 视频 AI API 有配额限制，需要精确控制并发数 |
| 存储 | 本地优先 + S3 可选 | MVP 阶段简化部署，后续可切换到云存储 |

### 3.7 一致性保障策略（核心难点）

这是整个系统最核心的技术难点。分三层保障：

**第一层：Prompt 级一致性**
- 每个分段 prompt 强制注入全局角色/环境/风格关键词
- 关键词由 LLM 在提取阶段生成，经用户确认后固化
- 关键词格式标准化，适配不同视频 AI 的 prompt 规范

**第二层：上下文衔接**
- 每个分段记录前一段的末帧描述（由视觉模型或 LLM 生成）
- 下一段的 prompt 开头包含"续接上一帧"的描述
- 确保动作、姿态、光线方向的连续性

**第三层：参考图锚定（进阶）**
- 角色参考图作为 image-to-video 的 reference 输入
- 支持 IP-Adapter / LoRA 等技术强化角色固定
- 场景参考图作为环境锚点

---

## 四、开发计划

### Phase 0：项目骨架（1 周）
- Python 项目初始化（pyproject.toml, src 结构）
- 基础数据模型定义
- 配置管理（API Key 等）
- CLI 入口（先做 CLI，后做 Web UI）

### Phase 1：核心流水线 - 文本处理（2 周）
- M1: 剧本输入与解析
- M2: 角色与场景提取（LLM）
- M3: 风格识别与选择
- M4: 剧本优化
- M5: 分段切割
- M6: Prompt 组装（不调用视频 AI，只输出 prompt）

### Phase 2：视频生成（2 周）
- 视频 AI 适配器（先接一家，如可灵）
- 视频生成编排器（并发 + 重试）
- 分段视频生成端到端打通

### Phase 3：后期合成（1 周）
- M7: 视频拼接 + 转场 + 空镜头
- M8: 音频处理（BGM 融合、错位拼接）
- M9: 导出

### Phase 4：Web UI（2 周）
- React 前端：剧本编辑器、角色管理、风格面板、时间轴预览
- WebSocket 进度推送
- 项目管理界面

### Phase 5：优化与扩展（持续）
- 接入更多视频 AI（MiniMax、Runway 等）
- LoRA / IP-Adapter 角色锁定
- 质量评估自动化
- 性能优化（缓存、增量生成）