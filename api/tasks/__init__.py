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
Task management for async operations

异步任务管理模块的初始化文件。
向外暴露核心的任务数据结构（模型）和全局任务管理器实例（`task_manager`）。
"""

from api.tasks.models import Task, TaskStatus, TaskType
from api.tasks.manager import task_manager

__all__ = ["Task", "TaskStatus", "TaskType", "task_manager"]

