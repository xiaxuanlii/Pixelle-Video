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
Models Package

核心数据模型模块初始化文件。
统一暴露了用于各服务之间进行数据流转的核心领域对象。
"""

from pixelle_video.models.progress import ProgressEvent
from pixelle_video.models.media import MediaResult
from pixelle_video.models.storyboard import (
    StoryboardConfig,
    StoryboardFrame,
    ContentMetadata,
    Storyboard,
    VideoGenerationResult
)

__all__ = [
    # 进度上报事件
    "ProgressEvent",
    # 媒体生成结果
    "MediaResult",
    # 视频剧本系列模型
    "StoryboardConfig",
    "StoryboardFrame",
    "ContentMetadata",
    "Storyboard",
    "VideoGenerationResult"
]
