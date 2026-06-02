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
LLM (Large Language Model) endpoints

此模块定义了与大语言模型（LLM）进行交互的直接 API 路由端点。
主要暴露了 `/api/llm/chat` 接口，允许前端或其他服务直接调用底层配置好的 LLM 引擎。
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.llm import LLMChatRequest, LLMChatResponse

# 创建带有 "/llm" 前缀的 APIRouter，并在 Swagger 中归类为 "Basic Services"
router = APIRouter(prefix="/llm", tags=["Basic Services"])


@router.post("/chat", response_model=LLMChatResponse)
async def llm_chat(
    request: LLMChatRequest,
    pixelle_video: PixelleVideoDep
):
    """
    LLM 对话交互端点。
    
    使用系统后台配置的语言模型（如 OpenAI、Gemini 或本地大模型）来生成文本响应。
    
    请求参数说明：
    - **prompt**: 用户的提示词或问题。
    - **temperature**: 生成的创造性（0.0 到 2.0，值越低生成的文本越确定和保守）。
    - **max_tokens**: 允许生成的最大 Token 数量。
    
    返回：
        LLMChatResponse: 包含生成的文本内容的对象。
    """
    try:
        # 记录请求的部分内容用于审计与调试
        logger.info(f"LLM chat request: {request.prompt[:50]}...")
        
        # 通过依赖注入获取到 PixelleVideoCore 实例，并调用其内部的 LLM 服务组件
        response = await pixelle_video.llm(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # 封装为响应数据模型并返回
        return LLMChatResponse(
            content=response,
            tokens_used=None  # 暂时预留，如果底层 LLM 接口支持统计 Token 消耗可在此处补充
        )
        
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        # 如果调用失败，抛出 HTTP 500 内部服务器错误并附带异常详情
        raise HTTPException(status_code=500, detail=str(e))

