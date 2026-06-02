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
API Configuration

此模块定义了 FastAPI 服务的核心配置项，包括服务器启动参数、CORS 跨域设置、
任务管理器参数、文件上传限制以及 API 路由前缀等。
"""

from typing import Optional
from pydantic import BaseModel


class APIConfig(BaseModel):
    """
    API 服务的配置数据模型。
    
    该类使用 Pydantic 的 BaseModel 进行参数验证和类型推断。
    通过全局实例 `api_config` 提供配置给 FastAPI 应用程序使用。
    """
    
    # Server settings / 服务器设置
    host: str = "0.0.0.0"      # 绑定的主机地址
    port: int = 8000           # 监听的端口号
    reload: bool = False       # 是否开启热重载（通常在开发模式下为 True）
    
    # CORS settings / 跨域资源共享设置
    cors_enabled: bool = True           # 是否启用 CORS
    cors_origins: list[str] = ["*"]     # 允许跨域请求的来源列表
    
    # Task settings / 异步任务管理设置
    max_concurrent_tasks: int = 5       # 最大并发执行的后台任务数
    task_cleanup_interval: int = 3600   # 定期清理已完成任务的时间间隔（秒），默认 1 小时
    task_retention_time: int = 86400    # 已完成任务结果的保留时间（秒），默认 24 小时
    
    # File upload settings / 文件上传设置
    max_upload_size: int = 100 * 1024 * 1024  # 允许的最大上传文件大小（字节），默认 100MB
    
    # API settings / 路由和文档设置
    api_prefix: str = "/api"            # 所有业务接口的统一前缀
    docs_url: Optional[str] = "/docs"   # Swagger UI 文档的访问路径
    redoc_url: Optional[str] = "/redoc" # ReDoc 文档的访问路径
    openapi_url: Optional[str] = "/openapi.json" # OpenAPI schema 文件的访问路径


# Global config instance / 全局配置实例
# 在整个 API 服务生命周期中，可以直接导入此实例以读取配置。
api_config = APIConfig()

