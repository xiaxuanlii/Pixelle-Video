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
Video generation endpoints

此模块定义了视频生成的核心 API 路由端点。
支持同步生成（请求阻塞直到完成）和异步生成（返回任务 ID，可通过轮询获取状态）两种模式。
"""

import os
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.video import (
    VideoGenerateRequest,
    VideoGenerateResponse,
    VideoGenerateAsyncResponse,
)
from api.tasks import task_manager, TaskType

# 创建带有 "/video" 前缀的 APIRouter，并在 Swagger 中归类为 "Video Generation"
router = APIRouter(prefix="/video", tags=["Video Generation"])


def path_to_url(request: Request, file_path: str) -> str:
    """
    将本地文件路径转换为可通过 API 访问的网络 URL。
    
    此函数处理绝对路径和相对路径，提取出相对于 `output` 目录的子路径，
    并结合当前 FastAPI 请求的 Base URL 拼装成完整的文件访问地址。
    
    Args:
        request: FastAPI 请求对象（提供当前请求的真实 host 和协议）。
        file_path: 视频文件的绝对或相对本地路径。
    
    Returns:
        str: 客户端可直接访问的完整 URL。
    
    Examples:
        Windows: G:\\...\\output\\20251205_233630_c939\\final.mp4
              -> http://localhost:8000/api/files/20251205_233630_c939/final.mp4
        
        Linux:   /home/user/.../output/20251205_233630_c939/final.mp4
              -> http://localhost:8000/api/files/20251205_233630_c939/final.mp4
    """
    from pathlib import Path
    import os
    
    # 首先将路径分隔符规范化为正斜杠（为了跨平台兼容性）
    file_path = file_path.replace("\\", "/")
    
    # 检查是否为绝对路径（兼容 Windows 和 Linux）
    is_absolute = os.path.isabs(file_path) or Path(file_path).is_absolute()
    
    if is_absolute:
        # 在路径中查找 "output" 目录，并截取其之后的所有部分
        parts = file_path.split("/")
        try:
            output_idx = parts.index("output")
            relative_parts = parts[output_idx + 1:]
            file_path = "/".join(relative_parts)
        except ValueError:
            # 如果路径中没有 "output"，则只使用文件名
            file_path = Path(file_path).name
    else:
        # 如果是相对路径且以 "output/" 开头，则去掉该前缀
        if file_path.startswith("output/"):
            file_path = file_path[7:]
    
    # 使用 request 的 base_url 构建最终 URL（自动匹配请求的域名或 IP）
    base_url = str(request.base_url).rstrip('/')
    return f"{base_url}/api/files/{file_path}"


@router.post("/generate/sync", response_model=VideoGenerateResponse)
async def generate_video_sync(
    request_body: VideoGenerateRequest,
    pixelle_video: PixelleVideoDep,
    request: Request
):
    """
    同步视频生成端点。
    
    此接口会一直阻塞等待，直到整个视频生成工作流完成才返回结果。
    适合生成时间较短（通常 < 30 秒）的小视频。
    
    **注意**：对于需要长时间生成的大型视频，可能会导致 HTTP 请求超时。
    建议使用 `/generate/async` 接口替代。
    
    请求体包含了视频生成的所有配置参数，详情参见 `VideoGenerateRequest` 数据模型。
    
    返回：
        VideoGenerateResponse: 包含生成的视频 URL、总时长和文件大小。
    """
    try:
        logger.info(f"Sync video generation: {request_body.text[:50]}...")
        
        # 强制要求提供 HTML 模板，并通过解析模板的 meta 标签自动确定视频画面的宽高尺寸
        if not request_body.frame_template:
            raise ValueError("frame_template is required to determine media size")
        
        from pixelle_video.services.frame_html import HTMLFrameGenerator
        from pixelle_video.utils.template_util import resolve_template_path
        
        # 解析模板真实路径并获取尺寸元数据
        template_path = resolve_template_path(request_body.frame_template)
        generator = HTMLFrameGenerator(template_path)
        media_width, media_height = generator.get_media_size()
        logger.debug(f"Auto-determined media size from template: {media_width}x{media_height}")
        
        # Build video generation parameters / 构建传递给底层引擎的视频生成参数字典
        video_params = {
            "text": request_body.text,
            "mode": request_body.mode,
            "title": request_body.title,
            "n_scenes": request_body.n_scenes,
            "min_narration_words": request_body.min_narration_words,
            "max_narration_words": request_body.max_narration_words,
            "min_image_prompt_words": request_body.min_image_prompt_words,
            "max_image_prompt_words": request_body.max_image_prompt_words,
            "media_width": media_width,     # 自动解析得到的宽度
            "media_height": media_height,   # 自动解析得到的高度
            "media_workflow": request_body.media_workflow,
            "video_fps": request_body.video_fps,
            "frame_template": request_body.frame_template,
            "prompt_prefix": request_body.prompt_prefix,
            "bgm_path": request_body.bgm_path,
            "bgm_volume": request_body.bgm_volume,
        }
        
        # Add TTS workflow if specified / 添加 TTS 工作流配置
        if request_body.tts_workflow:
            video_params["tts_workflow"] = request_body.tts_workflow
        
        # Add ref_audio if specified / 添加声音克隆参考音频
        if request_body.ref_audio:
            video_params["ref_audio"] = request_body.ref_audio
        
        # Legacy voice_id support (deprecated) / 兼容旧版的音色参数
        if request_body.voice_id:
            logger.warning("voice_id parameter is deprecated, please use tts_workflow instead")
            video_params["voice_id"] = request_body.voice_id
        
        # Add custom template parameters if specified / 添加向 HTML 模板注入的自定义参数
        if request_body.template_params:
            video_params["template_params"] = request_body.template_params
        
        # Call video generator service / 调用核心业务方法生成最终视频
        result = await pixelle_video.generate_video(**video_params)
        
        # Get file size / 计算生成文件的字节大小
        file_size = os.path.getsize(result.video_path) if os.path.exists(result.video_path) else 0
        
        # Convert path to URL / 转换为网络 URL
        video_url = path_to_url(request, result.video_path)
        
        return VideoGenerateResponse(
            video_url=video_url,
            duration=result.duration,
            file_size=file_size
        )
        
    except Exception as e:
        logger.error(f"Sync video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/async", response_model=VideoGenerateAsyncResponse)
async def generate_video_async(
    request_body: VideoGenerateRequest,
    pixelle_video: PixelleVideoDep,
    request: Request
):
    """
    异步视频生成端点。
    
    在后台创建一个视频生成任务，并立即向客户端返回一个唯一的 task_id。
    客户端可以使用此 task_id 来轮询追踪任务进度。
    
    **典型交互流程:**
    1. 客户端提交视频生成请求到本接口。
    2. 服务端接收请求并返回 `task_id`。
    3. 客户端定时轮询 `/api/tasks/{task_id}` 获取任务执行状态和进度条。
    4. 当任务状态变为 "completed" 时，客户端可从任务结果中提取生成的视频 URL。
    
    请求参数与同步生成接口一致，请参见 `VideoGenerateRequest`。
    
    返回：
        VideoGenerateAsyncResponse: 包含刚创建的 task_id。
    """
    try:
        logger.info(f"Async video generation: {request_body.text[:50]}...")
        
        # Create task / 在任务管理器中注册新任务
        task = task_manager.create_task(
            task_type=TaskType.VIDEO_GENERATION,
            request_params=request_body.model_dump()
        )
        
        # Define async execution function / 定义内部异步执行闭包
        async def execute_video_generation():
            """在后台实际执行视频生成的逻辑"""
            # 自动通过 HTML 模板确定媒体文件的分辨率尺寸
            if not request_body.frame_template:
                raise ValueError("frame_template is required to determine media size")
            
            from pixelle_video.services.frame_html import HTMLFrameGenerator
            from pixelle_video.utils.template_util import resolve_template_path
            
            template_path = resolve_template_path(request_body.frame_template)
            generator = HTMLFrameGenerator(template_path)
            media_width, media_height = generator.get_media_size()
            logger.debug(f"Auto-determined media size from template: {media_width}x{media_height}")
            
            # 构建参数字典
            video_params = {
                "text": request_body.text,
                "mode": request_body.mode,
                "title": request_body.title,
                "n_scenes": request_body.n_scenes,
                "min_narration_words": request_body.min_narration_words,
                "max_narration_words": request_body.max_narration_words,
                "min_image_prompt_words": request_body.min_image_prompt_words,
                "max_image_prompt_words": request_body.max_image_prompt_words,
                "media_width": media_width,
                "media_height": media_height,
                "media_workflow": request_body.media_workflow,
                "video_fps": request_body.video_fps,
                "frame_template": request_body.frame_template,
                "prompt_prefix": request_body.prompt_prefix,
                "bgm_path": request_body.bgm_path,
                "bgm_volume": request_body.bgm_volume,
                # 如果底层引擎支持进度回调，可在此处绑定，更新任务管理器的进度
                # "progress_callback": lambda event: task_manager.update_progress(...)
            }
            
            if request_body.tts_workflow:
                video_params["tts_workflow"] = request_body.tts_workflow
            
            if request_body.ref_audio:
                video_params["ref_audio"] = request_body.ref_audio
            
            if request_body.voice_id:
                logger.warning("voice_id parameter is deprecated, please use tts_workflow instead")
                video_params["voice_id"] = request_body.voice_id
            
            if request_body.template_params:
                video_params["template_params"] = request_body.template_params
            
            # 核心调用：执行耗时的视频合成流水线
            result = await pixelle_video.generate_video(**video_params)
            
            # 获取结果信息并封装返回值给 task
            file_size = os.path.getsize(result.video_path) if os.path.exists(result.video_path) else 0
            video_url = path_to_url(request, result.video_path)
            
            return {
                "video_url": video_url,
                "duration": result.duration,
                "file_size": file_size
            }
        
        # Start execution / 将闭包提交到后台任务管理器中调度执行
        await task_manager.execute_task(
            task_id=task.task_id,
            coro_func=execute_video_generation
        )
        
        # 立即向客户端返回 task_id
        return VideoGenerateAsyncResponse(
            task_id=task.task_id
        )
        
    except Exception as e:
        logger.error(f"Async video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

