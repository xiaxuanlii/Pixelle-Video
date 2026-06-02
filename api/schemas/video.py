# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Video generation API schemas

此模块定义了视频生成 API 接口（`/api/video`）所使用的请求和响应数据结构。
包含同步生成和异步任务生成的参数定义。
"""

from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class VideoGenerateRequest(BaseModel):
    """
    视频生成请求模型。
    
    聚合了从文本到最终视频合成所需的所有配置参数，包括内容生成模式、
    LLM 控制参数、TTS 语音参数、视觉模板参数以及背景音乐设置等。
    """
    
    # === Input / 输入源 ===
    text: str = Field(..., description="用于生成视频的源文本内容（可以是文章片段、提示词或完整剧本）")
    
    # === Processing Mode / 处理模式 ===
    mode: Literal["generate", "fixed"] = Field(
        "generate",
        description="处理模式：'generate' (由 AI 根据源文本自动生成分镜旁白和画面提示词) 或 'fixed' (不使用 AI 改写，直接将源文本逐句作为旁白)"
    )
    
    # === Optional Title / 可选标题 ===
    title: Optional[str] = Field(None, description="视频标题（如果未提供，系统将调用 LLM 自动提取或生成）")
    
    # === Basic Config / 基础配置 ===
    n_scenes: Optional[int] = Field(5, ge=1, le=20, description="预期生成的分镜数量（仅在 'generate' 模式下生效，'fixed' 模式下将被忽略）")
    
    # === TTS Parameters / 文本转语音(TTS)参数 ===
    tts_workflow: Optional[str] = Field(
        None, 
        description="TTS 工作流的标识符（例如：'runninghub/tts_edge.json'）。若未指定，将使用系统默认配置的工作流。"
    )
    ref_audio: Optional[str] = Field(
        None, 
        description="用于声音克隆的参考音频文件路径（可选，部分高级 TTS 工作流支持）"
    )
    voice_id: Optional[str] = Field(
        None, 
        description="(已废弃) 兼容旧版逻辑的 TTS 音色 ID"
    )
    
    # === LLM Parameters / 语言模型生成控制参数 ===
    min_narration_words: int = Field(5, ge=1, le=100, description="每个分镜旁白的最小字数限制")
    max_narration_words: int = Field(20, ge=1, le=200, description="每个分镜旁白的最大字数限制")
    min_image_prompt_words: int = Field(30, ge=10, le=100, description="每个分镜画面提示词的最小字数限制")
    max_image_prompt_words: int = Field(60, ge=10, le=200, description="每个分镜画面提示词的最大字数限制")
    
    # === Media Parameters / 媒体生成参数 ===
    # 注：media_width 和 media_height 通常通过解析所选 HTML 模板的 meta 标签自动确定
    media_workflow: Optional[str] = Field(None, description="自定义的底层媒体生成工作流（如 ComfyUI 的生图或生视频工作流路径）")
    
    # === Video Parameters / 视频合成参数 ===
    video_fps: int = Field(30, ge=15, le=60, description="最终合成视频的帧率 (FPS)")
    
    # === Frame Template / 画面排版模板 ===
    frame_template: Optional[str] = Field(
        None, 
        description="HTML 排版模板的相对路径（例如：'1080x1920/image_default.html'）。系统会通过该模板的 meta 标签自动确定视频的宽高尺寸。"
    )
    
    # === Template Custom Parameters / 模板自定义参数 ===
    template_params: Optional[Dict[str, Any]] = Field(
        None,
        description="传递给 HTML 模板的自定义渲染参数（例如：{'accent_color': '#ff0000', 'background': 'url'}）。"
                    "具体可用参数取决于所选模板。可通过调用 GET /api/templates/{template_path}/params 接口发现。"
    )
    
    # === Image Style / 视觉风格控制 ===
    prompt_prefix: Optional[str] = Field(None, description="附加到所有分镜画面提示词之前的全局风格前缀修饰语")
    
    # === BGM / 背景音乐参数 ===
    bgm_path: Optional[str] = Field(None, description="要混入视频的背景音乐文件路径")
    bgm_volume: float = Field(0.3, ge=0.0, le=1.0, description="背景音乐的相对音量大小 (0.0-1.0)")
    
    class Config:
        """为接口文档提供示例输入"""
        json_schema_extra = {
            "example": {
                "text": "原子习惯告诉我们，微小的改变随着时间的推移，能产生显著的效果。",
                "mode": "generate",
                "n_scenes": 5,
                "frame_template": "1080x1920/image_default.html",
                "template_params": {
                    "accent_color": "#3498db",
                    "background": "https://example.com/custom-bg.jpg"
                },
                "title": "原子习惯的力量"
            }
        }


class VideoGenerateResponse(BaseModel):
    """
    同步视频生成响应模型。
    
    当客户端调用同步视频生成接口时，系统会在生成完毕后直接返回此结构。
    """
    success: bool = True     # 请求是否成功
    message: str = "Success" # 响应消息
    video_url: str = Field(..., description="生成视频的访问或下载 URL")
    duration: float = Field(..., description="视频的总时长（秒）")
    file_size: int = Field(..., description="视频文件的字节大小")


class VideoGenerateAsyncResponse(BaseModel):
    """
    异步视频生成响应模型。
    
    当客户端调用异步视频生成接口时，系统会立即返回一个任务 ID，
    客户端需使用此任务 ID 轮询进度。
    """
    success: bool = True                    # 任务下发是否成功
    message: str = "Task created successfully" # 响应消息
    task_id: str = Field(..., description="用于追踪进度的异步任务 ID")

