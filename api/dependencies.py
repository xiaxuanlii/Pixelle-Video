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
FastAPI Dependencies

此模块提供 FastAPI 的依赖注入功能，主要用于实例化和管理 `PixelleVideoCore`（核心服务）
以及其他相关服务的生命周期。
"""

from typing import Annotated
from fastapi import Depends
from loguru import logger

from pixelle_video.service import PixelleVideoCore


# Global Pixelle-Video instance / 全局 Pixelle-Video 核心实例
# 采用单例模式，在需要时按需初始化
_pixelle_video_instance: PixelleVideoCore = None


async def get_pixelle_video() -> PixelleVideoCore:
    """
    获取 Pixelle-Video 核心实例（作为 FastAPI 依赖注入项）。
    
    采用单例模式实现：如果在当前上下文中 `_pixelle_video_instance` 为空，
    则创建一个新的 `PixelleVideoCore` 实例并调用其 `initialize` 异步方法进行初始化。
    
    Returns:
        PixelleVideoCore: 初始化完成的核心服务实例，供后续请求的业务逻辑调用。
    """
    global _pixelle_video_instance
    
    if _pixelle_video_instance is None:
        _pixelle_video_instance = PixelleVideoCore()
        await _pixelle_video_instance.initialize()
        logger.info("✅ Pixelle-Video initialized for API")
    
    return _pixelle_video_instance


async def shutdown_pixelle_video():
    """
    关闭 Pixelle-Video 实例并清理资源。
    
    该函数通常在 FastAPI 应用程序生命周期结束（如关闭服务）时调用。
    它负责清理底层核心逻辑的资源占用，例如清除临时文件缓存、关闭线程池，
    以及显式关闭 HTMLFrameGenerator 所使用的无头浏览器实例（例如 Playwright 浏览器），
    防止出现僵尸进程。
    """
    global _pixelle_video_instance
    if _pixelle_video_instance:
        logger.info("Shutting down Pixelle-Video...")
        await _pixelle_video_instance.cleanup()
        _pixelle_video_instance = None
    
    from pixelle_video.services.frame_html import HTMLFrameGenerator
    await HTMLFrameGenerator.close_browser()


# Type alias for dependency injection / 用于依赖注入的类型别名
# 在路由处理函数中，可通过声明 `pixelle_video: PixelleVideoDep` 自动注入核心实例。
PixelleVideoDep = Annotated[PixelleVideoCore, Depends(get_pixelle_video)]

