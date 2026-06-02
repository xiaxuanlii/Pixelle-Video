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
Frame/Template rendering endpoints

此模块定义了与 HTML 模板渲染相关的 API 路由端点。
主要用于将独立的 HTML 模板结合图文数据渲染成单张图片（常用于前端效果预览），
以及解析模板内部支持的自定义注入参数。
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.frame import FrameRenderRequest, FrameRenderResponse, TemplateParamsResponse
from pixelle_video.services.frame_html import HTMLFrameGenerator
from pixelle_video.utils.template_util import parse_template_size, resolve_template_path

# 创建带有 "/frame" 前缀的 APIRouter，并在 Swagger 中归类为 "Frame Rendering"
router = APIRouter(prefix="/frame", tags=["Frame Rendering"])


@router.post("/render", response_model=FrameRenderResponse)
async def render_frame(
    request: FrameRenderRequest,
    pixelle_video: PixelleVideoDep
):
    """
    单帧画面渲染端点。
    
    使用底层系统（如无头浏览器 Playwright）将指定的 HTML 模板、标题、正文文本和背景图像组合起来，
    截图生成一张静态画面。此接口非常适合用于在前端向用户提供“所见即所得”的排版预览功能。
    
    请求参数说明：
    - **template**: 要使用的 HTML 模板标识或路径（例如：'1080x1920/image_default.html'）。
    - **title**: (可选) 注入到画面中的主标题文本。
    - **text**: 注入到画面中的核心正文/旁白内容。
    - **image**: (可选) 注入到画面的背景图或配图路径（支持本地路径或网络 URL）。
    
    返回：
        FrameRenderResponse: 包含生成的截图文件相对路径以及实际画面的宽高像素。
    
    请求示例:
    ```json
    {
        "template": "1080x1920/modern.html",
        "title": "欢迎",
        "text": "这是一个带有自定义样式的精美排版画面",
        "image": "resources/example.png"
    }
    ```
    """
    try:
        logger.info(f"Frame render request: template={request.template}")
        
        # Resolve template path (returns absolute path with "templates/" or "data/templates/" prefix)
        # 解析模板真实路径，自动在默认目录和自定义数据目录中寻找
        template_path = resolve_template_path(request.template)
        
        # Parse template size / 从模板所在目录名（如 '1080x1920'）中解析最终视频帧的尺寸
        width, height = parse_template_size(template_path)
        
        # Create HTML frame generator / 初始化核心的 HTML 渲染截帧器
        generator = HTMLFrameGenerator(template_path)
        
        # Generate frame / 执行渲染并保存为图像
        frame_path = await generator.generate_frame(
            title=request.title,
            text=request.text,
            image=request.image
        )
        
        return FrameRenderResponse(
            frame_path=frame_path,
            width=width,
            height=height
        )
        
    except Exception as e:
        logger.error(f"Frame render error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/params", response_model=TemplateParamsResponse)
async def get_template_params(
    template: str
):
    """
    获取指定 HTML 模板的自定义参数端点。
    
    解析指定的 HTML 模板文件，提取内部定义的特殊参数标签。这些参数使得模板可以在生成视频时
    接受动态变量注入（例如动态修改主色调、背景图或特定文本）。
    这些参数可以通过在 `/api/video/generate` 接口的 `template_params` 字段中传入。
    
    模板参数定义语法: `{{param_name:type=default}}`
    
    支持的参数类型 (type):
    - `text`: 字符串输入框
    - `number`: 数字输入框
    - `color`: 颜色选择器（十六进制格式，如 #ff0000）
    - `bool`: 布尔开关/复选框
    
    HTML 模板语法示例:
    ```html
    <div style="color: {{accent_color:color=#ff0000}}">
        {{custom_text:text=Hello World}}
    </div>
    ```
    
    Args:
        template: 模板的相对路径标识（例如：'1080x1920/image_default.html'）
    
    Returns:
        TemplateParamsResponse: 包含模板允许定制的所有参数及其类型、默认值和前端展示标签。
    """
    try:
        logger.info(f"Get template params: {template}")
        
        # Resolve template path / 获取文件的真实本地路径
        template_path = resolve_template_path(template)
        
        # Create generator and parse parameters / 初始化渲染器并解析模板内容
        generator = HTMLFrameGenerator(template_path)
        params = generator.parse_template_parameters()
        
        # 获取该模板要求的内嵌媒体（视频/图片组件）预期分辨率
        media_width, media_height = generator.get_media_size()
        
        return TemplateParamsResponse(
            template=template,
            media_width=media_width,
            media_height=media_height,
            params=params
        )
        
    except FileNotFoundError:
        # 模板文件不存在则抛出 404
        raise HTTPException(status_code=404, detail=f"Template not found: {template}")
    except Exception as e:
        logger.error(f"Get template params error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

