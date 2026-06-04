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
LLM API schemas

此模块定义了大语言模型（LLM）对话交互所使用的请求和响应数据结构，
供 `/api/llm` 相关的路由使用。
"""

from typing import Optional
from pydantic import BaseModel, Field


class LLMChatRequest(BaseModel):
    """
    LLM 对话请求模型。
    
    封装了向后台语言模型发送请求时所需的核心参数。
    """
    prompt: str = Field(..., description="用户输入的提示词内容")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成文本的温度值（创造性），范围 0.0-2.0。值越高，输出越具有随机性和创意；值越低，输出越稳定、保守。")
    max_tokens: int = Field(2000, ge=1, le=32000, description="允许生成的最大 Token 数量上限。")
    
    class Config:
        """为 Swagger UI 等文档工具提供默认的示例结构。"""
        json_schema_extra = {
            "example": {
                "prompt": "用三句话解释原子习惯的概念",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }


class LLMChatResponse(BaseModel):
    """
    LLM 对话响应模型。
    
    封装了从语言模型接收到的生成结果及其元数据。
    """
    success: bool = True     # 标识请求是否成功
    message: str = "Success" # 响应的状态描述
    content: str = Field(..., description="大语言模型生成的实际文本内容")
    tokens_used: Optional[int] = Field(None, description="本次请求消耗的总 Token 数量（包含输入和输出，如果可用的话）")

