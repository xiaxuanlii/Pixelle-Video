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
Image Analysis Service - ComfyUI Workflow-based implementation

图像分析服务 (基于 ComfyUI 工作流实现)。
借助大视觉模型 (Vision-Language Models，如 Florence-2, BLIP 等) 来剖析图片语义并回传其精确描述。
这被主要应用于“资产驱动生成”中：当用户扔上几张自己产品的图，本服务负责把它提取为关键词让 LLM 编剧。
"""

from typing import Optional, Literal
from pathlib import Path

from comfykit import ComfyKit
from loguru import logger

from pixelle_video.services.comfy_base_service import ComfyBaseService


class ImageAnalysisService(ComfyBaseService):
    """
    图像解析与理解服务 (基于工作流)。
    
    通过底层的 ComfyKit 将图片扔给视觉多模态大模型进行观察和总结，最后返回自然语言的长篇描述文本。
    
    命名规约：所有的相关配置文件必须满足 `{source}/analyse_*.json` 的特征约束。
    - runninghub/analyse_image.json (针对云端，速度最快，默认策略)
    - selfhost/analyse_image.json (为私有部署，保障隐私安全)
    
    使用示例:
        # 使用云端方案进行全自动理解分析
        description = await pixelle_video.image_analysis("path/to/image.jpg")
    """
    
    WORKFLOW_PREFIX = "analyse_"
    WORKFLOWS_DIR = "workflows"
    
    def __init__(self, config: dict, core=None):
        """
        初始化解析服务。
        
        Args:
            config: 全局配置参数容器字典。
            core: 全局生命周期的 PixelleVideoCore 实例代理（可复用统一建立的 websocket 并发长连接）。
        """
        super().__init__(config, service_name="image_analysis", core=core)
    
    async def __call__(
        self,
        image_path: str,
        # 模型后端的来源指示
        source: Literal['runninghub', 'selfhost'] = 'runninghub',
        workflow: Optional[str] = None,
        # ComfyUI 重定向相关透传选项
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        # 后门扩展
        **params
    ) -> str:
        """
        调用视觉模型读取特定图片内容的主干方法。
        
        Args:
            image_path: 等待检查的单张本地素材存放路径。
            source: 后端推理提供商策略 ('runninghub' 或 'selfhost')。
            workflow: 如果强制提供某个文件，会覆盖规约自动探测结果。
            **params: 追加的扩展变量支持（有些模型可能要求传递 prompt 指导它如何检查图片，如“只看左上角”）。
            
        Returns:
            str: 成功提取的模型解析内容文本段落。
        """
        from pixelle_video.utils.workflow_util import resolve_workflow_path
        
        # 1. 对上传资产的本地可用情况进行强制的前置校验
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # 2. 如果业务没有强制打偏，遵照标准的命名约定进行路由寻址
        if workflow is None:
            workflow = resolve_workflow_path("analyse_image", source)
            logger.info(f"Using {source} workflow: {workflow}")
        
        workflow_info = self._resolve_workflow(workflow=workflow)
        
        # 3. 将本地路径赋值给名为 'image' 的变量供底层引擎通过 HTTP 上传传输
        workflow_params = {
            "image": str(image_path)
        }
        workflow_params.update(params)
        logger.debug(f"Workflow parameters: {workflow_params}")
        
        try:
            # 复用基底单例，获取到安全的并发支持
            kit = await self.core._get_or_create_comfykit()
            
            if workflow_info["source"] == "runninghub" and "workflow_id" in workflow_info:
                workflow_input = workflow_info["workflow_id"]
                logger.info(f"Executing RunningHub workflow: {workflow_input}")
            else:
                workflow_input = workflow_info["path"]
                logger.info(f"Executing selfhost workflow: {workflow_input}")
            
            result = await kit.execute(workflow_input, workflow_params)
            
            # 5. 断言结果完成度并开始从多达数百个节点的回复字典中寻宝 (提取出文本)
            if result.status != "completed":
                error_msg = result.msg or "Unknown error"
                logger.error(f"Image analysis failed: {error_msg}")
                raise Exception(f"Image analysis failed: {error_msg}")
            
            description = None
            
            # 兼容形态 1: 原生/最直接的支持 - ComfyKit 返回的包装中包含了 texts 对象流
            if result.outputs:
                for node_id, node_output in result.outputs.items():
                    if 'text' in node_output:
                        text_list = node_output['text']
                        if text_list and len(text_list) > 0:
                            description = text_list[0]
                            break
            
            # 兼容形态 2: 部分 RunningHub 远端提供的分析模型，会将其当成一个完整的 .txt 附件放在原始数据中传输回源
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
                                        break
            
            if not description:
                logger.error(f"No text found in outputs: {result.outputs}")
                raise Exception("No description generated")
            
            logger.info(f"✅ Image analyzed: {description[:100]}...")
            return description
        
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            raise
