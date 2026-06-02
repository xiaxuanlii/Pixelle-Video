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
Image generation endpoints

此模块定义了与图像生成服务交互的 API 路由端点。
主要暴露了 `/api/image/generate` 接口，允许前端请求底层绘画引擎（如基于 ComfyUI 的后台）生成图片。
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.image import ImageGenerateRequest, ImageGenerateResponse

# 创建带有 "/image" 前缀的 APIRouter，并在 Swagger 中归类为 "Basic Services"
router = APIRouter(prefix="/image", tags=["Basic Services"])


@router.post("/generate", response_model=ImageGenerateResponse)
async def image_generate(
    request: ImageGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    图像生成端点。
    
    使用底层的 ComfyKit/ComfyUI 媒体生成服务，根据文本提示词生成图像。
    
    请求参数说明：
    - **prompt**: 描述图像内容的提示词。
    - **width**: 图像的宽度（允许范围：512-2048 像素）。
    - **height**: 图像的高度（允许范围：512-2048 像素）。
    - **workflow**: (可选) 自定义的 ComfyUI 图像生成工作流名称或路径。
    
    返回：
        ImageGenerateResponse: 包含生成的图像文件的可访问路径/URL。
    
    注意：此端点专门为生成静态图像而设计，如果调用的工作流实际上生成了视频，系统将抛出 400 错误。
    """
    try:
        # 记录请求内容前缀用于调试日志
        logger.info(f"Image generation request: {request.prompt[:50]}...")
        
        # Call media service (backward compatible with image API) / 调用核心媒体生成服务（兼容旧版生图接口）
        media_result = await pixelle_video.media(
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            workflow=request.workflow
        )
        
        # For backward compatibility, only support image results in /image endpoint 
        # 出于接口职责分离的考虑，确保当前的 `/image` 端点只返回静态图片。
        # 如果检测到工作流实际生成的是视频，则提示客户端调用专门的媒体生成端点。
        if media_result.is_video:
            raise HTTPException(
                status_code=400,
                detail="Video workflow used. Please use /media/generate endpoint for video generation."
            )
        
        return ImageGenerateResponse(
            image_path=media_result.url
        )
        
    except HTTPException:
        # FastAPI 自定义的 HTTP 异常直接向上抛出
        raise
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        # 捕获其他未知异常并转换为 500 内部服务器错误返回
        raise HTTPException(status_code=500, detail=str(e))

