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
Frame/Template rendering API schemas

此模块定义了基于 HTML 模板进行帧（Frame）渲染及模板参数解析的 API 接口数据模型。
常用于在视频生成前，对包含文本、图像和排版的单个画面进行静态截图预览。
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class FrameRenderRequest(BaseModel):
    """
    画面帧渲染请求模型。
    
    请求后端加载指定的 HTML 模板，注入文本和图像数据，
    然后通过无头浏览器（如 Playwright）将其渲染并截图保存为图像。
    """
    template: str = Field(
        ..., 
        description="需要渲染的 HTML 模板路径或名称（例如：'1080x1920/image_default.html'）。如果仅提供文件名（如 'image_default.html'），将尝试使用默认分辨率下的同名模板。"
    )
    title: Optional[str] = Field(None, description="需要注入到模板中的主标题文本（可选，取决于模板设计）")
    text: str = Field(..., description="需要注入到模板中的核心正文/旁白内容")
    image: Optional[str] = Field(None, description="需要注入到模板中的背景图或配图路径/URL（可选）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template": "1080x1920/image_default.html",
                "title": "示例标题",
                "text": "这是一段用于画面帧渲染测试的示例文本。",
                "image": "resources/example.png"
            }
        }


class FrameRenderResponse(BaseModel):
    """
    画面帧渲染响应模型。
    
    返回生成的截图文件在服务器上的访问路径及其分辨率尺寸。
    """
    success: bool = True
    message: str = "Success"
    frame_path: str = Field(..., description="渲染完成后的图像文件（截图）相对路径或访问 URL")
    width: int = Field(..., description="最终生成的图像宽度（像素）")
    height: int = Field(..., description="最终生成的图像高度（像素）")


class TemplateParamConfig(BaseModel):
    """
    单个模板自定义参数的配置模型。
    
    用于向前端描述 HTML 模板暴露出来的自定义修改项
    （这些参数通常通过解析 HTML 模板内部的特殊 meta 标签提取）。
    """
    type: str = Field(..., description="前端输入控件的建议类型，例如：'text'（文本框）, 'number'（数字框）, 'color'（取色器）, 'bool'（开关）")
    default: Any = Field(..., description="该参数在未显式传递时的默认值")
    label: str = Field(..., description="在前端 UI 上展示的参数中文标签或说明文字")


class TemplateParamsResponse(BaseModel):
    """
    模板参数查询响应模型。
    
    用于返回某个 HTML 模板所定义的预期媒体尺寸及其支持的所有自定义参数。
    """
    success: bool = True
    message: str = "Success"
    template: str = Field(..., description="查询的模板文件路径")
    media_width: int = Field(..., description="从该模板的 meta 标签中提取出的内嵌媒体（如视频/图片占位符）预期宽度")
    media_height: int = Field(..., description="从该模板的 meta 标签中提取出的内嵌媒体预期高度")
    params: Dict[str, TemplateParamConfig] = Field(
        default_factory=dict,
        description="模板支持的所有自定义参数字典，键为参数名（如 'accent_color'），值为其配置和说明（TemplateParamConfig 对象）。"
    )

 )

