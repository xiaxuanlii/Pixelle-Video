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
History Manager Service

历史任务管理聚合服务层。
通过包装 `PersistenceService` 提供了专门面向业务和 UI 显示用的逻辑接口服务，
如支持生成表单预填充的“回填克隆”、“危险级联资源销毁”等高度封装的复合业务方法。
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
from loguru import logger

from pixelle_video.services.persistence import PersistenceService


class HistoryManager:
    """
    负责维护全生命周期产生物（视频和缓存）与页面显示数据的历史状态管控中心。
    
    核心功能矩阵:
    - 针对分页历史数据列表的提供及筛选查询支持。
    - 详尽包裹剧本和进度数据的深级提取。
    - 提供根据历史配置重新唤起填表的 "一键同款克隆 (Duplicate)"。
    - 安全抹除过往生成的占容文件及同步级联清理索引。
    """
    
    def __init__(self, persistence: PersistenceService):
        """
        依赖注入引入底层存储连接器。
        
        Args:
            persistence: 专门管理 I/O 文件写操作的持久化对象引用。
        """
        self.persistence = persistence
    
    async def get_task_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        以分页标准响应形式向外界提取历史总记录台账集合。
        
        Returns:
            Dict: 类似 {"tasks": [...], "total": 100, "page": 1, "page_size": 20, "total_pages": 5}
        """
        return await self.persistence.list_tasks_paginated(
            page=page,
            page_size=page_size,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        提取某个任务深达血肉的关联资源对象详情，包括基础请求与巨细无遗的分镜节点对象（Storyboard）。
        """
        metadata = await self.persistence.load_task_metadata(task_id)
        if not metadata:
            return None
        
        storyboard = await self.persistence.load_storyboard(task_id)
        
        return {
            "metadata": metadata,
            "storyboard": storyboard,
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取目前机器产出数据量大盘仪表汇总数据，常用于页面图表和资源压力监控告警预检。"""
        return await self.persistence.get_statistics()
    
    async def delete_task(self, task_id: str) -> bool:
        """物理层一键安全粉碎与指定任务绑定的文件流与大纲索引条目。"""
        return await self.persistence.delete_task(task_id)
    
    async def duplicate_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        核心便捷特性：一键历史配置提取。
        
        允许用户通过任意一次过去成功/失败的任务调用，快速原封不动地拉取当初传递的超长混合嵌套属性（如预设的模板、分辨率限制等）。
        这在页面交互上能够轻松实现类似 "基于此配置重新制作/修改参数重跑" 的流畅体验！
        
        Returns:
            Dict[str, Any]: 原始请求传参集合，提取自元数据 "input" 层。不存在时降级为 None。
        """
        metadata = await self.persistence.load_task_metadata(task_id)
        if not metadata:
            logger.warning(f"Task {task_id} not found for duplication")
            return None
        
        input_params = metadata.get("input", {})
        logger.info(f"Duplicated task {task_id} parameters")
        
        return input_params
    
    async def rebuild_index(self):
        """修复手段：请求重新全面洗牌和挂载持久存储区上的索引缓存服务体系。"""
        await self.persistence.rebuild_index()
    
    # ========================================================================
    # Future Extensions (Phase 3) / 规划阶段中的超前特性预埋挂载点
    # ========================================================================
    
    async def regenerate_frame(
        self,
        task_id: str,
        frame_index: int,
        **override_params
    ) -> Optional[str]:
        """
        (预留) 重制特定某个局部帧画面的 API 方法入口。
        解决因为其中一帧生图出错而不必全量回炉花费十几分钟跑完所有操作的痛点。
        """
        logger.warning("regenerate_frame is not implemented yet (Phase 3 feature)")
        return None
    
    async def export_task(self, task_id: str, export_path: str) -> Optional[str]:
        """
        (预留) 一键打包带走整个工程级项目（含素材，视频与分片，大纲 json）。
        便于开发者互相迁移作品结构工程以继续调试。
        """
        logger.warning("export_task is not implemented yet (Phase 3 feature)")
        return None
