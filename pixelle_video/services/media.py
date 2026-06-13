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
Media Generation Service - ComfyUI Workflow-based implementation

媒体（图像/视频）生成服务模块 - 基于 ComfyUI 工作流的实现。
支持自动扫描并解析生成图像（image_*.json）和生成视频（video_*.json）的工作流配置文件，
并根据 ExecuteResult 自动探测返回的数据类型。
"""

from typing import Optional

from comfykit import ComfyKit
from loguru import logger

from pixelle_video.services.comfy_base_service import ComfyBaseService
from pixelle_video.models.media import MediaResult


class MediaService(ComfyBaseService):
    """
    核心媒体生成服务 (基于工作流)。
    
    继承自 ComfyBaseService。使用底层的 ComfyKit 将提示词提交给实际的生图或生视频引擎执行。
    该类同时支持图像与视频两种生成类型的任务路由。
    
    使用示例:
        # 使用默认配置生成图片
        media = await pixelle_video.media(prompt="一只可爱的猫咪")
        if media.is_image:
            print(f"生成的图片路径: {media.url}")
        elif media.is_video:
            print(f"生成的视频路径: {media.url} (时长: {media.duration}秒)")
        
        # 明确指定需要调用的自定义工作流
        media = await pixelle_video.media(
            prompt="一辆飞驰的跑车",
            workflow="image_flux.json"
        )
        
        # 获取所有系统加载的媒体工作流列表
        workflows = pixelle_video.media.list_workflows()
    """
    
    WORKFLOW_PREFIX = ""  # 这里为空，因为我们重写了 _scan_workflows 支持多种前缀
    DEFAULT_WORKFLOW = None  # 没有硬编码的默认工作流，依赖系统配置
    WORKFLOWS_DIR = "workflows"
    
    def __init__(self, config: dict, core=None):
        """
        初始化媒体服务。
        
        Args:
            config: 全局配置字典。
            core: PixelleVideoCore 实例引用（用于获取共享的 ComfyKit 会话对象）。
        """
        # 为了配置兼容性，服务名依然映射至 "image" 节点
        super().__init__(config, service_name="image", core=core)
    
    def _scan_workflows(self):
        """
        重写父类的方法：扫描工作流配置目录。
        
        该服务同时需要支持生成图像（前缀 `image_`）和生成视频（前缀 `video_`）两种类型的工作流。
        
        Returns:
            List[dict]: 排序后的可用工作流字典列表。
        """
        from pixelle_video.utils.os_util import list_resource_dirs, list_resource_files, get_resource_path
        from pathlib import Path
        
        workflows = []
        
        # 获取所有工作流来源目录 (如 'runninghub', 'selfhost' 等)
        source_dirs = list_resource_dirs("workflows")
        
        if not source_dirs:
            logger.warning("No workflow source directories found")
            return workflows
        
        # 遍历扫描每个来源目录
        for source_name in source_dirs:
            workflow_files = list_resource_files("workflows", source_name)
            
            # 仅保留带有 image_ 或 video_ 前缀且为 .json 格式的配置文件
            matching_files = [
                f for f in workflow_files 
                if (f.startswith("image_") or f.startswith("video_")) and f.endswith('.json')
            ]
            
            for filename in matching_files:
                try:
                    # 获取该配置文件的物理绝对路径并尝试加载解析
                    file_path = Path(get_resource_path("workflows", source_name, filename))
                    workflow_info = self._parse_workflow_file(file_path, source_name)
                    workflows.append(workflow_info)
                    logger.debug(f"Found workflow: {workflow_info['key']}")
                except Exception as e:
                    logger.error(f"Failed to parse workflow {source_name}/{filename}: {e}")
        
        # 按照唯一标识键名 (key) 进行稳定排序返回
        return sorted(workflows, key=lambda w: w["key"])

    def list_workflows(self) -> list[dict]:
        """List Comfy/RunningHub/Selfhost workflows only.

        Direct provider models are exposed through core.api_media.list_workflows()
        so UI code can keep local workflows and API models in separate selectors.
        """
        return super().list_workflows()
    
    async def __call__(
        self,
        prompt: str,
        workflow: Optional[str] = None,
        # 指定实际生成的媒体类型（必须明确声明，以引导底层如何处理结果）
        media_type: str = "image",  # 接受 "image" 或 "video"
        # 覆盖级的 ComfyUI 连接凭据
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        # 常用的生图/视频节点参数提取暴露
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration: Optional[float] = None,  # Video duration in seconds (for video workflows) / 视频流专属参数（期望生成的视频时长/秒，通常由前置 TTS 的音频时长决定）
        output_path: Optional[str] = None,
        image_path: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        steps: Optional[int] = None,
        seed: Optional[int] = None,
        cfg: Optional[float] = None,
        sampler: Optional[str] = None,
        **params
    ) -> MediaResult:
        """
        触发工作流生成多媒体文件主入口。
        
        请求底层的 ComfyKit 将提示词和一系列超参数推送给引擎执行生图或生视频任务，并等待结果返回。
        
        Args:
            prompt: 正向画面提示词。
            workflow: 指定的工作流名称或路径（未指定则读取系统默认配置，例如 "image_flux.json"）。
            media_type: 生成的媒体类型 "image" 还是 "video"（默认为 "image"）。
            comfyui_url: 自定义的 ComfyUI 服务器地址（覆盖全局配置）。
            runninghub_api_key: 自定义的云端 API 凭据。
            width: 输出画面的宽度（像素）。
            height: 输出画面的高度（像素）。
            duration: 预期视频生成时长（秒）。**针对视频生成这是个非常核心的参数**，用于严格保证声画同步。
            negative_prompt: 反向提示词（告诉 AI 不应该包含哪些内容）。
            steps: 降噪采样步数。
            seed: 随机种子（固定种子可以生成大致相同的图片）。
            cfg: 提示词相关性权重（数值越大越遵循提示词，但画面可能变形）。
            sampler: 采样器名称。
            **params: 透传给工作流内部节点的其他任何定制参数。
        
        Returns:
            MediaResult: 包含最终 URL、判定出的实际类型以及可能附带的视频时长的结果对象。
            
        Raises:
            Exception: 底层执行失败、没有获取到有效媒体文件等。
        """
        selected_workflow = workflow or self.config.get("default_workflow")
        if selected_workflow and selected_workflow.startswith("api/"):
            if not self.core or not getattr(self.core, "api_media", None):
                raise RuntimeError("API media service is not initialized")
            return await self.core.api_media(
                prompt=prompt,
                workflow=selected_workflow,
                media_type=media_type,
                width=width,
                height=height,
                duration=duration,
                output_path=output_path,
                image_path=image_path,
                negative_prompt=negative_prompt,
                steps=steps,
                seed=seed,
                cfg=cfg,
                sampler=sampler,
                **params
            )

        # 1. Resolve workflow (returns structured info) / 解析请求的工作流，获取准确的配置和内部参数映射字典
        workflow_info = self._resolve_workflow(workflow=workflow)
        
        # 2. 构建传递给工作流中节点的输入变量字典
        workflow_params = {"prompt": prompt}
        
        # 填充所有额外指定的超参
        if width is not None:
            workflow_params["width"] = width
        if height is not None:
            workflow_params["height"] = height
        if duration is not None:
            workflow_params["duration"] = duration
            if media_type == "video":
                logger.info(f"📏 Target video duration: {duration:.2f}s (from TTS audio)")
        if negative_prompt is not None:
            workflow_params["negative_prompt"] = negative_prompt
        if steps is not None:
            workflow_params["steps"] = steps
        if seed is not None:
            workflow_params["seed"] = seed
        if cfg is not None:
            workflow_params["cfg"] = cfg
        if sampler is not None:
            workflow_params["sampler"] = sampler
        
        workflow_params.update(params)
        
        logger.debug(f"Workflow parameters: {workflow_params}")
        
        # 4. 从核心服务层获取 ComfyKit 共享连接并调度任务
        try:
            kit = await self.core._get_or_create_comfykit()
            
            # 判断并分发给云端或本地环境执行
            if workflow_info["source"] == "runninghub" and "workflow_id" in workflow_info:
                workflow_input = workflow_info["workflow_id"]
                logger.info(f"Executing RunningHub workflow: {workflow_input}")
            else:
                workflow_input = workflow_info["path"]
                logger.info(f"Executing selfhost workflow: {workflow_input}")
            
            result = await kit.execute(workflow_input, workflow_params)
            
            # 5. 分析执行结果
            if result.status != "completed":
                error_msg = result.msg or "Unknown error"
                logger.error(f"Media generation failed: {error_msg}")
                raise Exception(f"Media generation failed: {error_msg}")
            
            # 根据调用方期望的 media_type 去对应的结果池中拉取文件路径
            if media_type == "video":
                # 视频工作流 - 尝试从 videos 列表中提取结果
                if not result.videos:
                    logger.error("No video generated (workflow returned no videos)")
                    raise Exception("No video generated")
                
                video_url = result.videos[0]
                logger.info(f"✅ Generated video: {video_url}")
                
                # 如果引擎成功返回了实际计算出的时长，则带上
                duration = None
                if hasattr(result, 'duration') and result.duration:
                    duration = result.duration
                
                return MediaResult(
                    media_type="video",
                    url=video_url,
                    duration=duration
                )
            else:  # image
                # 图像工作流 - 尝试从 images 列表中提取结果
                if not result.images:
                    logger.error("No image generated (workflow returned no images)")
                    raise Exception("No image generated")
                
                image_url = result.images[0]
                logger.info(f"✅ Generated image: {image_url}")
                
                return MediaResult(
                    media_type="image",
                    url=image_url
                )
        
        except Exception as e:
            logger.error(f"Media generation error: {e}")
            raise
