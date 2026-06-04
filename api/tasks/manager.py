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
Task Manager

此模块提供基于内存的任务管理器，用于异步处理和追踪视频生成等耗时任务。
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from loguru import logger

from api.tasks.models import Task, TaskStatus, TaskType, TaskProgress
from api.config import api_config


class TaskManager:
    """
    异步视频生成任务的任务管理器。
    
    主要特性：
    - 基于内存的存储（未来可扩展为 Redis 或数据库存储以支持分布式）。
    - 任务生命周期管理（创建、运行、完成、失败、取消）。
    - 任务进度追踪（通过 update_progress 更新）。
    - 自动清理过期任务（定期清除已完成或失败的旧任务以释放内存）。
    """
    
    def __init__(self):
        # 存储任务元数据信息，键为 task_id
        self._tasks: Dict[str, Task] = {}
        # 存储 asyncio.Task 对象，用于控制任务执行和取消
        self._task_futures: Dict[str, asyncio.Task] = {}
        # 执行自动清理循环的后台任务对象
        self._cleanup_task: Optional[asyncio.Task] = None
        # 标记管理器是否正在运行
        self._running = False
    
    async def start(self):
        """
        启动任务管理器并调度清理循环。
        
        此方法通常在 FastAPI 的启动事件中调用。
        """
        if self._running:
            logger.warning("Task manager already running")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("✅ Task manager started")
    
    async def stop(self):
        """
        停止任务管理器并取消所有正在运行的任务。
        
        此方法通常在 FastAPI 的关闭事件中调用，以确保资源的优雅释放。
        """
        self._running = False
        
        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 取消所有正在运行的业务任务
        for task_id, future in self._task_futures.items():
            if not future.done():
                future.cancel()
                logger.info(f"Cancelled task: {task_id}")
        
        # 清空内存数据
        self._tasks.clear()
        self._task_futures.clear()
        logger.info("✅ Task manager stopped")
    
    def create_task(
        self,
        task_type: TaskType,
        request_params: Optional[dict] = None
    ) -> Task:
        """
        创建一个新的后台任务记录。
        
        生成唯一的 task_id，并将初始状态设置为 PENDING。
        
        Args:
            task_type: 任务的类型（例如视频生成、内容生成等）。
            request_params: 触发此任务的原始请求参数字典，方便后续查询。
            
        Returns:
            Task: 创建的 Task 数据模型对象。
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            request_params=request_params,
        )
        
        self._tasks[task_id] = task
        logger.info(f"Created task {task_id} ({task_type})")
        return task
    
    async def execute_task(
        self,
        task_id: str,
        coro_func: Callable,
        *args,
        **kwargs
    ):
        """
        异步执行指定的任务。
        
        将状态更新为 RUNNING 并开始执行传入的协程函数。执行完成后，
        根据结果将状态更新为 COMPLETED 或 FAILED，并记录执行时间及结果/错误信息。
        
        Args:
            task_id: 之前通过 `create_task` 创建的任务 ID。
            coro_func: 实际执行业务逻辑的异步协程函数。
            *args: 传递给协程函数的位置参数。
            **kwargs: 传递给协程函数的关键字参数。
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        # 定义内部异步包装函数
        async def _execute():
            try:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                logger.info(f"Task {task_id} started")
                
                # 实际执行业务逻辑
                result = await coro_func(*args, **kwargs)
                
                # 执行成功，更新任务结果
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                logger.info(f"Task {task_id} completed")
                
            except Exception as e:
                # 执行抛出异常，记录错误信息
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                logger.error(f"Task {task_id} failed: {e}")
        
        # 将内部函数放入 asyncio 执行队列中
        future = asyncio.create_task(_execute())
        self._task_futures[task_id] = future
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        通过任务 ID 获取任务详情。
        
        Args:
            task_id: 任务的唯一标识。
            
        Returns:
            Task: 如果找到任务，则返回 Task 对象，否则返回 None。
        """
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[Task]:
        """
        获取任务列表，支持状态过滤和数量限制。
        
        返回的任务列表会按照创建时间（created_at）降序排序（最新的排在前面）。
        
        Args:
            status: （可选）仅返回指定状态的任务。
            limit: 返回的最大任务数量，默认为 100。
            
        Returns:
            List[Task]: 符合条件的任务列表。
        """
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # 按创建时间降序排序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    def update_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        message: str = ""
    ):
        """
        更新任务的执行进度。
        
        Args:
            task_id: 任务的唯一标识。
            current: 当前完成的步数/数量。
            total: 总步数/数量。
            message: 当前进度的简要描述信息（如"正在生成图像..."）。
        """
        task = self._tasks.get(task_id)
        if not task:
            return
        
        # 计算百分比
        percentage = (current / total * 100) if total > 0 else 0
        task.progress = TaskProgress(
            current=current,
            total=total,
            percentage=percentage,
            message=message
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消一个正在运行的任务。
        
        向底层 asyncio.Task 发送取消信号，并将任务状态变更为 CANCELLED。
        
        Args:
            task_id: 任务的唯一标识。
            
        Returns:
            bool: 如果成功取消则返回 True，否则（如任务不存在）返回 False。
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # Do not cancel already-terminal tasks / 不要取消已终止的任务
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False

        # Cancel future if running / 如果任务还在运行，取消 future
        future = self._task_futures.get(task_id)
        if future and not future.done():
            future.cancel()
        
        # 更新任务状态
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        logger.info(f"Cancelled task {task_id}")
        return True
    
    async def _cleanup_loop(self):
        """
        后台循环协程，用于定期清理旧的、已完成的任务记录。
        
        清理周期由 `api_config.task_cleanup_interval` 决定。
        """
        while self._running:
            try:
                await asyncio.sleep(api_config.task_cleanup_interval)
                self._cleanup_old_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _cleanup_old_tasks(self):
        """
        执行实际的清理逻辑：移除超出保留时间（task_retention_time）的非活跃任务。
        """
        cutoff_time = datetime.now() - timedelta(seconds=api_config.task_retention_time)
        
        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            # 仅清理已完成、失败或被取消的任务
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task.completed_at and task.completed_at < cutoff_time:
                    tasks_to_remove.append(task_id)
        
        # 从字典中删除数据
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
            if task_id in self._task_futures:
                del self._task_futures[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")


# Global task manager instance / 全局任务管理器实例
task_manager = TaskManager()

