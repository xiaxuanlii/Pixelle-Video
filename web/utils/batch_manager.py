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
Lightweight batch manager for Streamlit (Simplified YAGNI version)

Streamlit 极简批量任务管理器 (YAGNI 原则)。
为 Web UI 提供了批量同时生成多个同配置不同主题视频的编排循环。
"""
import time
import traceback
from typing import List, Dict, Any, Optional, Callable
from loguru import logger


class SimpleBatchManager:
    """
    极简的矩阵批量任务管理器。
    
    设计原则:
    1. 仅支持纯 AI 提示词“发散生成模式”（因为每个视频只需要提供一句主题）。
    2. 所有批量下发的视频共享完全一样的高级参数配置（相同的配乐、模版和画风）。
    3. 不搞复杂的 CSV 上传和繁重的校验，简单地按换行符切分用户输入后，以 for 循环逐个排队等待生成。
    """
    
    def __init__(self):
        self.results = []        # 成功队列收集
        self.errors = []         # 失败队列收集
        self.current_index = 0   # 当前正执行的指针
        self.total_count = 0     # 任务池总数
    
    def execute_batch(
        self,
        pixelle_video,
        topics: List[str],
        shared_config: Dict[str, Any],
        overall_progress_callback: Optional[Callable] = None,
        task_progress_callback_factory: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        按照公共配置对一组主题进行遍历生成。
        
        Args:
            pixelle_video: PixelleVideoCore 的全局核心服务实例。
            topics: 用户输入的每一行独立的主题文本列表。
            shared_config: 这一批次共享的视频生成配置表 (包含 BGM、模板、LLM提示等)。
            overall_progress_callback: (可选) 向页面汇报大盘进度（“正在生成第 2 个，共 10 个”）的函数。
            task_progress_callback_factory: (可选) 为每个具体任务生产专属细粒度进度回调的工厂函数。
        
        Returns:
            Dict: 包含了处理完毕的成功明细、失败报错及整体数据统计的字典反馈。
        """
        self.results = []
        self.errors = []
        self.total_count = len(topics)
        
        logger.info(f"Starting batch generation: {self.total_count} topics")
        
        for idx, topic in enumerate(topics, 1):
            self.current_index = idx
            
            # 向页面上报总体大的外围进度
            if overall_progress_callback:
                overall_progress_callback(
                    current=idx,
                    total=self.total_count,
                    topic=topic
                )
            
            try:
                logger.info(f"Task {idx}/{self.total_count} started: {topic}")
                
                # 尝试取出可选的统一标题前缀修饰
                title_prefix = shared_config.get("title_prefix")
                
                # 开始组装当前这一个小任务所需的最终请求字典
                task_params = {
                    "text": topic,        # 主题就是它要生成的入参
                    "mode": "generate",   # 批量任务固定采用 LLM 自由发散剧本的模式
                }
                
                # 将分享的公共参数剔除掉 None 空值后全部透传给底层服务
                for key, value in shared_config.items():
                    if key != "title_prefix" and value is not None:
                        task_params[key] = value
                
                # 生成拼接该视频的真实落盘标题
                if title_prefix:
                    task_params["title"] = f"{title_prefix} - {topic}"
                else:
                    task_params["title"] = topic
                
                # 如果 UI 层提供了进度条监控，注入生成
                if task_progress_callback_factory:
                    task_params["progress_callback"] = task_progress_callback_factory(idx, topic)
                
                # 使用桥接方法在同步函数中唤起并阻塞等待异步生成的成果
                from web.utils.async_helpers import run_async
                result = run_async(pixelle_video.generate_video(**task_params))
                
                # 解析获取到的输出文件，倒推回对应的任务独立 UUID 目录名
                from pathlib import Path
                task_id = Path(result.video_path).parent.name
                
                # 将正确的结果录入到总盘面中
                self.results.append({
                    "index": idx,
                    "topic": topic,
                    "task_id": task_id,
                    "video_path": result.video_path,
                    "status": "success"
                })
                
                logger.info(f"Task {idx}/{self.total_count} completed: {result.video_path}")
                
            except Exception as e:
                # 某个视频出错失败，只记录错误轨迹并不应打断外层循环的后续生成任务
                error_msg = str(e)
                error_trace = traceback.format_exc()
                
                logger.error(f"Task {idx}/{self.total_count} failed: {error_msg}")
                logger.debug(f"Error traceback:\n{error_trace}")
                
                self.errors.append({
                    "index": idx,
                    "topic": topic,
                    "error": error_msg,
                    "traceback": error_trace,
                    "status": "failed"
                })
                
                continue
        
        success_count = len(self.results)
        failed_count = len(self.errors)
        
        logger.info(
            f"Batch generation completed: "
            f"{success_count}/{self.total_count} succeeded, "
            f"{failed_count} failed"
        )
        
        return {
            "results": self.results,
            "errors": self.errors,
            "total_count": self.total_count,
            "success_count": success_count,
            "failed_count": failed_count
        }
