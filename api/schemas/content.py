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
Content generation API schemas

此模块定义了内容生成（例如旁白拆分生成、画面提示词生成、标题生成）API 的请求与响应数据结构。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Narration Generation / 旁白生成
# ============================================================================

class NarrationGenerateRequest(BaseModel):
    """
    旁白生成请求模型。
    
    请求 LLM 根据提供的源文本生成用于视频各分镜的旁白文本。
    """
    text: str = Field(..., description="用于生成旁白的原始长文本内容")
    n_scenes: int = Field(5, ge=1, le=20, description="期望拆分生成的旁白/分镜总数")
    min_words: int = Field(5, ge=1, le=100, description="每个分镜旁白的最小字数限制")
    max_words: int = Field(20, ge=1, le=200, description="每个分镜旁白的最大字数限制")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "原子习惯告诉我们，微小的改变随着时间的推移，能产生显著的效果。",
                "n_scenes": 5,
                "min_words": 5,
                "max_words": 20
            }
        }


class NarrationGenerateResponse(BaseModel):
    """
    旁白生成响应模型。
    """
    success: bool = True
    message: str = "Success"
    narrations: List[str] = Field(..., description="生成的旁白文本列表（每个元素对应一个分镜）")


# ============================================================================
# Image Prompt Generation / 画面提示词生成
# ============================================================================

class ImagePromptGenerateRequest(BaseModel):
    """
    画面提示词生成请求模型。
    
    请求 LLM 根据已生成的旁白列表，为每个分镜生成对应的 AI 绘图提示词（Prompt）。
    """
    narrations: List[str] = Field(..., description="已拆分的旁白文本列表")
    min_words: int = Field(30, ge=10, le=100, description="每个画面提示词的最小字数限制")
    max_words: int = Field(60, ge=10, le=200, description="每个画面提示词的最大字数限制")
    
    class Config:
        json_schema_extra = {
            "example": {
                "narrations": [
                    "微小的习惯随着时间推移产生复利效应",
                    "关注构建系统，而不是单纯设定目标"
                ],
                "min_words": 30,
                "max_words": 60
            }
        }


class ImagePromptGenerateResponse(BaseModel):
    """
    画面提示词生成响应模型。
    """
    success: bool = True
    message: str = "Success"
    image_prompts: List[str] = Field(..., description="生成的画面提示词列表（与请求的旁白列表一一对应）")


# ============================================================================
# Title Generation / 标题生成
# ============================================================================

class TitleGenerateRequest(BaseModel):
    """
    标题生成请求模型。
    
    请求 LLM 根据源文本提炼或生成具有吸引力的视频标题。
    """
    text: str = Field(..., description="用于提取标题的源文本内容")
    style: Optional[str] = Field(None, description="标题风格（例如：'engaging' 吸引人的, 'formal' 正式的）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "原子习惯告诉我们，微小的改变随着时间的推移，能产生显著的效果。",
                "style": "engaging"
            }
        }


class TitleGenerateResponse(BaseModel):
    """
    标题生成响应模型。
    """
    success: bool = True
    message: str = "Success"
    title: str = Field(..., description="生成的精炼标题文本")

