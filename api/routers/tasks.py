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
Task management endpoints

此模块定义了用于管理和追踪异步长耗时任务（如视频生成）的 API 路由端点。
包含了任务列表查询、特定任务进度查询和取消任务的接口。
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.tasks import task_manager, Task, TaskStatus

# 创建带有 "/tasks" 前缀的 APIRouter，并在 Swagger 中归类为 "Tasks"
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=List[Task])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="可选的任务状态过滤条件"),
    limit: int = Query(100, ge=1, le=1000, description="最大返回的任务条数（默认 100）")
):
    """
    获取后台任务列表。
    
    返回系统当前记录的所有任务信息，默认按照创建时间倒序排列（最新的在最前）。
    可用于前端管理面板或监控页面展示系统负载。
    
    请求参数说明：
    - **status**: 可选过滤参数，仅返回指定状态的任务（如 pending/running/completed/failed/cancelled）。
    - **limit**: 最多返回的条目数（上限 1000）。
    
    返回：
        List[Task]: 符合条件的任务对象列表。
    """
    try:
        tasks = task_manager.list_tasks(status=status, limit=limit)
        return tasks
        
    except Exception as e:
        logger.error(f"List tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """
    查询指定任务的详情。
    
    通常由客户端调用此接口来进行短轮询（Polling），以获取任务当前的执行进度、
    阶段描述以及任务完成后的最终结果。
    
    请求参数说明：
    - **task_id**: 创建任务时系统返回的唯一 UUID。
    
    返回：
        Task: 任务的完整详情，如果完成还会包含 `result` 数据，如果失败则包含 `error` 字段。
    """
    try:
        task = task_manager.get_task(task_id)
        
        if not task:
            # 如果内存中找不到该任务（可能由于过期被清理或本身无效），返回 404
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """
    取消正在执行或排队中的任务。
    
    如果任务处于 PENDING 或 RUNNING 状态，系统将中断底层的 asyncio Task。
    注意：某些底层强绑定或原子性的子进程（如某些外部调用）可能无法立即停止，但逻辑主线会中断。
    
    请求参数说明：
    - **task_id**: 要取消的任务唯一标识。
    
    返回：
        dict: 操作成功与否的状态信息。
    """
    try:
        success = task_manager.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return {
            "success": True,
            "message": f"Task {task_id} cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

