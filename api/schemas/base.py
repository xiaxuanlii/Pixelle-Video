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
Base schemas

此模块定义了 API 接口响应的最基础数据结构，
所有具体的业务响应模型都可以继承或参照这些结构，
以确保 API 返回格式的一致性。
"""

from typing import Any, Optional
from pydantic import BaseModel


class BaseResponse(BaseModel):
    """
    基础 API 响应模型。
    
    用于封装所有成功的 API 请求的返回结果，提供统一的数据结构。
    
    Attributes:
        success: 标识请求是否成功，默认为 True。
        message: 响应的提示信息，默认为 "Success"。
        data: 实际返回的业务数据，类型可以是任意结构（字典、列表等）。
    """
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """
    错误响应模型。
    
    用于封装 API 请求失败或异常时的返回结果。
    
    Attributes:
        success: 标识请求是否成功，此模型中强制为 False。
        message: 向用户展示的友好错误提示信息。
        error: 详细的系统报错信息或异常堆栈（通常仅在开发或调试时返回）。
    """
    success: bool = False
    message: str
    error: Optional[str] = None

