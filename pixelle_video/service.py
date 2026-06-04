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
Pixelle-Video Core - Service Layer

此模块是整个视频生成后端的核心服务层（门面模式）。
它负责初始化和统一管理所有的基础能力子服务（如 LLM、TTS、媒体生成、历史记录），
并按需进行底层生图/生视频引擎（ComfyKit）的懒加载和热重载。
"""

import hashlib
import json
from typing import Optional

from loguru import logger
from comfykit import ComfyKit

from pixelle_video.config import config_manager
from pixelle_video.services.llm_service import LLMService
from pixelle_video.services.tts_service import TTSService
from pixelle_video.services.media import MediaService
from pixelle_video.services.api_media import APIProviderMediaService
from pixelle_video.services.image_analysis import ImageAnalysisService
from pixelle_video.services.video_analysis import VideoAnalysisService
from pixelle_video.services.api_asset_analysis import APIAssetAnalysisService
from pixelle_video.services.video import VideoService
from pixelle_video.services.frame_processor import FrameProcessor
from pixelle_video.services.persistence import PersistenceService
from pixelle_video.services.history_manager import HistoryManager
from pixelle_video.pipelines.standard import StandardPipeline
from pixelle_video.pipelines.custom import CustomPipeline
from pixelle_video.pipelines.asset_based import AssetBasedPipeline


class PixelleVideoCore:
    """
    Pixelle-Video Core - 核心服务聚合类
    
    采用门面模式（Facade），为应用层（如 API 路由）提供调用底层原子能力
    以及运行高级工作流（Pipelines）的统一入口。
    
    使用示例:
        from pixelle_video import pixelle_video
        
        # 1. 系统启动时初始化
        await pixelle_video.initialize()
        
        # 2. 直接调用各项原子能力
        answer = await pixelle_video.llm("解释一下什么是原子习惯")
        audio = await pixelle_video.tts("你好，世界")
        media = await pixelle_video.media(prompt="一只可爱的猫咪")
        
    简化架构图:
        PixelleVideoCore (本类)
          ├── config (全局配置管理器)
          ├── llm (语言模型服务 - 直接封装大厂 SDK)
          ├── tts (语音合成服务 - 封装 ComfyKit/本地脚本)
          ├── media (媒体生成服务 - 封装 ComfyKit，支持生图和生视频)
          └── pipelines (视频生成流水线)
              ├── standard (默认全自动标准流水线)
              ├── custom (自定义流水线扩展点)
              └── asset_based (基于现有素材的流水线)
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化核心服务类的骨架。
        注意：此时并不会立刻连接到底层引擎，实际的初始化在 `initialize()` 方法中。
        
        Args:
            config_path: 配置文件路径（目前主要依赖全局单例 config_manager）
        """
        # 使用全局配置管理器单例的字典快照
        self.config = config_manager.config.to_dict()
        self._initialized = False
        
        # ComfyKit 懒加载机制相关属性（在首次真正需要调用绘画/TTS工作流时创建）
        # 并且支持在配置发生变化时自动销毁重建
        self._comfykit: Optional[ComfyKit] = None
        self._comfykit_config_hash: Optional[str] = None
        
        # 核心子服务声明（将在 initialize() 中被实例化）
        self.llm: Optional[LLMService] = None
        self.tts: Optional[TTSService] = None
        self.media: Optional[MediaService] = None
        self.api_media: Optional[APIProviderMediaService] = None
        self.video: Optional[VideoService] = None
        self.frame_processor: Optional[FrameProcessor] = None
        self.persistence: Optional[PersistenceService] = None
        self.history: Optional[HistoryManager] = None
        
        # 视频生成工作流集合（字典: 工作流名称 -> 工作流实例）
        self.pipelines = {}
        
        # 默认的视频生成入口函数（为了向后兼容早期的 API 调用方式）
        self.generate_video = None
    
    def _get_comfykit_config(self) -> dict:
        """
        从全局配置管理器中提取出 ComfyKit 客户端所需的专门配置。
        
        Returns:
            dict: 提取出的 ComfyKit 配置字典。
        """
        # 重新读取全局配置快照（支持配置文件的热重载机制）
        self.config = config_manager.config.to_dict()
        
        comfyui_config = self.config.get("comfyui", {})
        kit_config = {}
        
        # 提取关键连接信息
        if comfyui_config.get("comfyui_url"):
            kit_config["comfyui_url"] = comfyui_config["comfyui_url"]
        if comfyui_config.get("comfyui_api_key"):
            kit_config["api_key"] = comfyui_config["comfyui_api_key"]
        if comfyui_config.get("runninghub_api_key"):
            kit_config["runninghub_api_key"] = comfyui_config["runninghub_api_key"]
            
        # 只有当 instance_type 非空时才传递给 ComfyKit
        instance_type = comfyui_config.get("runninghub_instance_type")
        if instance_type and instance_type.strip():
            kit_config["runninghub_instance_type"] = instance_type
        
        return kit_config
    
    def _compute_comfykit_config_hash(self, config: dict) -> str:
        """
        计算 ComfyKit 配置的 MD5 哈希值，用于快速检测配置是否发生变更。
        
        Args:
            config: ComfyKit 配置字典
        
        Returns:
            str: 排序后的字典计算出的 MD5 字符串
        """
        # 对字典的 key 排序以保证相同配置产生稳定的哈希
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    async def _get_or_create_comfykit(self) -> ComfyKit:
        """
        获取或创建 ComfyKit 实例（懒加载 + 热重载支持）。
        
        此方法的功能：
        1. 首次调用时创建 ComfyKit 实例（懒加载，加快系统初始启动速度）。
        2. 后续调用时，检测配置文件的哈希值是否发生变化，若变化则销毁旧实例并基于新配置重建。
        3. 确保底层长连接（如 WebSocket）被正确关闭。
        
        Returns:
            ComfyKit: 就绪的 ComfyKit 客户端实例。
        """
        current_config = self._get_comfykit_config()
        current_hash = self._compute_comfykit_config_hash(current_config)
        
        # 检查是否需要初次创建或因配置变更需要重建
        if self._comfykit is None or self._comfykit_config_hash != current_hash:
            # 安全关闭并清理旧的连接实例
            if self._comfykit is not None:
                logger.info("🔄 ComfyUI configuration changed, recreating ComfyKit instance...")
                try:
                    await self._comfykit.close()
                except Exception as e:
                    logger.warning(f"Failed to close old ComfyKit instance: {e}")
                self._comfykit = None
            
            # 使用最新的配置建立新的连接实例
            logger.info("✨ Creating ComfyKit instance...")
            logger.debug(f"ComfyKit config: {current_config}")
            self._comfykit = ComfyKit(**current_config)
            self._comfykit_config_hash = current_hash
            logger.info("✅ ComfyKit instance created")
        
        return self._comfykit
    
    async def initialize(self):
        """
        初始化所有核心能力和子服务。
        
        在开始使用核心处理能力之前，必须显式调用此异步方法。
        注意：此处并不会立刻初始化耗时的 ComfyKit，而是将其延迟到第一次实际调用底层生图/TTS时。
        """
        if self._initialized:
            logger.warning("Pixelle-Video already initialized")
            return
        
        logger.info("🚀 Initializing Pixelle-Video...")
        
        # 1. 实例化各个子服务，并将核心控制类的引用 (core=self) 传递给它们
        # 这样子服务内部也能按需获取懒加载的 ComfyKit 客户端
        self.llm = LLMService(self.config)
        self.tts = TTSService(self.config, core=self)
        self.api_media = APIProviderMediaService(self.config, core=self)
        self.media = MediaService(self.config, core=self)
        self.image = self.media  # 保留旧版的别名，向后兼容
        self.image_analysis = ImageAnalysisService(self.config, core=self)
        self.video_analysis = VideoAnalysisService(self.config, core=self)
        self.api_asset_analysis = APIAssetAnalysisService(self.config, core=self)
        self.video = VideoService()
        self.frame_processor = FrameProcessor(self)
        self.persistence = PersistenceService(output_dir="output")
        self.history = HistoryManager(self.persistence)
        
        # 2. 注册视频生成流水线 (Pipelines)
        self.pipelines = {
            "standard": StandardPipeline(self),
            "custom": CustomPipeline(self),
            "asset_based": AssetBasedPipeline(self),
        }
        logger.info(f"📹 Registered pipelines: {', '.join(self.pipelines.keys())}")
        
        # 3. 设置默认的视频生成包装函数 (绑定到实例属性)
        self.generate_video = self._create_generate_video_wrapper()
        
        self._initialized = True
        logger.info("✅ Pixelle-Video initialized successfully\n")
    
    async def cleanup(self):
        """
        清理和释放资源。
        
        主要负责断开与 ComfyUI 或 RunningHub 后端保持的网络连接（WebSocket 监听等）。
        通常在系统优雅关闭（Shutdown）时被调用。
        """
        if self._comfykit:
            logger.info("🧹 Closing ComfyKit session...")
            try:
                await self._comfykit.close()
                logger.info("✅ ComfyKit session closed")
            except Exception as e:
                logger.error(f"Failed to close ComfyKit: {e}")
            finally:
                self._comfykit = None
                self._comfykit_config_hash = None
    
    async def __aenter__(self):
        """支持 async with 上下文管理器用法：进入"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持 async with 上下文管理器用法：退出并自动清理"""
        await self.cleanup()
    
    def _create_generate_video_wrapper(self):
        """
        工厂方法：创建一个带智能分发功能的视频生成外壳函数。
        
        这既保证了旧代码里直接调用 `pixelle_video.generate_video(...)` 依然有效，
        又引入了 `pipeline` 参数，可以根据需要将请求分发给特定的流水线处理对象。
        """
        async def generate_video_wrapper(
            text: str,
            pipeline: str = "standard",
            **kwargs
        ):
            """
            使用指定的工作流策略（Pipeline）执行端到端的视频生成。
            
            Args:
                text: 用户的核心提示文本或脚本内容。
                pipeline: 流水线的名称，默认为 "standard"。
                **kwargs: 透传给具体流水线的配置参数。
            
            Returns:
                VideoGenerationResult: 视频生成的结果模型。
            
            Raises:
                ValueError: 当请求了一个未注册的 pipeline 时。
            """
            if pipeline not in self.pipelines:
                available = ", ".join(self.pipelines.keys())
                raise ValueError(
                    f"Unknown pipeline: '{pipeline}'. "
                    f"Available pipelines: {available}"
                )
            
            pipeline_instance = self.pipelines[pipeline]
            # 实际上是调用相应 Pipeline 对象的 __call__ 方法
            return await pipeline_instance(text=text, **kwargs)
        
        return generate_video_wrapper
    
    @property
    def project_name(self) -> str:
        """从配置中获取当前项目名称的快捷属性"""
        return self.config.get("project_name", "Pixelle-Video")
    
    def __repr__(self) -> str:
        """友好的字符串调试表示"""
        status = "initialized" if self._initialized else "not initialized"
        pipelines = f"pipelines={list(self.pipelines.keys())}" if self._initialized else ""
        return f"<PixelleVideoCore project={self.project_name!r} status={status} {pipelines}>"


# 全局核心实例，整个应用中仅应存在并初始化一份
pixelle_video = PixelleVideoCore()
