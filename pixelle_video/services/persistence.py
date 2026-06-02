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
Persistence Service

持久化文件系统服务模块。
专门负责将流水线流转过程中的所有中间元数据（请求参数、耗时状况、各分镜剧本记录）
格式化落地为 JSON 保存到本地硬盘。这是项目能够“回放”和重构前端历史页面的基石。
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from pixelle_video.models.storyboard import Storyboard, StoryboardFrame, StoryboardConfig, ContentMetadata


class PersistenceService:
    """
    基于 JSON 和文件系统的核心任务状态存储与持久化服务。
    
    底层会组织并维护如下干净、独立的单任务沙盒目录格式：
        output/
        └── {task_id}/
            ├── metadata.json          # 记录全局输入参数、结果特征和部分核心运行时设置
            ├── storyboard.json        # 极其详细的剧本树形对象 (所有的图文提示词, 素材地址等)
            ├── final.mp4              # [业务方写入] 最后的交付合并成品
            └── frames/                # [业务方写入] 每一步的音频、图片、单切片
                ├── 01_audio.mp3
                ├── 01_image.png
                └── ...
                
    使用示例:
        persistence = PersistenceService()
        
        # 序列化存储元数据
        await persistence.save_task_metadata(task_id, metadata)
        
        # 分页模糊查询任务列表（将遍历 metadata 并借助预构建的 .index.json）
        tasks = await persistence.list_tasks(status="completed", limit=50)
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        初始化持久化服务。
        
        Args:
            output_dir: 存放所有生成任务的主根目录名称 (默认 "output")。
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 借助该隐藏索引文件，防止未来产出十万条视频任务后全盘遍历导致文件系统卡死
        self.index_file = self.output_dir / ".index.json"
        self._ensure_index()
    
    def get_task_dir(self, task_id: str) -> Path:
        """获取专属某个 task_id 的相对工作区地址"""
        return self.output_dir / task_id
    
    def get_metadata_path(self, task_id: str) -> Path:
        """获取专属某个任务的全局元数据 JSON 地址"""
        return self.get_task_dir(task_id) / "metadata.json"
    
    def get_storyboard_path(self, task_id: str) -> Path:
        """获取专属某个任务的具体剧本分镜 JSON 地址"""
        return self.get_task_dir(task_id) / "storyboard.json"
    
    # ========================================================================
    # Metadata Operations / 元数据持久化写入相关
    # ========================================================================
    
    async def save_task_metadata(
        self,
        task_id: str,
        metadata: Dict[str, Any]
    ):
        """
        保存任务级别的元数据（入参、执行时限和最终结果）。
        
        Args:
            task_id: 任务标识 UUID。
            metadata: 需要存盘的字典，格式要求如下：
                {
                    "task_id": str,
                    "created_at": str,
                    "completed_at": str (可选),
                    "status": str,
                    "input": dict,
                    "result": dict (可选),
                    "config": dict
                }
        """
        try:
            task_dir = self.get_task_dir(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_path = self.get_metadata_path(task_id)
            metadata["task_id"] = task_id
            
            # 将运行时的 datetime 强制转义为 ISO 以保证跨平台时区识别解析
            if "created_at" in metadata and isinstance(metadata["created_at"], datetime):
                metadata["created_at"] = metadata["created_at"].isoformat()
            if "completed_at" in metadata and isinstance(metadata["completed_at"], datetime):
                metadata["completed_at"] = metadata["completed_at"].isoformat()
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved task metadata: {task_id}")
            
            # 同时将关键查询信息抽出存入顶层的全局快速查询索引表中
            await self._update_index_for_task(task_id, metadata)
            
        except Exception as e:
            logger.error(f"Failed to save task metadata {task_id}: {e}")
            raise
    
    async def load_task_metadata(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        从物理磁盘唤醒读取元数据 JSON 文件。
        """
        try:
            metadata_path = self.get_metadata_path(task_id)
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load task metadata {task_id}: {e}")
            return None
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """
        向外提供的一键更新任务状态及失败日志的方法。
        主要供后台的任务执行管理器调用，无需重复组织字典即可覆盖 status。
        """
        try:
            metadata = await self.load_task_metadata(task_id)
            if not metadata:
                logger.warning(f"Cannot update status: task {task_id} not found")
                return
            
            metadata["status"] = status
            
            if status in ["completed", "failed", "cancelled"]:
                metadata["completed_at"] = datetime.now().isoformat()
            
            if error:
                metadata["error"] = error
            
            await self.save_task_metadata(task_id, metadata)
            
        except Exception as e:
            logger.error(f"Failed to update task status {task_id}: {e}")
    
    # ========================================================================
    # Storyboard Operations / 分镜剧本结构树化写入相关
    # ========================================================================
    
    async def save_storyboard(
        self,
        task_id: str,
        storyboard: Storyboard
    ):
        """
        持久化分镜序列对象为标准 JSON。
        会利用本类内的辅助方法对 Pydantic 及 Dataclass 进行安全序列化。
        """
        try:
            task_dir = self.get_task_dir(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)
            
            storyboard_path = self.get_storyboard_path(task_id)
            
            storyboard_dict = self._storyboard_to_dict(storyboard)
            
            with open(storyboard_path, "w", encoding="utf-8") as f:
                json.dump(storyboard_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved storyboard: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to save storyboard {task_id}: {e}")
            raise
    
    async def load_storyboard(self, task_id: str) -> Optional[Storyboard]:
        """
        重新唤醒加载历史的图文声分离资源表及生成足迹。
        """
        try:
            storyboard_path = self.get_storyboard_path(task_id)
            
            if not storyboard_path.exists():
                return None
            
            with open(storyboard_path, "r", encoding="utf-8") as f:
                storyboard_dict = json.load(f)
            
            storyboard = self._dict_to_storyboard(storyboard_dict)
            return storyboard
            
        except Exception as e:
            logger.error(f"Failed to load storyboard {task_id}: {e}")
            return None
    
    # ========================================================================
    # Task Listing & Querying / 历史回溯列表与筛选工具
    # ========================================================================
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        全局遍历获取所有产生的业务任务（按时间倒排）。
        注意：如果数量过大此方法可能有性能瓶颈，建议改用依托缓存表的 `list_tasks_paginated`。
        """
        try:
            index = self._load_index()
            tasks = index.get("tasks", [])

            # Filter by status / 按状态筛选
            if status:
                tasks = [t for t in tasks if t.get("status") == status]

            # Sort by created_at descending / 按创建时间倒序排列
            tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)

            # Apply pagination / 应用分页
            return tasks[offset:offset + limit]

        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []
    
    async def task_exists(self, task_id: str) -> bool:
        """快速判断一个生成的流水号文件夹是否实际存活"""
        return self.get_task_dir(task_id).exists()

    async def delete_task(self, task_id: str):
        """
        危险操作：清空抹除指定生成的任务所有的上下文及其产生的所有小视频、录音和长视频产物。
        """
        try:
            task_dir = self.get_task_dir(task_id)

            if task_dir.exists():
                import shutil
                shutil.rmtree(task_dir)
                logger.info(f"Deleted task: {task_id}")

        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise

    # ========================================================================
    # Serialization Helpers / 辅助类：对象字典相互清洗序列化
    # ========================================================================
    
    def _storyboard_to_dict(self, storyboard: Storyboard) -> Dict[str, Any]:
        """将 Dataclass Storyboard 扁平化安全转为 Dict"""
        return {
            "title": storyboard.title,
            "config": self._config_to_dict(storyboard.config),
            "frames": [self._frame_to_dict(frame) for frame in storyboard.frames],
            "content_metadata": self._content_metadata_to_dict(storyboard.content_metadata) if storyboard.content_metadata else None,
            "final_video_path": storyboard.final_video_path,
            "total_duration": storyboard.total_duration,
            "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
            "completed_at": storyboard.completed_at.isoformat() if storyboard.completed_at else None,
        }
    
    def _dict_to_storyboard(self, data: Dict[str, Any]) -> Storyboard:
        """从扁平 JSON 反射重新还原为可交互的业务 Dataclass"""
        return Storyboard(
            title=data["title"],
            config=self._dict_to_config(data["config"]),
            frames=[self._dict_to_frame(frame_data) for frame_data in data["frames"]],
            content_metadata=self._dict_to_content_metadata(data["content_metadata"]) if data.get("content_metadata") else None,
            final_video_path=data.get("final_video_path"),
            total_duration=data.get("total_duration", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )
    
    def _config_to_dict(self, config: StoryboardConfig) -> Dict[str, Any]:
        return {
            "task_id": config.task_id,
            "n_storyboard": config.n_storyboard,
            "min_narration_words": config.min_narration_words,
            "max_narration_words": config.max_narration_words,
            "min_image_prompt_words": config.min_image_prompt_words,
            "max_image_prompt_words": config.max_image_prompt_words,
            "video_fps": config.video_fps,
            "tts_inference_mode": config.tts_inference_mode,
            "voice_id": config.voice_id,
            "tts_workflow": config.tts_workflow,
            "tts_speed": config.tts_speed,
            "ref_audio": config.ref_audio,
            "media_width": config.media_width,
            "media_height": config.media_height,
            "media_workflow": config.media_workflow,
            "frame_template": config.frame_template,
            "template_params": config.template_params,
        }
    
    def _dict_to_config(self, data: Dict[str, Any]) -> StoryboardConfig:
        return StoryboardConfig(
            task_id=data.get("task_id"),
            n_storyboard=data.get("n_storyboard", 5),
            min_narration_words=data.get("min_narration_words", 5),
            max_narration_words=data.get("max_narration_words", 20),
            min_image_prompt_words=data.get("min_image_prompt_words", 30),
            max_image_prompt_words=data.get("max_image_prompt_words", 60),
            video_fps=data.get("video_fps", 30),
            tts_inference_mode=data.get("tts_inference_mode", "local"),
            voice_id=data.get("voice_id"),
            tts_workflow=data.get("tts_workflow"),
            tts_speed=data.get("tts_speed"),
            ref_audio=data.get("ref_audio"),
            media_width=data.get("media_width", data.get("image_width", 1024)),
            media_height=data.get("media_height", data.get("image_height", 1024)),
            media_workflow=data.get("media_workflow", data.get("image_workflow")),
            frame_template=data.get("frame_template", "1080x1920/image_default.html"),
            template_params=data.get("template_params"),
        )
    
    def _frame_to_dict(self, frame: StoryboardFrame) -> Dict[str, Any]:
        return {
            "index": frame.index,
            "narration": frame.narration,
            "image_prompt": frame.image_prompt,
            "audio_path": frame.audio_path,
            "media_type": frame.media_type,
            "image_path": frame.image_path,
            "video_path": frame.video_path,
            "composed_image_path": frame.composed_image_path,
            "video_segment_path": frame.video_segment_path,
            "duration": frame.duration,
            "created_at": frame.created_at.isoformat() if frame.created_at else None,
        }
    
    def _dict_to_frame(self, data: Dict[str, Any]) -> StoryboardFrame:
        return StoryboardFrame(
            index=data["index"],
            narration=data["narration"],
            image_prompt=data["image_prompt"],
            audio_path=data.get("audio_path"),
            media_type=data.get("media_type"),
            image_path=data.get("image_path"),
            video_path=data.get("video_path"),
            composed_image_path=data.get("composed_image_path"),
            video_segment_path=data.get("video_segment_path"),
            duration=data.get("duration", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )
    
    def _content_metadata_to_dict(self, metadata: ContentMetadata) -> Dict[str, Any]:
        return {
            "title": metadata.title,
            "author": metadata.author,
            "subtitle": metadata.subtitle,
            "genre": metadata.genre,
            "summary": metadata.summary,
            "publication_year": metadata.publication_year,
            "cover_url": metadata.cover_url,
        }
    
    def _dict_to_content_metadata(self, data: Dict[str, Any]) -> ContentMetadata:
        return ContentMetadata(
            title=data["title"],
            author=data.get("author"),
            subtitle=data.get("subtitle"),
            genre=data.get("genre"),
            summary=data.get("summary"),
            publication_year=data.get("publication_year"),
            cover_url=data.get("cover_url"),
        )
    
    # ========================================================================
    # Index Management / 为缓解磁盘压力准备的高性能大盘缓存记录表
    # ========================================================================
    
    def _ensure_index(self):
        """安全保护：如果用于查询缓冲的索列表没被找到，则自动生成初始的空状态表"""
        if not self.index_file.exists():
            self._save_index({"version": "1.0", "tasks": []})
    
    def _load_index(self) -> Dict[str, Any]:
        """将缓存数据库（极小尺寸JSON，常驻内存安全）载入提供遍历服务"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return {"version": "1.0", "tasks": []}
    
    def _save_index(self, index_data: Dict[str, Any]):
        """序列化写入保护索引池表，将打上记录最后变更的时间"""
        try:
            index_data["last_updated"] = datetime.now().isoformat()
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    async def _update_index_for_task(self, task_id: str, metadata: Dict[str, Any]):
        """在特定项目流转保存时被回调的方法，对高速索引缓存表实现追加或者复写。"""
        index = self._load_index()
        
        title = metadata.get("input", {}).get("title")
        if not title or title == "":
            storyboard = await self.load_storyboard(task_id)
            if storyboard and storyboard.title:
                title = storyboard.title
            else:
                input_text = metadata.get("input", {}).get("text", "")
                if input_text:
                    title = input_text[:30] + ("..." if len(input_text) > 30 else "")
                else:
                    title = "Untitled"
        
        index_entry = {
            "task_id": task_id,
            "created_at": metadata.get("created_at"),
            "completed_at": metadata.get("completed_at"),
            "status": metadata.get("status", "unknown"),
            "title": title,
            "duration": metadata.get("result", {}).get("duration", 0),
            "n_frames": metadata.get("result", {}).get("n_frames", 0),
            "file_size": metadata.get("result", {}).get("file_size", 0),
            "video_path": metadata.get("result", {}).get("video_path"),
        }
        
        tasks = index.get("tasks", [])
        existing_idx = next((i for i, t in enumerate(tasks) if t["task_id"] == task_id), None)
        
        if existing_idx is not None:
            tasks[existing_idx] = index_entry
        else:
            tasks.append(index_entry)
        
        index["tasks"] = tasks
        self._save_index(index)
    
    async def rebuild_index(self):
        """修复手段：当文件系统内手动发生破坏时，遍历扫描一切 output 数据并进行耗时的全局重编译索引构建。"""
        logger.info("Rebuilding task index...")
        index = {"version": "1.0", "tasks": []}
        
        for task_dir in self.output_dir.iterdir():
            if not task_dir.is_dir() or task_dir.name.startswith("."):
                continue
            
            task_id = task_dir.name
            metadata = await self.load_task_metadata(task_id)
            
            if metadata:
                title = metadata.get("input", {}).get("title")
                if not title or title == "":
                    storyboard = await self.load_storyboard(task_id)
                    if storyboard and storyboard.title:
                        title = storyboard.title
                    else:
                        input_text = metadata.get("input", {}).get("text", "")
                        if input_text:
                            title = input_text[:30] + ("..." if len(input_text) > 30 else "")
                        else:
                            title = "Untitled"
                
                index["tasks"].append({
                    "task_id": task_id,
                    "created_at": metadata.get("created_at"),
                    "completed_at": metadata.get("completed_at"),
                    "status": metadata.get("status", "unknown"),
                    "title": title,
                    "duration": metadata.get("result", {}).get("duration", 0),
                    "n_frames": metadata.get("result", {}).get("n_frames", 0),
                    "file_size": metadata.get("result", {}).get("file_size", 0),
                    "video_path": metadata.get("result", {}).get("video_path"),
                })
        
        self._save_index(index)
        logger.info(f"Index rebuilt: {len(index['tasks'])} tasks")
    
    # ========================================================================
    # Paginated Listing / 面向列表的游标查询
    # ========================================================================
    
    async def list_tasks_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        利用高度索引缓存服务快速分页查询展示视频处理履历列表。
        
        Returns:
            Dict 包含总条数、页数、单页的数据包裹的组装分页对象。
        """
        index = self._load_index()
        tasks = index.get("tasks", [])
        
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        
        reverse = (sort_order == "desc")
        if sort_by in ["created_at", "completed_at"]:
            tasks.sort(
                key=lambda t: datetime.fromisoformat(t.get(sort_by, "1970-01-01T00:00:00")),
                reverse=reverse
            )
        elif sort_by in ["title", "duration", "n_frames"]:
            tasks.sort(key=lambda t: t.get(sort_by, ""), reverse=reverse)
        
        total = len(tasks)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_tasks = tasks[start_idx:end_idx]
        
        return {
            "tasks": page_tasks,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    
    # ========================================================================
    # Statistics / 大盘业务看板分析
    # ========================================================================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """为看板和首页提供针对当前磁盘消耗的总体视频合成量及处理情况的总计度量。"""
        index = self._load_index()
        tasks = index.get("tasks", [])
        
        stats = {
            "total_tasks": len(tasks),
            "completed": len([t for t in tasks if t.get("status") == "completed"]),
            "failed": len([t for t in tasks if t.get("status") == "failed"]),
            "total_duration": sum(t.get("duration", 0) for t in tasks),
            "total_size": sum(t.get("file_size", 0) for t in tasks),
        }
        
        return stats
    
    # ========================================================================
    # Delete Task
    # ========================================================================
    
    async def delete_task(self, task_id: str) -> bool:
        """
        危险操作：安全擦除包含文件和索引表的整个任务目录所有流转资产痕迹。
        """
        try:
            import shutil
            
            task_dir = self.get_task_dir(task_id)
            if task_dir.exists():
                shutil.rmtree(task_dir)
                logger.info(f"Deleted task directory: {task_dir}")
            
            index = self._load_index()
            tasks = index.get("tasks", [])
            tasks = [t for t in tasks if t["task_id"] != task_id]
            index["tasks"] = tasks
            self._save_index(index)
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False
