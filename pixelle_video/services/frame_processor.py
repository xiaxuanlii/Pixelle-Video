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
Frame processor - Process single frame through complete pipeline

分镜帧处理器模块。
负责协调单个分镜的完整端到端生产流水线：
旁白语音生成 (TTS) → 画面生成 (生图或生视频) → 画面渲染合成 (叠加模板) → 合成为视频片段。

核心特性：
- TTS 驱动的时长控制：将 TTS 生成的音频准确时长提取后，传递给后续的视频生成工作流，
  以确保最终生成的画面与语音完美同步对齐（无需后期的截断或填充补帧）。
"""

from typing import Callable, Optional

import httpx
from loguru import logger

from pixelle_video.models.progress import ProgressEvent
from pixelle_video.models.storyboard import Storyboard, StoryboardFrame, StoryboardConfig


class FrameProcessor:
    """
    分镜帧处理器类。
    
    作为流水线（Pipeline）中最重要的原子工作流引擎，它负责把抽象的分镜脚本
    转化为包含画面、旁白、字幕的真实视频媒体小片段。
    """
    
    def __init__(self, pixelle_video_core):
        """
        初始化帧处理器。
        
        Args:
            pixelle_video_core: PixelleVideoCore 的全局核心服务实例，用于获取底层的生图、TTS 等基础能力。
        """
        self.core = pixelle_video_core
    
    async def __call__(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig,
        total_frames: int = 1,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None
    ) -> StoryboardFrame:
        """
        执行单个分镜帧的完整加工流水线。
        
        执行步骤:
        1. 调用 TTS 将旁白文本转换为音频。
        2. 调用底层媒体引擎（如 ComfyKit）生成背景图片或背景视频片段。
        3. 调用 HTML 渲染器将模板、生成好的图片/视频、文本组合并渲染叠加。
        4. 使用 ffmpeg 将渲染好的画面与音频混合，合成出一个完整的分段小视频。
        
        Args:
            frame: 要处理的目标分镜数据对象。
            storyboard: 所属的完整剧本大纲对象。
            config: 全局生成配置对象。
            total_frames: 剧本中的总分镜数（用于计算总体进度）。
            progress_callback: （可选）用于向外汇报每一步进度的回调函数。
            
        Returns:
            StoryboardFrame: 处理完成后的分镜对象，内部的物理路径（音频、图片、最终视频段）已被填充。
        """
        logger.info(f"Processing frame {frame.index}...")
        
        frame_num = frame.index + 1
        
        # 判断当前帧是否需要生成全新的视觉媒体内容。
        # 如果 frame 中已经提前存在 image_path 或 video_path（例如在基于现有素材的工作流中），
        # 我们认为“已有媒体资源”并跳过 ComfyUI 的生成步骤。
        has_existing_media = frame.image_path is not None or frame.video_path is not None
        # 如果存在画面提示词，说明这是一个需要调用 AI 引擎生成画面的帧。
        needs_generation = frame.image_prompt is not None
        
        try:
            # Step 1: Generate audio (TTS) / 第一步：生成音频
            if not frame.audio_path:
                if progress_callback:
                    progress_callback(ProgressEvent(
                        event_type="frame_step",
                        progress=0.0,
                        frame_current=frame_num,
                        frame_total=total_frames,
                        step=1,
                        action="audio"
                    ))
                await self._step_generate_audio(frame, config)
            else:
                logger.debug(f"  1/4: Using existing audio: {frame.audio_path}")
            
            # Step 2: Generate media (image or video) / 第二步：调用底层大模型生成视觉媒体（图/视频）
            if needs_generation:
                if progress_callback:
                    progress_callback(ProgressEvent(
                        event_type="frame_step",
                        progress=0.25,
                        frame_current=frame_num,
                        frame_total=total_frames,
                        step=2,
                        action="media"
                    ))
                await self._step_generate_media(frame, config)
            elif has_existing_media:
                # 记录使用了现有媒体素材的日志
                if frame.video_path:
                    logger.debug(f"  2/4: Using existing video: {frame.video_path}")
                else:
                    logger.debug(f"  2/4: Using existing image: {frame.image_path}")
            else:
                # 某些特定静态模板不需要底图，直接跳过生成
                frame.image_path = None
                frame.media_type = None
                logger.debug(f"  2/4: Skipped media generation (not required by template)")
        
            # Step 3: Compose frame (add subtitle) / 第三步：画面渲染与文字合成
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.50 if (needs_generation or has_existing_media) else 0.33,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=3,
                    action="compose"
                ))
            await self._step_compose_frame(frame, storyboard, config)
            
            # Step 4: Create video segment / 第四步：合成视频与音频轨段
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.75 if (needs_generation or has_existing_media) else 0.67,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=4,
                    action="video"
                ))
            
            await self._step_create_video_segment(frame, config)
            
            logger.info(f"✅ Frame {frame.index} all steps completed")
            return frame

        except Exception as e:
            logger.error(f"❌ Failed to process frame {frame.index}: {e}")
            raise
    
    async def _step_generate_audio(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """内部步骤 1：利用 TTS 服务生成旁白录音"""
        logger.debug(f"  1/4: Generating audio for frame {frame.index}...")
        
        # 利用工具函数生成当前分镜音频的安全落盘路径
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "audio")
        
        # 组装透传给底层 TTS 服务的参数
        tts_params = {
            "text": frame.narration,
            "inference_mode": config.tts_inference_mode,
            "output_path": output_path,
            "index": frame.index + 1,  # 某些工作流中节点索引可能需要从 1 开始
        }
        
        if config.tts_inference_mode == "local":
            # 本地直接推理模式：仅支持基础的音色和语速
            if config.voice_id:
                tts_params["voice"] = config.voice_id
            if config.tts_speed is not None:
                tts_params["speed"] = config.tts_speed
        else:  # comfyui 模式
            # ComfyUI/RunningHub 云端模式：支持复杂工作流和声音克隆
            if config.tts_workflow:
                tts_params["workflow"] = config.tts_workflow
            if config.voice_id:
                tts_params["voice"] = config.voice_id
            if config.tts_speed is not None:
                tts_params["speed"] = config.tts_speed
            if config.ref_audio:
                tts_params["ref_audio"] = config.ref_audio
        
        # 触发生成并返回落盘位置
        audio_path = await self.core.tts(**tts_params)
        
        frame.audio_path = audio_path
        
        # 读取生成音频的精确时长，这个时长极为关键，将驱动后续生视频阶段的时长参数??为什么要通过音频去驱动生成视频的时长
        frame.duration = await self._get_audio_duration(audio_path)
        
        logger.debug(f"  ✓ Audio generated: {audio_path} ({frame.duration:.2f}s)")
    
    async def _step_generate_media(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """内部步骤 2：利用核心媒体服务生成背景图像或视频"""
        logger.debug(f"  2/4: Generating media for frame {frame.index}...")
        
        # Determine media type based on workflow/template.
        # video_ prefix in workflow name indicates ComfyUI video generation;
        # video_* templates can also use direct API video workflows.
        # 通过工作流配置文件的命名规约，简单判断底层是”生图”还是”生视频”
        workflow_name = config.media_workflow or ""
        from pixelle_video.utils.template_util import get_template_type
        template_type = get_template_type(config.frame_template or "")
        is_video_workflow = "video_" in workflow_name.lower() or template_type == "video"
        media_type = "video" if is_video_workflow else "image"
        
        logger.debug(f"  → Media type: {media_type} (workflow: {workflow_name})")
        
        # Build media generation parameters / 组装给 ComfyKit 的请求参数
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, media_type)
        api_video_params = dict(config.api_video_params or {}) if media_type == "video" else {}
        if media_type == "video" and workflow_name.startswith("api/"):
            await self._prepare_api_video_inputs(frame, config, api_video_params)

        media_params = {
            "prompt": frame.image_prompt,
            "workflow": config.media_workflow,  # None 时底层服务会使用系统默认值
            "media_type": media_type,
            "width": config.media_width,
            "height": config.media_height,
            "output_path": output_path,
            "image_path": frame.image_path,
            "index": frame.index + 1,  # 1-based index for workflow
        }
        media_params.update(api_video_params)
        
        # 非常关键：对于视频生成工作流，将前面 TTS 产生的精确音频时长传给底层，
        # 要求 AI 引擎生成出完全等长（或帧数对应）的视频片段，确保音画同步
        if is_video_workflow and frame.duration:
            media_params["duration"] = frame.duration
            logger.info(f"  → Generating video with target duration: {frame.duration:.2f}s (from TTS audio)")
        
        # 调用核心生成接口
        media_result = await self.core.media(**media_params)
        
        # 保存媒体的具体类型以便在 Step 4 时选择正确的合成策略
        frame.media_type = media_result.media_type
        
        if media_result.is_image:
            # 将生成的图片从云端或临时目录下载并固化到本任务专属的输出文件夹中
            local_path = await self._download_media(
                media_result.url,
                frame.index,
                config.task_id,
                media_type="image"
            )
            frame.image_path = local_path
            logger.debug(f"  ✓ Image generated: {local_path}")
        
        elif media_result.is_video:
            # 下载生成的视频片段
            local_path = await self._download_media(
                media_result.url,
                frame.index,
                config.task_id,
                media_type="video"
            )
            frame.video_path = local_path
            
            # 更新帧对象的实际视频时长
            if media_result.duration:
                frame.duration = media_result.duration
                logger.debug(f"  ✓ Video generated: {local_path} (duration: {frame.duration:.2f}s)")
            else:
                # 若返回结果未携带，则探查物理文件读取实际时长
                frame.duration = await self._get_video_duration(local_path)
                logger.debug(f"  ✓ Video generated: {local_path} (duration: {frame.duration:.2f}s)")
        
        else:
            raise ValueError(f"Unknown media type: {media_result.media_type}")

    async def _prepare_api_video_inputs(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig,
        api_video_params: dict,
    ) -> None:
        """Prepare provider-specific inputs for API video models."""
        from pixelle_video.utils.os_util import get_task_frame_path

        if api_video_params.pop("use_narration_audio_as_driving_audio", False):
            api_video_params["audio_path"] = frame.audio_path

        if frame.image_path or api_video_params.get("first_clip_path") or api_video_params.get("first_video_path"):
            return

        first_frame_workflow = api_video_params.pop("first_frame_workflow", None)
        if not first_frame_workflow:
            return

        first_frame_path = get_task_frame_path(config.task_id, frame.index, "image")
        logger.info(f"  → Generating API video first frame via {first_frame_workflow}")
        image_result = await self.core.media(
            prompt=frame.image_prompt,
            workflow=first_frame_workflow,
            media_type="image",
            width=config.media_width,
            height=config.media_height,
            output_path=first_frame_path,
            index=frame.index + 1,
        )
        frame.image_path = await self._download_media(
            image_result.url,
            frame.index,
            config.task_id,
            media_type="image",
        )
    
    async def _step_compose_frame(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig
    ):
        """内部步骤 3：加载 HTML 模板并组合排版生成覆盖层/基础画面"""
        logger.debug(f"  3/4: Composing frame {frame.index}...")
        
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "composed")
        
        # 当为视频时，HTML 模板通常负责渲染带有透明背景的字幕与装饰边框
        # 当为图片时，HTML 模板可能负责把背景图和文本一同渲染出来
        composed_path = await self._compose_frame_html(frame, storyboard, config, output_path)
        
        frame.composed_image_path = composed_path
        
        logger.debug(f"  ✓ Frame composed: {composed_path}")
    
    async def _compose_frame_html(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig,
        output_path: str
    ) -> str:
        """调用无头浏览器生成包含模板排版样式的最终静态截图"""
        from pixelle_video.services.frame_html import HTMLFrameGenerator
        from pixelle_video.utils.template_util import resolve_template_path
        
        template_path = resolve_template_path(config.frame_template)
        
        content_metadata = storyboard.content_metadata if storyboard else None
        
        # 准备透传给 HTML 模板的上下文变量
        ext = {
            "index": frame.index + 1,
        }
        
        if config.template_params:
            ext.update(config.template_params)
        
        generator = HTMLFrameGenerator(template_path)
        
        # 根据实际类型提供底图路径给模板进行注入
        media_path = frame.video_path if frame.media_type == "video" else frame.image_path
        logger.debug(f"Generating frame with media: '{media_path}' (type: {frame.media_type})")
        
        composed_path = await generator.generate_frame(
            title=storyboard.title,
            text=frame.narration,
            image=media_path,
            ext=ext,
            output_path=output_path
        )
        
        return composed_path
    
    async def _step_create_video_segment(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """内部步骤 4：将生成好的画面与音频轨道混合成 MP4 视频片段"""
        logger.debug(f"  4/4: Creating video segment for frame {frame.index}...")
        
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "segment")
        
        from pixelle_video.services.video import VideoService
        video_service = VideoService()
        
        # 根据画面是动态视频还是静态图片，采用不同的 FFmpeg 混合策略
        if frame.media_type == "video":
            # 动态视频策略：先将透明的 HTML 截图（字幕层）叠加到视频上，再替换音轨
            logger.debug(f"  → Using video-based composition with HTML overlay")
            
            # 第一阶段：叠图
            temp_video_with_overlay = get_task_frame_path(config.task_id, frame.index, "video") + "_overlay.mp4"
            
            video_service.overlay_image_on_video(
                video=frame.video_path,
                overlay_image=frame.composed_image_path,
                output=temp_video_with_overlay,
                scale_mode="contain"  # 强制视频尺寸适配模板设计的安全框大小
            )
            
            # 第二阶段：配音。替换或直接附加生成的旁白录音
            segment_path = video_service.merge_audio_video(
                video=temp_video_with_overlay,
                audio=frame.audio_path,
                output=output_path,
                replace_audio=True,  # 抛弃原视频的可能有杂音的音轨，仅使用生成的旁白
                audio_volume=1.0
            )
            
            # 清理过程产生的临时过度文件
            import os
            if os.path.exists(temp_video_with_overlay):
                os.unlink(temp_video_with_overlay)
        
        elif frame.media_type == "image" or frame.media_type is None:
            # 静态图片策略：将带有文字的合成长图基于音频时长拉长生成为静态视频流
            logger.debug(f"  → Using image-based composition")
            
            segment_path = video_service.create_video_from_image(
                image=frame.composed_image_path,
                audio=frame.audio_path,
                output=output_path,
                fps=config.video_fps
            )
        
        else:
            raise ValueError(f"Unknown media type: {frame.media_type}")
        
        # 记录处理完毕的切片文件位置
        frame.video_segment_path = segment_path
        
        logger.debug(f"  ✓ Video segment created: {segment_path}")
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """解析本地音频文件的精确时长（秒）"""
        try:
            # 优先使用 ffprobe 读取精准容器信息
            import ffmpeg
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}, using estimate")
            # 回退方案：如果 ffprobe 失败，通过文件大小粗略估算
            import os
            file_size = os.path.getsize(audio_path)
            # 粗略假设 MP3 码率约为 16kbps -> 约 2KB 每秒
            estimated_duration = file_size / 2000
            return max(1.0, estimated_duration)  # 保底算 1 秒
    
    async def _download_media(
        self,
        url: str,
        frame_index: int,
        task_id: str,
        media_type: str
    ) -> str:
        """Download media (image or video) from URL to local file / 异步从指定的 URL 下载生成的素材文件保存到本地任务目录"""
        import os
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(task_id, frame_index, media_type)

        if url.startswith("file://"):
            local_path = url[7:]
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Generated media file not found: {local_path}")
            return local_path

        if os.path.exists(url):
            return url
        
        timeout = httpx.Timeout(connect=10.0, read=60, write=60, pool=60)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        return output_path
    
    async def _get_video_duration(self, video_path: str) -> float:
        """解析本地视频文件的精确时长（秒）"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.warning(f"Failed to get video duration: {e}, using audio duration")
            # Fallback: use audio duration if available
            return 1.0  # Default to 1 second if unable to determine / 发生异常时保底返回 1 秒

