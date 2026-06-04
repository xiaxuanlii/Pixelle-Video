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
Video Analysis Service - ComfyUI Workflow-based implementation

基于 ComfyUI 工作流实现的视频内容分析服务。
用于反推或提炼上传视频的文本描述。
"""

from typing import Optional, Literal
from pathlib import Path

from comfykit import ComfyKit
from loguru import logger

from pixelle_video.services.comfy_base_service import ComfyBaseService


class VideoAnalysisService(ComfyBaseService):
    """
    视频分析服务 (基于工作流)。
    
    使用底层的 ComfyKit 调度视频理解大模型 (如 Qwen-VL 等视频理解模型)。
    返回对视频内容的详细文本描述。
    
    规约约定: 自动扫描匹配 `{source}/analyse_video.json` 的工作流配置文件。
    - runninghub/analyse_video.json (默认云端)
    - selfhost/analyse_video.json (本地私有化节点)
    
    使用示例:
        # 使用默认配置获取视频摘要
        description = await pixelle_video.video_analysis("path/to/video.mp4")
        
        # 强制指定使用本地私有化的视觉模型进行分析
        description = await pixelle_video.video_analysis(
            "path/to/video.mp4",
            source="selfhost"
        )
    """
    
    WORKFLOW_PREFIX = "analyse_video"
    WORKFLOWS_DIR = "workflows"
    
    def __init__(self, config: dict, core=None):
        """
        初始化视频分析服务。
        
        Args:
            config: 全局配置字典。
            core: PixelleVideoCore 实例引用（用于获取共享的 ComfyKit 会话对象）。
        """
        super().__init__(config, service_name="video_analysis", core=core)
    
    async def __call__(
        self,
        video_path: str,
        # 强制指定的工作流查找源
        source: Literal['runninghub', 'selfhost'] = 'runninghub',
        workflow: Optional[str] = None,
        # ComfyUI 连接信息覆盖
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        # 额外参数
        **params
    ) -> str:
        """
        核心调用：触发针对指定视频的语义分析流。
        
        Args:
            video_path: 需要分析的源视频本地路径或网络 URL。
            source: 策略来源（默认走云端 runninghub）。
            workflow: 如果传入具体名字，将覆盖 source 的查找策略直接加载该文件。
            **params: 透传给工作流节点的其他特定参数。
            
        Returns:
            str: 模型解析出的视频详细描述文本。
        """
        from pixelle_video.utils.workflow_util import resolve_workflow_path
        
        # 1. 安全检验输入文件的合法性
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # 2. 如果没给，利用标准规约反查真实工作流 JSON 位置
        if workflow is None:
            workflow = resolve_workflow_path("analyse_video", source)
            logger.info(f"Using {source} workflow: {workflow}")
        
        # 3. 将工作流文件解析为标准化字典模型
        workflow_info = self._resolve_workflow(workflow=workflow)
        
        # 4. 组装发给底层引擎的输入数据包
        workflow_params = {
            "video": str(video_path)  # 对应于工作流中的 Load Video 节点输入
        }
        workflow_params.update(params)
        logger.debug(f"Workflow parameters: {workflow_params}")
        
        try:
            kit = await self.core._get_or_create_comfykit()
            
            # 分发调用逻辑 (云端直接透传 ID，本地使用上传路径)
            if workflow_info["source"] == "runninghub" and "workflow_id" in workflow_info:
                workflow_input = workflow_info["workflow_id"]
                logger.info(f"Executing RunningHub workflow: {workflow_input}")
            else:
                workflow_input = workflow_info["path"]
                logger.info(f"Executing selfhost workflow: {workflow_input}")
            
            result = await kit.execute(workflow_input, workflow_params)
            
            # 6. 后置处理与各种可能的回包格式适配提取
            if result.status != "completed":
                error_msg = result.msg or "Unknown error"
                logger.error(f"Video analysis failed: {error_msg}")
                raise Exception(f"Video analysis failed: {error_msg}")
            
            description = None
            
            # 格式 1: 标准输出中的 texts 文本数组直接携带
            if result.texts and len(result.texts) > 0:
                description = result.texts[0]
                logger.debug(f"Found description in result.texts: {description[:100]}...")
            
            # 格式 2: Selfhost 原始的 Node 输出对象嵌套
            elif result.outputs:
                for node_id, node_output in result.outputs.items():
                    if 'text' in node_output:
                        text_list = node_output['text']
                        if text_list and len(text_list) > 0:
                            description = text_list[0]
                            logger.debug(f"Found description in outputs.text: {description[:100]}...")
                            break
            
            # 格式 3: RunningHub 云端某些模型为了防止长文本溢出，可能返回带有 txt 外链的结构
            if not description and result.outputs and 'raw_data' in result.outputs:
                raw_data = result.outputs['raw_data']
                if raw_data and len(raw_data) > 0:
                    for item in raw_data:
                        if item.get('fileType') == 'txt' and 'fileUrl' in item:
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.get(item['fileUrl']) as resp:
                                    if resp.status == 200:
                                        description = await resp.text()
                                        description = description.strip()
                                        logger.debug(f"Downloaded description from URL: {description[:100]}...")
                                        break
            
            if not description:
                logger.error(f"No text found in result. Status: {result.status}, Outputs: {result.outputs}, Texts: {result.texts}")
                raise Exception("No description generated from video analysis")
            
            logger.info(f"✅ Video analyzed: {description[:100]}...")
            return description
        
        except Exception as e:
            logger.error(f"Video analysis error: {e}")
            raise
