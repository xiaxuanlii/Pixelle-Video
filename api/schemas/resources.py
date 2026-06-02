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
Resource discovery API schemas

此模块定义了用于查询系统内部资源的 API 数据模型，
例如获取所有可用的工作流、HTML 画面排版模板以及背景音乐列表，供前端生成配置表单时使用。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class WorkflowInfo(BaseModel):
    """
    工作流信息模型。
    
    描述了单个配置好的 AI 生成工作流（例如 TTS、生图、生视频的 JSON 配置文件）。
    """
    name: str = Field(..., description="工作流的原始文件名（如 'tts_edge.json'）")
    display_name: str = Field(..., description="在前端 UI 上展示的友好名称（通常附带来源标识）")
    source: str = Field(..., description="工作流文件的来源分类（如 'runninghub' 或 'selfhost'）")
    path: str = Field(..., description="工作流文件在服务器上的绝对或相对路径")
    key: str = Field(..., description="用于标识该工作流的唯一键名，格式通常为 'source/name'")
    workflow_id: Optional[str] = Field(None, description="如果来源是 RunningHub，此处为其对应的工作流 ID（可选）")


class WorkflowListResponse(BaseModel):
    """
    工作流列表响应模型。
    """
    success: bool = True
    message: str = "Success"
    workflows: List[WorkflowInfo] = Field(..., description="系统当前扫描到的所有可用工作流列表")


class TemplateInfo(BaseModel):
    """
    HTML 画面排版模板信息模型。
    
    描述了单个可用于渲染视频帧画面的 HTML 模板及其尺寸元数据。
    """
    name: str = Field(..., description="模板的文件名称（如 'image_default.html'）")
    display_name: str = Field(..., description="供前端展示的模板友好名称")
    size: str = Field(..., description="模板所在目录代表的尺寸规格（如 '1080x1920'）")
    width: int = Field(..., description="该模板对应的画面宽度（像素）")
    height: int = Field(..., description="该模板对应的画面高度（像素）")
    orientation: str = Field(..., description="画面方向标识（'portrait' 竖屏 / 'landscape' 横屏 / 'square' 方屏）")
    path: str = Field(..., description="模板文件在服务器上的完整路径")
    key: str = Field(..., description="用于请求渲染该模板的唯一标识，格式为 'size/name'")


class TemplateListResponse(BaseModel):
    """
    模板列表响应模型。
    """
    success: bool = True
    message: str = "Success"
    templates: List[TemplateInfo] = Field(..., description="系统当前支持的所有排版模板列表")


class BGMInfo(BaseModel):
    """
    背景音乐信息模型。
    
    描述了系统中可用的单个背景音乐文件。
    """
    name: str = Field(..., description="音频文件名称（如 'default.mp3'）")
    path: str = Field(..., description="音频文件的服务器路径")
    source: str = Field(..., description="音频来源（如 'default' 系统自带 或 'custom' 用户自定义）")


class BGMListResponse(BaseModel):
    """
    背景音乐列表响应模型。
    """
    success: bool = True
    message: str = "Success"
    bgm_files: List[BGMInfo] = Field(..., description="当前可供选择的所有背景音乐文件列表")

