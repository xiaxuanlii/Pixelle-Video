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
Pixelle-Video - AI-powered video generator

Pixelle-Video 核心后端服务包。
基于规约与统一配置中心驱动的开源跨平台 AI 营销视频生成引擎框架！

使用示例:
    from pixelle_video import pixelle_video
    
    # 全局初始化一次
    await pixelle_video.initialize()
    
    # 原子级能力调用示例
    answer = await pixelle_video.llm("Explain atomic habits")
    audio = await pixelle_video.tts("Hello world")
    
    # 调用视频流水线总成
    result = await pixelle_video.generate_video(
        text="如何提高学习效率",
        n_scenes=5
    )
"""

from pixelle_video.service import PixelleVideoCore, pixelle_video
from pixelle_video.config import config_manager

__version__ = "0.1.0"

__all__ = ["PixelleVideoCore", "pixelle_video", "config_manager"]
