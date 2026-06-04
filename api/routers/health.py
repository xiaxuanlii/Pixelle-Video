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
Health check and system info endpoints

此模块定义了服务的健康检查（Health check）与系统信息路由端点。
主要用于负载均衡器、容器编排工具（如 Kubernetes）或监控系统来检测服务是否存活。
"""

from fastapi import APIRouter
from pydantic import BaseModel

# 创建 APIRouter 实例，并在 Swagger 文档中将其归类为 "Health" 标签
router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """
    健康检查的响应数据模型。
    """
    status: str = "healthy"          # 当前服务状态标识
    version: str = "0.1.0"           # 服务的当前版本号
    service: str = "Pixelle-Video API" # 服务的名称标识


class CapabilitiesResponse(BaseModel):
    """
    系统能力响应数据模型（预留扩展用，如返回是否支持 GPU 加速等信息）。
    """
    success: bool = True
    capabilities: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查端点。
    
    返回服务的存活状态及版本信息。如果服务崩溃或由于资源耗尽无响应，
    监控平台将无法收到 "healthy" 的反馈。
    
    Returns:
        HealthResponse: 包含状态、版本和服务名称的对象。
    """
    return HealthResponse()


@router.get("/version", response_model=HealthResponse)
async def get_version():
    """
    获取 API 版本端点。
    
    功能与 /health 类似，返回当前运行的服务版本信息。
    
    Returns:
        HealthResponse: 包含状态、版本和服务名称的对象。
    """
    return HealthResponse()

