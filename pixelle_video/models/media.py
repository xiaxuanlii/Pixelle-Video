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
Media generation result models

媒体生成结果数据模型模块。
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class MediaResult(BaseModel):
    """
    底层媒体工作流执行完毕后返回的统一结果模型。
    
    支持图像和视频两种输出形式（主要对接 ComfyKit 的 ExecuteResult）。
    
    Attributes:
        media_type: 实际生成的媒体类型 ("image" 或 "video")。
        url: 媒体文件的可访问网络 URL 或物理存放路径。
        duration: 仅当为视频时记录其播放时长（秒），如果是图片则为 None。
    
    Examples:
        # 图像生成结果
        MediaResult(media_type="image", url="http://example.com/image.png")
        
        # 视频生成结果
        MediaResult(media_type="video", url="http://example.com/video.mp4", duration=5.2)
    """
    
    media_type: Literal["image", "video"] = Field(
        description="生成的媒体类型 (图像/视频)"
    )
    url: str = Field(
        description="目标媒体文件的 URL 或本地路径"
    )
    duration: Optional[float] = Field(
        None,
        description="视频播放时长(秒)，仅针对视频输出有效"
    )
    
    @property
    def is_image(self) -> bool:
        """快速判断是否为静态图片类型"""
        return self.media_type == "image"
    
    @property
    def is_video(self) -> bool:
        """快速判断是否为动态视频类型"""
        return self.media_type == "video"
