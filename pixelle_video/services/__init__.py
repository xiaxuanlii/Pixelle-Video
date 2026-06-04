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
Pixelle-Video Services

系统核心内部原子服务能力层大礼包。

本目录统一暴露出各项专职的基础服务驱动器实现：
- LLMService: 大语言模型的统一直连管道与数据清洗器
- TTSService: 处理长文本朗读转音的系统
- MediaService: ComfyUI 画师系统的分发调度核心
- VideoService: 本地级 ffmpeg 离线剪辑剪切混合轨道大师
- FrameProcessor: 单帧渲染与混合管道总装控制器
- PersistenceService: 全生命周期的任务结果持久化记录归档器
- HistoryManager: 处理查询操作等交互向业务的高级组件
- ComfyBaseService: 以上涉及 ComfyUI 流程调用的底座抽象父类
"""

from pixelle_video.services.comfy_base_service import ComfyBaseService
from pixelle_video.services.llm_service import LLMService
from pixelle_video.services.tts_service import TTSService
from pixelle_video.services.media import MediaService
from pixelle_video.services.video import VideoService
from pixelle_video.services.frame_processor import FrameProcessor
from pixelle_video.services.persistence import PersistenceService
from pixelle_video.services.history_manager import HistoryManager

# 为了防止兼容性问题破坏旧架构对图片专用生成的引用而采用的前置保留处理名
ImageService = MediaService

__all__ = [
    "ComfyBaseService",
    "LLMService",
    "TTSService",
    "MediaService",
    "ImageService",  # Backward compatibility
    "VideoService",
    "FrameProcessor",
    "PersistenceService",
    "HistoryManager",
]
