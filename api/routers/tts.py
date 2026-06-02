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
TTS (Text-to-Speech) endpoints

此模块定义了与文本转语音（TTS）服务交互的 API 路由端点。
主要暴露了 `/api/tts/synthesize` 接口，供前端或其他服务独立调用系统的语音合成和声音克隆功能。
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from pixelle_video.utils.tts_util import get_audio_duration

# 创建带有 "/tts" 前缀的 APIRouter，并在 Swagger 中归类为 "Basic Services"
router = APIRouter(prefix="/tts", tags=["Basic Services"])


@router.post("/synthesize", response_model=TTSSynthesizeResponse)
async def tts_synthesize(
    request: TTSSynthesizeRequest,
    pixelle_video: PixelleVideoDep
):
    """
    文本转语音（TTS）合成端点。
    
    使用底层系统（如 ComfyUI 工作流）将传入的文本转换为音频文件。
    支持标准语音合成以及基于参考音频的自定义声音克隆。
    
    请求参数说明：
    - **text**: 需要合成的原始文本。
    - **workflow**: (可选) 指定调用的 TTS 工作流名称或路径。如果未指定，系统将使用配置的默认工作流。
    - **ref_audio**: (可选) 用于声音克隆的参考音频文件路径或 URL。
    - **voice_id**: (已废弃) 为了兼容旧版本预留的音色标识参数。
    
    返回：
        TTSSynthesizeResponse: 包含生成的音频文件路径以及音频的准确时长（秒）。
    
    示例（标准合成）：
    ```json
    {
        "text": "你好，欢迎使用 Pixelle-Video！",
        "workflow": "runninghub/tts_edge.json"
    }
    ```
    
    示例（带声音克隆）：
    ```json
    {
        "text": "你好，这是一段克隆声音生成的测试文本。",
        "workflow": "runninghub/tts_index2.json",
        "ref_audio": "path/to/reference.wav"
    }
    ```
    """
    try:
        # 记录请求内容前缀用于调试
        logger.info(f"TTS synthesis request: {request.text[:50]}...")
        
        # Build TTS parameters / 构建传递给底层引擎的参数字典
        tts_params = {"text": request.text}
        
        # Add workflow if specified / 如果指定了具体工作流，则添加
        if request.workflow:
            tts_params["workflow"] = request.workflow
        
        # Add ref_audio if specified / 如果提供了参考音频（用于声音克隆），则添加
        if request.ref_audio:
            tts_params["ref_audio"] = request.ref_audio
        
        # Legacy voice_id support (deprecated) / 兼容老版本的 voice_id 逻辑
        if request.voice_id and not request.workflow:
            logger.warning("voice_id parameter is deprecated, please use workflow instead")
            tts_params["voice"] = request.voice_id
        
        # Call TTS service / 调用核心服务进行实际的音频合成并等待结果
        audio_path = await pixelle_video.tts(**tts_params)
        
        # Get audio duration / 读取生成音频文件的准确时长
        duration = get_audio_duration(audio_path)
        
        # 封装为响应对象返回
        return TTSSynthesizeResponse(
            audio_path=audio_path,
            duration=duration
        )
        
    except Exception as e:
        logger.error(f"TTS synthesis error: {e}")
        # 如果底层引擎抛出异常，捕获并转换为 HTTP 500 错误返回给客户端
        raise HTTPException(status_code=500, detail=str(e))

