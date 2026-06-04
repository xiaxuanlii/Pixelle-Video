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
Task data models

此模块定义了后台任务流中使用的各类数据模型和枚举类型，
主要用于 API 请求和响应的序列化/反序列化，以及内存状态管理。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """
    任务状态枚举类型。
    
    用于标识一个异步任务（如视频生成）当前所处的生命周期阶段。
    """
    PENDING = "pending"       # 任务已创建，等待调度执行
    RUNNING = "running"       # 任务正在执行中
    COMPLETED = "completed"   # 任务已成功执行完毕
    FAILED = "failed"         # 任务执行失败（发生了异常）
    CANCELLED = "cancelled"   # 任务已被用户或系统主动取消


class TaskType(str, Enum):
    """
    任务类型枚举。
    
    目前系统支持的后台长耗时任务类型。
    """
    VIDEO_GENERATION = "video_generation"  # 异步端到端视频生成任务


class TaskProgress(BaseModel):
    """
    任务进度信息模型。
    
    记录任务在执行过程中的具体进展，供前端轮询进度条展示。
    """
    current: int = 0          # 当前已完成的步数
    total: int = 0            # 总步数（预估值）
    percentage: float = 0.0   # 计算得出的百分比进度 (0.0 - 100.0)
    message: str = ""         # 当前阶段的状态描述（如"正在合成语音..."）


class Task(BaseModel):
    """
    核心任务数据模型。
    
    综合包含了一个异步任务的所有元数据、状态、进度以及最终结果，
    在整个任务生命周期中由 TaskManager 进行维护和更新。
    """
    task_id: str                      # 全局唯一的任务标识符 (UUID)
    task_type: TaskType               # 任务的具体类型
    status: TaskStatus = TaskStatus.PENDING # 当前任务状态，默认为等待中
    
    # Progress tracking / 进度追踪信息
    progress: Optional[TaskProgress] = None
    
    # Result / 最终结果或错误记录
    result: Optional[Any] = None      # 任务成功后返回的业务数据（如视频的下载链接或相对路径）
    error: Optional[str] = None       # 任务失败时记录的详细异常信息
    
    # Metadata / 时间元数据
    created_at: datetime = Field(default_factory=datetime.now) # 任务被创建的初始时间
    started_at: Optional[datetime] = None                      # 任务实际开始运行的时间
    completed_at: Optional[datetime] = None                    # 任务完成（成功、失败或取消）的时间
    
    # Request parameters (for reference) / 触发任务时的原始请求参数（用于回溯查证）
    request_params: Optional[dict] = None
    
    class Config:
        """Pydantic 模型配置"""
        json_encoders = {
            # 在 JSON 序列化时自动将 datetime 对象转换为 ISO 8601 格式字符串
            datetime: lambda v: v.isoformat()
        }

