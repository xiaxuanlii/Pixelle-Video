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
Linear Video Pipeline Base Class

线性视频生成流水线的基类模块。
此模块利用“模板方法”（Template Method）设计模式定义了视频生成的标准工作流骨架。
同时引入了 `PipelineContext` 用于整个生命周期中的状态管理。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from loguru import logger

from pixelle_video.pipelines.base import BasePipeline
from pixelle_video.models.storyboard import (
    Storyboard,
    VideoGenerationResult,
    StoryboardConfig
)
from pixelle_video.models.progress import ProgressEvent


@dataclass
class PipelineContext:
    """
    流水线执行上下文对象。
    
    该对象在 LinearVideoPipeline 的生命周期各个步骤之间传递，用于保存所有的输入参数、
    中间生成状态以及最终的结果数据。
    """
    # === Input / 输入数据 ===
    input_text: str
    params: Dict[str, Any]
    progress_callback: Optional[Callable[[ProgressEvent], None]] = None
    
    # === Task State / 任务状态 ===
    task_id: Optional[str] = None
    task_dir: Optional[str] = None
    
    # === Content / 文本内容 ===
    title: Optional[str] = None
    narrations: List[str] = field(default_factory=list)
    
    # === Visuals / 视觉计划 ===
    image_prompts: List[Optional[str]] = field(default_factory=list)
    
    # === Configuration & Storyboard / 配置与分镜剧本 ===
    config: Optional[StoryboardConfig] = None
    storyboard: Optional[Storyboard] = None
    
    # === Output / 最终输出 ===
    final_video_path: Optional[str] = None
    result: Optional[VideoGenerationResult] = None


class LinearVideoPipeline(BasePipeline):
    """
    基于模板方法设计模式的线性视频生成流水线基类。
    
    该类将复杂的视频生成过程编排为清晰的 8 个生命周期步骤：
    1. setup_environment (初始化环境与任务目录)
    2. generate_content (生成或处理脚本/旁白)
    3. determine_title (确定或生成视频标题)
    4. plan_visuals (生成画面提示词或视觉计划)
    5. initialize_storyboard (初始化分镜剧本对象)
    6. produce_assets (核心处理：生成音视频资产并渲染画面)
    7. post_production (后期制作：拼接视频并添加 BGM)
    8. finalize (流程收尾：持久化元数据并返回结果)
    
    子类应根据具体的业务需求重写特定的步骤，同时保持整体工作流结构的统一。
    """
    
    async def __call__(
        self,
        text: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        **kwargs
    ) -> VideoGenerationResult:
        """
        执行基于模板方法的完整生成流水线。
        """
        # 1. 初始化上下文对象
        ctx = PipelineContext(
            input_text=text,
            params=kwargs,
            progress_callback=progress_callback
        )
        
        try:
            # === Phase 1: Preparation / 准备阶段 ===
            await self.setup_environment(ctx)
            
            # === Phase 2: Content Creation / 内容创作阶段 ===
            await self.generate_content(ctx)
            await self.determine_title(ctx)
            
            # === Phase 3: Visual Planning / 视觉策划阶段 ===
            await self.plan_visuals(ctx)
            await self.initialize_storyboard(ctx)
            
            # === Phase 4: Asset Production / 资产生产核心阶段 ===
            await self.produce_assets(ctx)
            
            # === Phase 5: Post Production / 后期处理阶段 ===
            await self.post_production(ctx)
            
            # === Phase 6: Finalization / 交付与收尾阶段 ===
            return await self.finalize(ctx)
            
        except Exception as e:
            await self.handle_exception(ctx, e)
            raise

    # ==================== Lifecycle Methods / 生命周期方法 ====================
    
    async def setup_environment(self, ctx: PipelineContext):
        """步骤 1：初始化任务独立目录和基础环境"""
        pass
        
    async def generate_content(self, ctx: PipelineContext):
        """步骤 2：生成或切分出用于各分镜的旁白脚本"""
        pass
        
    async def determine_title(self, ctx: PipelineContext):
        """步骤 3：确定或利用 AI 总结视频的主标题"""
        pass
        
    async def plan_visuals(self, ctx: PipelineContext):
        """步骤 4：基于各个旁白设计对应的画面提示词"""
        pass
        
    async def initialize_storyboard(self, ctx: PipelineContext):
        """步骤 5：将前面生成的所有元数据拼装为 Storyboard 分镜剧本对象"""
        pass
        
    async def produce_assets(self, ctx: PipelineContext):
        """步骤 6：核心耗时步骤。调用底层引擎生成配音、配图/视频，并渲染出排版好的视频帧片段"""
        pass
        
    async def post_production(self, ctx: PipelineContext):
        """步骤 7：视频拼接与混入背景音乐"""
        pass
        
    async def finalize(self, ctx: PipelineContext) -> VideoGenerationResult:
        """步骤 8：持久化工作流历史记录并打包返回最终结果"""
        raise NotImplementedError("finalize must be implemented by subclass")

    async def handle_exception(self, ctx: PipelineContext, error: Exception):
        """生命周期异常时的全局回调挂载点"""
        logger.error(f"Pipeline execution failed: {error}")
