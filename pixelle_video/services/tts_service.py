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
TTS (Text-to-Speech) Service - Supports both local and ComfyUI inference

文本转语音 (TTS) 服务模块。
作为系统统一的配音入口，支持两种工作模式：
1. Local (本地模式): 使用开源的 Edge TTS 生成高质量配音（速度极快，无需显卡，免费）。
2. ComfyUI (云端/工作流模式): 使用底层的 ComfyKit 桥接执行复杂的声音克隆或高质量 TTS 工作流。
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from comfykit import ComfyKit
from loguru import logger

from pixelle_video.services.comfy_base_service import ComfyBaseService
from pixelle_video.utils.tts_util import edge_tts
from pixelle_video.tts_voices import speed_to_rate


class TTSService(ComfyBaseService):
    """
    TTS (Text-to-Speech) 核心服务类。
    
    继承自 `ComfyBaseService`，因此天然具备自动发现和解析 `workflows/` 目录下 
    TTS 相关工作流 JSON 配置的能力。
    
    使用示例:
        # 使用系统配置的默认机制生成配音
        audio_path = await pixelle_video.tts(text="你好，世界！")
        
        # 强制指定使用某一个工作流进行配音
        audio_path = await pixelle_video.tts(
            text="你好，世界！",
            workflow="runninghub/tts_edge.json"
        )
        
        # 获取系统当前扫描到的所有可用 TTS 工作流
        workflows = pixelle_video.tts.list_workflows()
    """
    
    # 约定：该服务只识别和加载文件名以 "tts_" 开头的工作流文件
    WORKFLOW_PREFIX = "tts_"
    DEFAULT_WORKFLOW = None  # 没有硬编码的默认值，完全依赖外部 config.yaml 配置
    WORKFLOWS_DIR = "workflows"
    
    def __init__(self, config: dict, core=None):
        """
        初始化 TTS 服务。
        
        Args:
            config: 全局应用配置字典。
            core: PixelleVideoCore 的实例引用（为了让本服务能够获取到 core 中懒加载的 ComfyKit 连接）。
        """
        # 调用父类初始化，设置 service_name="tts"，用于在配置文件中定位对应的子项
        super().__init__(config, service_name="tts", core=core)
    
    
    async def __call__(
        self,
        text: str,
        workflow: Optional[str] = None,
        # ComfyUI 覆盖配置 (目前由 Core 统一管理，这里保留定义以向下兼容)
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        # TTS 核心业务参数
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        # 强制指定推理模式
        inference_mode: Optional[str] = None,
        # 指定输出路径
        output_path: Optional[str] = None,
        **params
    ) -> str:
        """
        执行文本转语音的主入口。
        内部会根据配置或参数智能路由到本地 Edge TTS 或底层的 ComfyUI 工作流引擎。
        
        Args:
            text: 需要转换为语音的旁白文本。
            workflow: 指定的工作流标识（针对 ComfyUI 模式，默认读取全局配置）。
            comfyui_url: (可选) 覆盖请求级别的 ComfyUI 地址。
            runninghub_api_key: (可选) 覆盖请求级别的 RunningHub API Key。
            voice: 指定音色 ID。在 local 模式下，这是 Edge TTS 的系统音色；在 ComfyUI 模式下，将透传给工作流。
            speed: 语速倍率（1.0 = 正常，>1.0 = 加速，<1.0 = 减速）。
            inference_mode: 强制指定推理模式（"local" 或 "comfyui"）。如果未提供，读取配置。
            output_path: 生成音频的本地保存路径（如果不提供，系统会自动在 output/ 目录下生成 UUID 文件名）。
            **params: 透传给底层工作流的其他定制参数（例如 ref_audio 用于声音克隆）。
        
        Returns:
            str: 生成成功的本地音频文件路径。
            
        Examples:
            # 本地免费推理 (Edge TTS)
            audio_path = await pixelle_video.tts(
                text="欢迎来到 Pixelle-Video！",
                inference_mode="local",
                voice="zh-CN-YunjianNeural",
                speed=1.2
            )
            
            # 使用工作流引擎执行复杂推理 (如声音克隆)
            audio_path = await pixelle_video.tts(
                text="这是一段克隆声音的测试",
                inference_mode="comfyui",
                workflow="runninghub/tts_index2.json",
                ref_audio="path/to/my_voice.wav"
            )
        """
        # 确定最终使用的推理模式 (优先级: 方法传参 > 配置文件)
        mode = inference_mode or self.config.get("inference_mode", "local")
        
        # 将请求路由到具体的实现分支
        if mode == "local":
            return await self._call_local_tts(
                text=text,
                voice=voice,
                speed=speed,
                output_path=output_path
            )
        else:  # comfyui
            # 1. 解析指定的工作流（从磁盘或缓存返回具体的结构化数据）
            workflow_info = self._resolve_workflow(workflow=workflow)
            
            # 2. 将任务派发给底层 ComfyUI 执行
            return await self._call_comfyui_workflow(
                workflow_info=workflow_info,
                text=text,
                comfyui_url=comfyui_url,
                runninghub_api_key=runninghub_api_key,
                voice=voice,
                speed=speed,
                output_path=output_path,
                **params
            )
    
    async def _call_local_tts(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        分支实现：使用轻量级的本地 Edge TTS 生成语音。
        
        优点是完全免费且速度极快，适合日常和开发测试环境。
        
        Args:
            text: 旁白文本。
            voice: Edge TTS 的音色 ID（未指定则读取配置）。
            speed: 语速倍数（未指定则读取配置）。
            output_path: 自定义保存路径。
        
        Returns:
            str: 生成的音频文件本地路径。
        """
        # 从配置中提取针对 local 引擎的默认设置
        local_config = self.config.get("local", {})
        
        # 确定音色和语速 (优先级: 方法传参 > 配置文件)
        final_voice = voice or local_config.get("voice", "zh-CN-YunjianNeural")
        final_speed = speed if speed is not None else local_config.get("speed", 1.2)
        
        # 将我们习惯的 float 倍速转换为 Edge TTS 要求的内部格式参数 (如 +20%)
        rate = speed_to_rate(final_speed)
        
        logger.info(f"🎙️  Using local Edge TTS: voice={final_voice}, speed={final_speed}x (rate={rate})")
        
        # 如果调用者未指定存放位置，自动在系统 output/ 目录下生成 UUID 路径
        if not output_path:
            unique_id = uuid.uuid4().hex
            output_path = f"output/{unique_id}.mp3"
            
            # 确保父目录结构存在
            Path("output").mkdir(parents=True, exist_ok=True)
        
        # 执行开源的底层封装库
        try:
            audio_bytes = await edge_tts(
                text=text,
                voice=final_voice,
                rate=rate,
                output_path=output_path
            )
            
            logger.info(f"✅ Generated audio (local Edge TTS): {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Local TTS generation error: {e}")
            raise
    
    async def _call_comfyui_workflow(
        self,
        workflow_info: dict,
        text: str,
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        voice: Optional[str] = None,
        speed: float = 1.0,
        output_path: Optional[str] = None,
        **params
    ) -> str:
        """
        分支实现：使用 ComfyUI/RunningHub 引擎及对应的工作流文件执行复杂的语音合成。
        
        Args:
            workflow_info: 通过 `_resolve_workflow()` 获取的工作流字典结构。
            text: 要合成的文本。
            comfyui_url: 引擎后端地址。
            runninghub_api_key: 云端服务的凭证。
            voice: 传递给工作流内部节点的音色参数。
            speed: 传递给工作流内部节点的语速参数。
            output_path: 如果提供，将会把云端生成的音频下载到此本地路径。
            **params: 其他需要动态注入到工作流中的节点参数。
        
        Returns:
            str: 生成结果的路径或 URL。
        """
        logger.info(f"🎙️  Using workflow: {workflow_info['key']}")
        
        # 1. 组装要推送到 ComfyUI 工作流前端的替换参数集
        workflow_params = {"text": text}
        
        # 仅当有显式赋值且并非默认值时才覆盖工作流参数
        if voice is not None:
            workflow_params["voice"] = voice
        if speed is not None and speed != 1.0:
            workflow_params["speed"] = speed
        
        # 合并用户传入的其他高级参数 (比如声音克隆用的 ref_audio)
        workflow_params.update(params)
        
        logger.debug(f"Workflow parameters: {workflow_params}")
        
        # 3. 使用 Core 实例中管理的单一 ComfyKit 连接执行任务
        try:
            # 获取支持热重载和懒初始化的客户端会话
            kit = await self.core._get_or_create_comfykit()
            
            # 根据工作流的来源决定向 ComfyKit 提交哪种入参结构
            if workflow_info["source"] == "runninghub" and "workflow_id" in workflow_info:
                # 如果是 RunningHub 来源，通过其云端专属的 workflow_id 进行调用
                workflow_input = workflow_info["workflow_id"]
                logger.info(f"Executing RunningHub TTS workflow: {workflow_input}")
            else:
                # 否则，提供本地的 JSON 配置文件路径，ComfyKit 将其加载后发送给底层服务器
                workflow_input = workflow_info["path"]
                logger.info(f"Executing selfhost TTS workflow: {workflow_input}")
            
            # 执行并等待结果
            result = await kit.execute(workflow_input, workflow_params)
            
            # 4. 解析生成的业务结果
            if result.status != "completed":
                error_msg = result.msg or "Unknown error"
                logger.error(f"TTS generation failed: {error_msg}")
                raise Exception(f"TTS generation failed: {error_msg}")
            
            # ComfyKit 返回的对象结构较为灵活，可能包含多处存放文件的属性，我们依次探测
            audio_path = None
            
            # 第一优先级: result.audios (如果是最新的专门针对音频返回的字段)
            if hasattr(result, 'audios') and result.audios:
                audio_path = result.audios[0]
                logger.debug(f"✅ Found audio in result.audios: {audio_path}")
            # 第二优先级: result.files
            elif hasattr(result, 'files') and result.files:
                audio_path = result.files[0]
                logger.debug(f"✅ Found audio in result.files: {audio_path}")
            # 第三优先级: result.outputs 字典 (部分非标准节点可能会放在这里)
            elif hasattr(result, 'outputs') and result.outputs:
                logger.debug(f"Searching for audio file in result.outputs: {result.outputs}")
                # 遍历查找以常见音频格式结尾的字符串
                for key, value in result.outputs.items():
                    if isinstance(value, str) and any(value.endswith(ext) for ext in ['.mp3', '.wav', '.flac']):
                        audio_path = value
                        logger.debug(f"✅ Found audio in result.outputs[{key}]: {audio_path}")
                        break
            
            if not audio_path:
                # 探测失败，抛出致命异常并打印对象的详细内存结构以供排查
                logger.error("No audio file generated")
                logger.error(f"❌ Result analysis:")
                logger.error(f"   - result.audios: {getattr(result, 'audios', 'NOT_FOUND')}")
                logger.error(f"   - result.files: {getattr(result, 'files', 'NOT_FOUND')}")
                logger.error(f"   - result.outputs: {getattr(result, 'outputs', 'NOT_FOUND')}")
                logger.error(f"   - Full __dict__: {result.__dict__}")
                raise Exception("No audio file generated by workflow")
            
            # 如果请求中包含了输出路径，且工作流返回的是网络 URL，则异步下载到本地
            if output_path and audio_path.startswith(('http://', 'https://')):
                import httpx
                import os
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                logger.info(f"Downloading audio from {audio_path} to {output_path}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(audio_path)
                    response.raise_for_status()
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                
                logger.info(f"✅ Generated audio (ComfyUI): {output_path}")
                return output_path
            
            logger.info(f"✅ Generated audio (ComfyUI): {audio_path}")
            return audio_path
        
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            raise
