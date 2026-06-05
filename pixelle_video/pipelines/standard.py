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
Standard Video Generation Pipeline

标准视频生成流水线模块。
此模块定义了将主题文本或预定脚本转换为最终视频的标准工作流。
这是针对通用视频生成的默认管道实现。
目前已重构为继承自 `LinearVideoPipeline` (采用模板方法设计模式)。
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Literal, List
import asyncio
import shutil

from loguru import logger

from pixelle_video.pipelines.linear import LinearVideoPipeline, PipelineContext
from pixelle_video.models.progress import ProgressEvent
from pixelle_video.models.storyboard import (
    Storyboard,
    StoryboardFrame,
    StoryboardConfig,
    ContentMetadata,
    VideoGenerationResult
)
from pixelle_video.utils.content_generators import (
    generate_title,
    generate_narrations_from_topic,
    split_narration_script,
    generate_image_prompts,
)
from pixelle_video.utils.os_util import (
    create_task_output_dir,
    get_task_final_video_path
)
from pixelle_video.utils.template_util import get_template_type
from pixelle_video.utils.prompt_helper import build_image_prompt
from pixelle_video.services.video import VideoService


class StandardPipeline(LinearVideoPipeline):
    """
    标准视频生成流水线 (Standard video generation pipeline)
    
    完整工作流步骤:
    1. 生成或确定视频标题 (生成模式下调用大模型)。
    2. 生成分镜旁白 (基于主题通过大模型发散，或者直接切割预定好的用户脚本)。
    3. 为每个旁白生成对应的画面提示词 (Image Prompts)。
    4. 遍历每个分镜执行原子任务:
       - 生成旁白音频 (调用 TTS)
       - 生成画面背景 (调用绘画引擎如 ComfyUI)
       - 将 HTML 模板与前面生成的图文音合并渲染出单帧静态图
       - 将静态帧图像配合音频转换为视频片段
    5. 将所有生成好的分段视频拼接为一个完整的长视频。
    6. 混入背景音乐 (BGM)（可选）。
    
    支持两种模式 (Mode):
    - "generate": 内容生成模式，利用 LLM 根据给定主题发散出整套视频脚本。
    - "fixed": 脚本固定模式，不使用大模型发散，直接将提供的脚本按行或标点作为旁白直接使用。
    """
    
    # ==================== Lifecycle Methods / 生命周期重写方法 ====================

    async def setup_environment(self, ctx: PipelineContext):
        """第一步：初始化任务专属的工作目录和执行环境"""
        text = ctx.input_text
        mode = ctx.params.get("mode", "generate")
        
        logger.info(f"🚀 Starting StandardPipeline in '{mode}' mode")
        logger.info(f"   Text length: {len(text)} chars")
        
        # 创建具有唯一 UUID 的独立任务输出目录
        task_dir, task_id = create_task_output_dir()
        ctx.task_id = task_id
        ctx.task_dir = task_dir
        
        logger.info(f"📁 Task directory created: {task_dir}")
        logger.info(f"   Task ID: {task_id}")
        
        # 确定最终生成的视频文件的保存路径
        output_path = ctx.params.get("output_path")
        if output_path is None:
            ctx.final_video_path = get_task_final_video_path(task_id)
        else:
            # 如果请求中明确指定了输出路径，我们将在后期制作的最后一步复制过去。
            # 在内部处理拼接逻辑时，依然使用统一的工作目录。
            ctx.final_video_path = get_task_final_video_path(task_id)
            logger.info(f"   Will copy final video to: {output_path}")

    async def generate_content(self, ctx: PipelineContext):
        """第二步：生成或处理剧本和旁白"""
        mode = ctx.params.get("mode", "generate")
        text = ctx.input_text
        n_scenes = ctx.params.get("n_scenes", 5)
        min_words = ctx.params.get("min_narration_words", 5)
        max_words = ctx.params.get("max_narration_words", 20)
        
        if mode == "generate":
            self._report_progress(ctx.progress_callback, "generating_narrations", 0.05)
            # 使用 LLM 根据主题文本生成多段有逻辑的分镜旁白
            ctx.narrations = await generate_narrations_from_topic(
                self.llm,
                topic=text,
                n_scenes=n_scenes,
                min_words=min_words,
                max_words=max_words
            )
            logger.info(f"✅ Generated {len(ctx.narrations)} narrations")
        else:  # fixed / 固定模式
            self._report_progress(ctx.progress_callback, "splitting_script", 0.05)
            split_mode = ctx.params.get("split_mode", "paragraph")
            # 不调用大模型，直接根据段落或标点符号切分原始长文本作为分镜旁白
            ctx.narrations = await split_narration_script(text, split_mode=split_mode)
            logger.info(f"✅ Split script into {len(ctx.narrations)} segments (mode={split_mode})")
            logger.info(f"   Note: n_scenes={n_scenes} is ignored in fixed mode")

    async def determine_title(self, ctx: PipelineContext):
        """第三步：确定或利用 LLM 生成视频的标题"""
        title = ctx.params.get("title")
        mode = ctx.params.get("mode", "generate")
        text = ctx.input_text
        
        if title:
            # 如果接口入参中已明确提供标题，直接使用
            ctx.title = title
            logger.info(f"   Title: '{title}' (user-specified)")
        else:
            self._report_progress(ctx.progress_callback, "generating_title", 0.01)
            if mode == "generate":
                # auto: 根据需要自动决定生成策略
                ctx.title = await generate_title(self.llm, text, strategy="auto")
                logger.info(f"   Title: '{ctx.title}' (auto-generated)")
            else:  # fixed
                # 即使旁白是固定的，标题依然可以通过 LLM 从文本中总结提炼
                ctx.title = await generate_title(self.llm, text, strategy="llm")
                logger.info(f"   Title: '{ctx.title}' (LLM-generated)")

    async def plan_visuals(self, ctx: PipelineContext):
        """第四步：基于旁白为每个分镜生成画面提示词 (Image Prompts)"""
        # 探测所选 HTML 排版模板的类型，决定是否需要真实生成媒体资产（生图/生视频）
        frame_template = ctx.params.get("frame_template") or "1080x1920/image_default.html"
        
        template_name = Path(frame_template).name
        template_type = get_template_type(template_name)
        template_requires_media = (template_type in ["image", "video"])
        
        if template_type == "image":
            logger.info(f"📸 Template requires image generation")
        elif template_type == "video":
            logger.info(f"🎬 Template requires video generation")
        else:  # static (静态模板)
            logger.info(f"⚡ Static template - skipping media generation pipeline")
            logger.info(f"   💡 Benefits: Faster generation + Lower cost + No ComfyUI dependency")
        
        # 仅当模板需要配图/配视频时，才调用大语言模型去发散提示词，节省 Token 成本
        if template_requires_media:
            self._report_progress(ctx.progress_callback, "generating_image_prompts", 0.15)
            
            prompt_prefix = ctx.params.get("prompt_prefix")
            min_words = ctx.params.get("min_image_prompt_words", 30)
            max_words = ctx.params.get("max_image_prompt_words", 60)
            
            # 如果请求覆盖了 prompt_prefix，暂时更新内存配置以便提示词组装器获取
            original_prefix = None
            if prompt_prefix is not None:
                image_config = self.core.config.get("comfyui", {}).get("image", {})
                original_prefix = image_config.get("prompt_prefix")
                image_config["prompt_prefix"] = prompt_prefix
                logger.info(f"Using custom prompt_prefix: '{prompt_prefix}'")
            
            try:
                # 包装一个带进度的子回调，供 LLM 内部批处理时向外抛出进度
                def image_prompt_progress(completed: int, total: int, message: str):
                    batch_progress = completed / total if total > 0 else 0
                    overall_progress = 0.15 + (batch_progress * 0.15)
                    self._report_progress(
                        ctx.progress_callback,
                        "generating_image_prompts",
                        overall_progress,
                        extra_info=message
                    )
                
                # 生成基础的画面提示词列表
                base_image_prompts = await generate_image_prompts(
                    self.llm,
                    narrations=ctx.narrations,
                    min_words=min_words,
                    max_words=max_words,
                    progress_callback=image_prompt_progress
                )
                
                # 应用全局风格前缀修饰语
                image_config = self.core.config.get("comfyui", {}).get("image", {})
                prompt_prefix_to_use = prompt_prefix if prompt_prefix is not None else image_config.get("prompt_prefix", "")
                
                ctx.image_prompts = []
                for base_prompt in base_image_prompts:
                    final_prompt = build_image_prompt(base_prompt, prompt_prefix_to_use)
                    ctx.image_prompts.append(final_prompt)
                
            finally:
                # 还原原始的全局提示词前缀
                if original_prefix is not None:
                    image_config["prompt_prefix"] = original_prefix
            
            logger.info(f"✅ Generated {len(ctx.image_prompts)} image prompts")
        else:
            # 静态模板无需图片提示词，直接填充空占位符以对齐数据长度
            ctx.image_prompts = [None] * len(ctx.narrations)
            logger.info(f"⚡ Skipped image prompt generation (static template)")
            logger.info(f"   💡 Savings: {len(ctx.narrations)} LLM calls + {len(ctx.narrations)} media generations")

    async def initialize_storyboard(self, ctx: PipelineContext):
        """第五步：拼装内部核心数据结构 Storyboard（分镜剧本大纲）"""
        # === 处理不同版本 TTS 参数向后兼容逻辑 ===
        tts_inference_mode = ctx.params.get("tts_inference_mode")
        tts_voice = ctx.params.get("tts_voice")
        voice_id = ctx.params.get("voice_id")
        tts_workflow = ctx.params.get("tts_workflow")
        
        final_voice_id = None
        final_tts_workflow = tts_workflow
        
        if tts_inference_mode:
            # 兼容新版 Web UI 下发的字段
            if tts_inference_mode == "local":
                final_voice_id = tts_voice or "zh-CN-YunjianNeural"
                final_tts_workflow = None
                logger.debug(f"TTS Mode: local (voice={final_voice_id})")
            elif tts_inference_mode == "comfyui":
                final_voice_id = None
                logger.debug(f"TTS Mode: comfyui (workflow={final_tts_workflow})")
        else:
            # 兼容旧版本 API 调用
            final_voice_id = voice_id or tts_voice or "zh-CN-YunjianNeural"
            logger.debug(f"TTS Mode: legacy (voice_id={final_voice_id}, workflow={final_tts_workflow})")
            
        # 实例化整个长视频所需的配置集
        ctx.config = StoryboardConfig(
            task_id=ctx.task_id,
            n_storyboard=len(ctx.narrations), # 确保使用真实切分的长度
            min_narration_words=ctx.params.get("min_narration_words", 5),
            max_narration_words=ctx.params.get("max_narration_words", 20),
            min_image_prompt_words=ctx.params.get("min_image_prompt_words", 30),
            max_image_prompt_words=ctx.params.get("max_image_prompt_words", 60),
            video_fps=ctx.params.get("video_fps", 30),
            tts_inference_mode=tts_inference_mode or "local",
            voice_id=final_voice_id,
            tts_workflow=final_tts_workflow,
            tts_speed=ctx.params.get("tts_speed", 1.2),
            ref_audio=ctx.params.get("ref_audio"),
            media_width=ctx.params.get("media_width"),
            media_height=ctx.params.get("media_height"),
            media_workflow=ctx.params.get("media_workflow"),
            api_video_params=ctx.params.get("api_video_params"),
            frame_template=ctx.params.get("frame_template") or "1080x1920/image_default.html",
            template_params=ctx.params.get("template_params")
        )
        
        # 创建空的分镜主干对象
        ctx.storyboard = Storyboard(
            title=ctx.title,
            config=ctx.config,
            content_metadata=ctx.params.get("content_metadata"),
            created_at=datetime.now()
        )
        
        # 将旁白与对应的画面提示词填入具体帧中
        for i, (narration, image_prompt) in enumerate(zip(ctx.narrations, ctx.image_prompts)):
            frame = StoryboardFrame(
                index=i,
                narration=narration,
                image_prompt=image_prompt,
                created_at=datetime.now()
            )
            ctx.storyboard.frames.append(frame)

    async def produce_assets(self, ctx: PipelineContext):
        """第六步：核心生成环节。生产音频、生成图像，并将二者结合模板渲染为短视频片段"""
        storyboard = ctx.storyboard
        config = ctx.config
        
        # 检查是否使用了 RunningHub 的工作流，如果是，则支持一定数量的并行并发请求
        is_runninghub = (
            (config.tts_workflow and config.tts_workflow.startswith("runninghub/")) or
            (config.media_workflow and config.media_workflow.startswith("runninghub/"))
        )
        
        # 动态获取可允许的最大并发数支持（热重载）
        from pixelle_video.config import config_manager
        runninghub_concurrent_limit = config_manager.config.comfyui.runninghub_concurrent_limit or 1
        
        if is_runninghub and runninghub_concurrent_limit > 1:
            logger.info(f"🚀 Using parallel processing for RunningHub workflows (max {runninghub_concurrent_limit} concurrent)")
            
            # 使用 asyncio 信号量限制并发协程数量
            semaphore = asyncio.Semaphore(runninghub_concurrent_limit)
            completed_count = 0
            
            async def process_frame_with_semaphore(i: int, frame: StoryboardFrame):
                nonlocal completed_count
                async with semaphore:
                    base_progress = 0.2
                    frame_range = 0.6
                    per_frame_progress = frame_range / len(storyboard.frames)
                    
                    # 动态创建针对当前并行的帧级别的进度回调闭包
                    def frame_progress_callback(event: ProgressEvent):
                        overall_progress = base_progress + (per_frame_progress * completed_count) + (per_frame_progress * event.progress)
                        if ctx.progress_callback:
                            adjusted_event = ProgressEvent(
                                event_type=event.event_type,
                                progress=overall_progress,
                                frame_current=i+1,
                                frame_total=len(storyboard.frames),
                                step=event.step,
                                action=event.action
                            )
                            ctx.progress_callback(adjusted_event)
                    
                    # 上报分镜处理开始
                    self._report_progress(
                        ctx.progress_callback,
                        "processing_frame",
                        base_progress + (per_frame_progress * completed_count),
                        frame_current=i+1,
                        frame_total=len(storyboard.frames)
                    )
                    
                    # 调用统一的 FrameProcessor 处理该帧的综合生成与合成
                    processed_frame = await self.core.frame_processor(
                        frame=frame,
                        storyboard=storyboard,
                        config=config,
                        total_frames=len(storyboard.frames),
                        progress_callback=frame_progress_callback
                    )
                    
                    completed_count += 1
                    logger.info(f"✅ Frame {i+1} completed ({processed_frame.duration:.2f}s) [{completed_count}/{len(storyboard.frames)}]")
                    return i, processed_frame
            
            # 将所有的分镜帧包装为并发任务并一起执行
            tasks = [process_frame_with_semaphore(i, frame) for i, frame in enumerate(storyboard.frames)]
            results = await asyncio.gather(*tasks)
            
            # 还原结果顺序，累加总时长
            for idx, processed_frame in sorted(results, key=lambda x: x[0]):
                storyboard.frames[idx] = processed_frame
                storyboard.total_duration += processed_frame.duration
            
            logger.info(f"✅ All frames processed in parallel (total duration: {storyboard.total_duration:.2f}s)")
        else:
            # 串行处理逻辑（常用于本地 ComfyUI 无法承受高并发排队压力的场景）
            logger.info("⚙️ Using serial processing (non-RunningHub workflow)")
            
            for i, frame in enumerate(storyboard.frames):
                base_progress = 0.2
                frame_range = 0.6
                per_frame_progress = frame_range / len(storyboard.frames)
                
                def frame_progress_callback(event: ProgressEvent):
                    overall_progress = base_progress + (per_frame_progress * i) + (per_frame_progress * event.progress)
                    if ctx.progress_callback:
                        adjusted_event = ProgressEvent(
                            event_type=event.event_type,
                            progress=overall_progress,
                            frame_current=event.frame_current,
                            frame_total=event.frame_total,
                            step=event.step,
                            action=event.action
                        )
                        ctx.progress_callback(adjusted_event)
                
                self._report_progress(
                    ctx.progress_callback,
                    "processing_frame",
                    base_progress + (per_frame_progress * i),
                    frame_current=i+1,
                    frame_total=len(storyboard.frames)
                )
                
                # 同步依次等待上一帧结束
                processed_frame = await self.core.frame_processor(
                    frame=frame,
                    storyboard=storyboard,
                    config=config,
                    total_frames=len(storyboard.frames),
                    progress_callback=frame_progress_callback
                )
                storyboard.total_duration += processed_frame.duration
                logger.info(f"✅ Frame {i} completed ({processed_frame.duration:.2f}s)")

    async def post_production(self, ctx: PipelineContext):
        """第七步：后期制作。将产生的所有视频小片段拼接成完整长视频，并尝试混入背景音乐"""
        self._report_progress(ctx.progress_callback, "concatenating", 0.85)
        
        storyboard = ctx.storyboard
        # 收集所有分段视频的绝对路径
        segment_paths = [frame.video_segment_path for frame in storyboard.frames]
        
        video_service = VideoService()
        
        # 调用 ffmpeg 服务执行音视频混合轨道合并
        final_video_path = video_service.concat_videos(
            videos=segment_paths,
            output=ctx.final_video_path,
            bgm_path=ctx.params.get("bgm_path"),
            bgm_volume=ctx.params.get("bgm_volume", 0.2),
            bgm_mode=ctx.params.get("bgm_mode", "loop")
        )
        
        storyboard.final_video_path = final_video_path
        storyboard.completed_at = datetime.now()
        
        # 若用户请求中明确包含了绝对输出位置，则额外进行拷贝
        user_specified_output = ctx.params.get("output_path")
        if user_specified_output:
            Path(user_specified_output).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(final_video_path, user_specified_output)
            logger.info(f"📹 Final video copied to: {user_specified_output}")
            ctx.final_video_path = user_specified_output
            storyboard.final_video_path = user_specified_output
        
        logger.success(f"🎬 Video generation completed: {ctx.final_video_path}")

    async def finalize(self, ctx: PipelineContext) -> VideoGenerationResult:
        """第八步：流程收尾。将最终结果对象封装返回，并将中间过程的所有元数据及剧本固化保存至磁盘硬盘以备追溯。"""
        self._report_progress(ctx.progress_callback, "completed", 1.0)
        
        video_path_obj = Path(ctx.final_video_path)
        file_size = video_path_obj.stat().st_size
        
        result = VideoGenerationResult(
            video_path=ctx.final_video_path,
            storyboard=ctx.storyboard,
            duration=ctx.storyboard.total_duration,
            file_size=file_size
        )
        
        ctx.result = result
        
        logger.info(f"✅ Generated video: {ctx.final_video_path}")
        logger.info(f"   Duration: {ctx.storyboard.total_duration:.2f}s")
        logger.info(f"   Size: {file_size / (1024*1024):.2f} MB")
        logger.info(f"   Frames: {len(ctx.storyboard.frames)}")
        
        # 持久化元数据（包含执行日志与最终分镜记录）
        await self._persist_task_data(ctx)
        
        return result

    async def _persist_task_data(self, ctx: PipelineContext):
        """
        辅助方法：将任务的入参元数据、中间执行产生的分镜日志等落地为 json 文件以供前端读取历史记录。
        """
        try:
            storyboard = ctx.storyboard
            result = ctx.result
            task_id = storyboard.config.task_id
            
            if not task_id:
                logger.warning("No task_id in storyboard, skipping persistence")
                return
            
            # 重新拼装出供外部审查的元数据结构
            input_with_title = ctx.params.copy()
            input_with_title["text"] = ctx.input_text # Ensure text is included
            if not input_with_title.get("title"):
                input_with_title["title"] = storyboard.title
            
            metadata = {
                "task_id": task_id,
                "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
                "completed_at": storyboard.completed_at.isoformat() if storyboard.completed_at else None,
                "status": "completed",
                
                "input": input_with_title,
                
                "result": {
                    "video_path": result.video_path,
                    "duration": result.duration,
                    "file_size": result.file_size,
                    "n_frames": len(storyboard.frames)
                },
                
                "config": {
                    "llm_model": self.core.config.get("llm", {}).get("model", "unknown"),
                    "llm_base_url": self.core.config.get("llm", {}).get("base_url", "unknown"),
                    "comfyui_url": self.core.config.get("comfyui", {}).get("comfyui_url", "unknown"),
                    "runninghub_enabled": bool(self.core.config.get("comfyui", {}).get("runninghub_api_key")),
                }
            }
            
            # 调用文件管理服务存盘
            await self.core.persistence.save_task_metadata(task_id, metadata)
            logger.info(f"💾 Saved task metadata: {task_id}")
            
            # 详细包含图文音频拆分数据的剧本存盘
            await self.core.persistence.save_storyboard(task_id, storyboard)
            logger.info(f"💾 Saved storyboard: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to persist task data: {e}")
            # 保存数据失败不应中断或影响正常生成完成的流转，直接跳过并记录日志即可
