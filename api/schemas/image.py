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
Image generation API schemas

此模块定义了图像生成（`/api/image`）接口所使用的请求和响应数据模型，
通常作为视频生成流程中获取分镜画面的基础。
"""

from typing import Optional
from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """
    图像生成请求模型。
    
    请求底层 AI 绘图服务（如基于 ComfyUI 包装的后端接口）根据文本提示词生成图像。
    """
    prompt: str = Field(..., description="用于生成图像的具体提示词（Prompt）")
    width: int = Field(1024, ge=512, le=2048, description="生成图像的宽度（像素），建议区间 512-2048")
    height: int = Field(1024, ge=512, le=2048, description="生成图像的高度（像素），建议区间 512-2048")
    workflow: Optional[str] = Field(None, description="自定义 ComfyUI 工作流文件的名称或路径（可选）。如果为空，将使用默认配置。")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "日落时分宁静的山水风景，照片级真实风格",
                "width": 1024,
                "height": 1024
            }
        }


class ImageGenerateResponse(BaseModel):
    """
    图像生成响应模型。
    
    返回生成的图像文件在服务器上的访问路径或相对路径。
    """
    success: bool = True
    message: str = "Success"
    image_path: str = Field(..., description="已生成的图像文件的相对路径或可访问的 URL 链接")

