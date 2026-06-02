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
Base Pipeline for Video Generation

视频生成流水线基础抽象类模块。
所有自定义的流水线实现都必须继承自 `BasePipeline`，并实现 `__call__` 方法。
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable

from loguru import logger

from pixelle_video.models.progress import ProgressEvent
from pixelle_video.models.storyboard import VideoGenerationResult


class BasePipeline(ABC):
    """
    视频生成的抽象基类流水线。
    
    所有自定义流水线应当继承此类并实现 `__call__` 方法以暴露标准的调用接口。
    
    设计原则:
    - 每一个 Pipeline 子类代表一种完整的、特定业务场景下的视频生成工作流。
    - 各个 Pipeline 之间完全独立，可以拥有截然不同的编排逻辑。
    - 所有 Pipeline 都可以通过 `self.core` 访问全局持有的底层引擎原子服务 (如 llm, tts, media)。
    - Pipeline 应当在关键节点通过 `progress_callback` 汇报自身进度，以便前端渲染进度条。
    
    示例:
        >>> class MyPipeline(BasePipeline):
        ...     async def __call__(self, text: str, **kwargs):
        ...         # 步骤 1: 准备内容
        ...         narrations = await some_logic(text)
        ...         
        ...         # 步骤 2: 生产画面
        ...         for narration in narrations:
        ...             audio = await self.core.tts(narration)
        ...             # ...
        ...         
        ...         return VideoGenerationResult(...)
    """
    
    def __init__(self, pixelle_video_core):
        """
        使用核心服务实例初始化流水线基类。
        
        Args:
            pixelle_video_core: PixelleVideoCore 的引用实例，提供了所有底层服务的懒加载桥接。
        """
        self.core = pixelle_video_core
        
        # 快捷方式代理核心子服务，方便子类直接调用
        self.llm = pixelle_video_core.llm
        self.tts = pixelle_video_core.tts
        self.media = pixelle_video_core.media
        self.video = pixelle_video_core.video
        
        # 保留对旧版本代码的向下兼容支持
        self.image = pixelle_video_core.media
    
    @abstractmethod
    async def __call__(
        self,
        text: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        **kwargs
    ) -> VideoGenerationResult:
        """
        执行流水线。子类必须实现此方法。
        
        Args:
            text: 输入内容（具体含义由实现流水线自行解释，如：脚本、提示词等）。
            progress_callback: (可选) 用于实时上报进度的回调函数，接收 ProgressEvent 对象。
            **kwargs: 提供给该流水线的特有定制化超参。
            
        Returns:
            VideoGenerationResult: 封装好的最终视频结果对象，包含路径、元数据。
            
        Raises:
            Exception: 流水线执行期间发生错误时向外抛出。
        """
        pass
    
    def _report_progress(
        self,
        callback: Optional[Callable[[ProgressEvent], None]],
        event_type: str,
        progress: float,
        **kwargs
    ):
        """
        辅助方法：发送进度汇报事件。
        
        Args:
            callback: 进度回调函数。
            event_type: 进度事件的类型标识（如 "generating_script"）。
            progress: 总进度百分比 (0.0-1.0)。
            **kwargs: 额外的定制数据（如 frame_current, frame_total 等）。
        """
        if callback:
            event = ProgressEvent(event_type=event_type, progress=progress, **kwargs)
            callback(event)
            logger.debug(f"Progress: {progress*100:.0f}% - {event_type}")
        else:
            logger.debug(f"Progress: {progress*100:.0f}% - {event_type}")
