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
Prompts package

系统提示词大礼包。
集中管理、维护并对外暴露所有与各类大模型 (LLM) 进行深度交互时所需的高质量模板与约束词。
"""

# 剧本与旁白生成的智能助手提示词
from pixelle_video.prompts.topic_narration import build_topic_narration_prompt
from pixelle_video.prompts.content_narration import build_content_narration_prompt
from pixelle_video.prompts.title_generation import build_title_generation_prompt

# 视觉画面构建的智能助手提示词
from pixelle_video.prompts.image_generation import (
    build_image_prompt_prompt,
    IMAGE_STYLE_PRESETS,
    DEFAULT_IMAGE_STYLE
)
from pixelle_video.prompts.style_conversion import build_style_conversion_prompt


__all__ = [
    # Narration builders
    "build_topic_narration_prompt",
    "build_content_narration_prompt",
    "build_title_generation_prompt",
    
    # Image builders
    "build_image_prompt_prompt",
    "build_style_conversion_prompt",
    
    # Image style presets
    "IMAGE_STYLE_PRESETS",
    "DEFAULT_IMAGE_STYLE",
]
