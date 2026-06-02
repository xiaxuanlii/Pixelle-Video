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
API Schemas (Pydantic models)

API 接口数据模型包初始化文件。
此文件集中导入并暴露了各个子模块中定义的 Pydantic 请求和响应模型，
方便在其他地方通过 `from api.schemas import xxx` 统一引用。
"""

from api.schemas.base import BaseResponse, ErrorResponse
from api.schemas.llm import LLMChatRequest, LLMChatResponse
from api.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from api.schemas.image import ImageGenerateRequest, ImageGenerateResponse
from api.schemas.content import (
    NarrationGenerateRequest,
    NarrationGenerateResponse,
    ImagePromptGenerateRequest,
    ImagePromptGenerateResponse,
    TitleGenerateRequest,
    TitleGenerateResponse,
)
from api.schemas.video import (
    VideoGenerateRequest,
    VideoGenerateResponse,
    VideoGenerateAsyncResponse,
)

__all__ = [
    # Base / 基础模型
    "BaseResponse",
    "ErrorResponse",
    # LLM / 大语言模型对话
    "LLMChatRequest",
    "LLMChatResponse",
    # TTS / 语音合成
    "TTSSynthesizeRequest",
    "TTSSynthesizeResponse",
    # Image / 图像生成
    "ImageGenerateRequest",
    "ImageGenerateResponse",
    # Content / 内容创作(旁白、提示词、标题)
    "NarrationGenerateRequest",
    "NarrationGenerateResponse",
    "ImagePromptGenerateRequest",
    "ImagePromptGenerateResponse",
    "TitleGenerateRequest",
    "TitleGenerateResponse",
    # Video / 视频生成
    "VideoGenerateRequest",
    "VideoGenerateResponse",
    "VideoGenerateAsyncResponse",
]

