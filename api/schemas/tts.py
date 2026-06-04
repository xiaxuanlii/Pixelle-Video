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
TTS API schemas

此模块定义了文本转语音（TTS）API 接口（`/api/tts`）所使用的请求和响应数据模型，
支持标准语音合成以及基于参考音频的声音克隆功能。
"""

from typing import Optional
from pydantic import BaseModel, Field


class TTSSynthesizeRequest(BaseModel):
    """
    TTS 语音合成请求模型。
    
    请求将指定文本转换为音频文件。
    """
    text: str = Field(..., description="需要合成语音的原始文本")
    workflow: Optional[str] = Field(
        None, 
        description="指定调用的 TTS 工作流（例如：'runninghub/tts_edge.json' 或 'selfhost/tts_edge.json'）。如果不指定，系统将回退使用配置中的默认工作流。"
    )
    ref_audio: Optional[str] = Field(
        None, 
        description="用于声音克隆的参考音频路径（可选）。可以是服务器上的本地相对路径或可访问的 URL。"
    )
    voice_id: Optional[str] = Field(
        None, 
        description="（已废弃）为了向后兼容保留的音色 ID 参数，建议使用 workflow 参数替代。"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "你好，欢迎使用 Pixelle-Video 视频生成平台！",
                "workflow": "runninghub/tts_edge.json",
                "ref_audio": None
            }
        }


class TTSSynthesizeResponse(BaseModel):
    """
    TTS 语音合成响应模型。
    
    返回合成后的音频文件路径及音频的基本元数据。
    """
    success: bool = True
    message: str = "Success"
    audio_path: str = Field(..., description="已生成的音频文件的相对路径或访问 URL")
    duration: float = Field(..., description="生成的音频总时长（以秒为单位）")

