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
Resource discovery endpoints

此模块定义了资源发现 API 路由端点。
主要为前端提供各种可用资源列表（如：可用工作流、可用排版模板、可用背景音乐），
以便前端动态渲染下拉列表和选项框。
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.resources import (
    WorkflowInfo,
    WorkflowListResponse,
    TemplateInfo,
    TemplateListResponse,
    BGMInfo,
    BGMListResponse,
)
from pixelle_video.utils.os_util import list_resource_files, get_root_path, get_data_path
from pixelle_video.utils.template_util import get_all_templates_with_info

# 创建带有 "/resources" 前缀的 APIRouter，并在 Swagger 中归类为 "Resources"
router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/workflows/tts", response_model=WorkflowListResponse)
async def list_tts_workflows(pixelle_video: PixelleVideoDep):
    """
    获取所有可用的 TTS（文本转语音）工作流。
    
    合并返回 RunningHub 和本地托管（self-hosted）来源中的所有 TTS 配置文件。
    仅返回文件名以 "tts_" 开头的工作流。
    
    返回示例:
    ```json
    {
        "workflows": [
            {
                "name": "tts_edge.json",
                "display_name": "tts_edge.json - Runninghub",
                "source": "runninghub",
                "path": "workflows/runninghub/tts_edge.json",
                "key": "runninghub/tts_edge.json",
                "workflow_id": "123456"
            }
        ]
    }
    ```
    """
    try:
        # Get all workflows from TTS service / 从底层 TTS 服务查询所有被加载的工作流
        all_workflows = pixelle_video.tts.list_workflows()
        
        # Filter to TTS workflows only (filename starts with "tts_") / 过滤出以 tts_ 开头的文件
        tts_workflows = [
            WorkflowInfo(**wf) 
            for wf in all_workflows 
            if wf["name"].startswith("tts_")
        ]
        
        return WorkflowListResponse(workflows=tts_workflows)
        
    except Exception as e:
        logger.error(f"List TTS workflows error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/media", response_model=WorkflowListResponse)
async def list_media_workflows(pixelle_video: PixelleVideoDep):
    """
    获取所有可用的媒体（图像和视频）生成工作流。
    
    返回系统中所有负责产生画面的配置流，供用户在高级配置中选择特定的生图或生视频引擎策略。
    
    返回示例:
    ```json
    {
        "workflows": [
            {
                "name": "image_flux.json",
                "display_name": "image_flux.json - Runninghub",
                "source": "runninghub",
                "path": "workflows/runninghub/image_flux.json",
                "key": "runninghub/image_flux.json",
                "workflow_id": "123456"
            },
            {
                "name": "video_wan2.1.json",
                "display_name": "video_wan2.1.json - Runninghub",
                "source": "runninghub",
                "path": "workflows/runninghub/video_wan2.1.json",
                "key": "runninghub/video_wan2.1.json",
                "workflow_id": "123457"
            }
        ]
    }
    ```
    """
    try:
        # Get all workflows from media service (includes both image and video) / 从媒体服务获取所有流
        all_workflows = pixelle_video.media.list_workflows()
        
        media_workflows = [WorkflowInfo(**wf) for wf in all_workflows]
        
        return WorkflowListResponse(workflows=media_workflows)
        
    except Exception as e:
        logger.error(f"List media workflows error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Keep old endpoint for backward compatibility / 保留旧的独立端点，以防破坏早期版本客户端
@router.get("/workflows/image", response_model=WorkflowListResponse)
async def list_image_workflows(pixelle_video: PixelleVideoDep):
    """
    获取所有可用的生图工作流。（已弃用，建议改用 `/workflows/media`）
    
    此接口目前主要用于向后兼容，且内部通过过滤仅返回文件名以 "image_" 开头的工作流。
    """
    try:
        all_workflows = pixelle_video.media.list_workflows()
        
        # Filter to image workflows only (filename starts with "image_")
        image_workflows = [
            WorkflowInfo(**wf) 
            for wf in all_workflows 
            if wf["name"].startswith("image_")
        ]
        
        return WorkflowListResponse(workflows=image_workflows)
        
    except Exception as e:
        logger.error(f"List image workflows error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates():
    """
    获取所有可用的 HTML 视频排版模板。
    
    将自动扫描并合并系统默认目录（`templates/`）和用户自定义数据目录（`data/templates/`），
    并提取模板内置的 meta 标签来解析尺寸和方向。
    
    返回示例:
    ```json
    {
        "templates": [
            {
                "name": "image_default.html",
                "display_name": "image_default.html",
                "size": "1080x1920",
                "width": 1080,
                "height": 1920,
                "orientation": "portrait",
                "path": "templates/1080x1920/image_default.html",
                "key": "1080x1920/image_default.html"
            }
        ]
    }
    ```
    """
    try:
        # Get all templates with info / 通过辅助类自动抓取和解析 HTML 模板信息
        all_templates = get_all_templates_with_info()
        
        # Convert to API response format / 格式化为 API 返回结构
        templates = []
        for t in all_templates:
            templates.append(TemplateInfo(
                name=t.display_info.name,
                display_name=t.display_info.name,
                size=t.display_info.size,
                width=t.display_info.width,
                height=t.display_info.height,
                orientation=t.display_info.orientation,
                path=t.template_path,
                key=t.template_path
            ))
        
        return TemplateListResponse(templates=templates)
        
    except Exception as e:
        logger.error(f"List templates error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bgm", response_model=BGMListResponse)
async def list_bgm():
    """
    获取所有可用的背景音乐文件列表。
    
    扫描合并系统预置目录（`bgm/`）和用户自定义目录（`data/bgm/`）。
    如果存在同名文件，自定义目录中的文件优先级更高。
    
    支持格式: mp3, wav, flac, m4a, aac, ogg
    
    返回示例:
    ```json
    {
        "bgm_files": [
            {
                "name": "default.mp3",
                "path": "bgm/default.mp3",
                "source": "default"
            },
            {
                "name": "happy.mp3",
                "path": "data/bgm/happy.mp3",
                "source": "custom"
            }
        ]
    }
    ```
    """
    try:
        # Supported audio extensions / 支持扫描的音频扩展名白名单
        audio_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg')
        
        # Collect BGM files from both locations / 用于合并两个目录结果并去重的字典
        bgm_files_dict = {}  # {filename: {"path": str, "source": str}}
        
        # Scan default bgm/ directory / 扫描系统自带默认目录
        default_bgm_dir = Path(get_root_path("bgm"))
        if default_bgm_dir.exists() and default_bgm_dir.is_dir():
            for item in default_bgm_dir.iterdir():
                if item.is_file() and item.suffix.lower() in audio_extensions:
                    bgm_files_dict[item.name] = {
                        "path": f"bgm/{item.name}",
                        "source": "default"
                    }
        
        # Scan custom data/bgm/ directory (overrides default) / 扫描自定义挂载目录（存在同名则覆盖）
        custom_bgm_dir = Path(get_data_path("bgm"))
        if custom_bgm_dir.exists() and custom_bgm_dir.is_dir():
            for item in custom_bgm_dir.iterdir():
                if item.is_file() and item.suffix.lower() in audio_extensions:
                    bgm_files_dict[item.name] = {
                        "path": f"data/bgm/{item.name}",
                        "source": "custom"
                    }
        
        # Convert to response format / 对合并后的字典排序并转为模型列表
        bgm_files = [
            BGMInfo(
                name=name,
                path=info["path"],
                source=info["source"]
            )
            for name, info in sorted(bgm_files_dict.items())
        ]
        
        return BGMListResponse(bgm_files=bgm_files)
        
    except Exception as e:
        logger.error(f"List BGM error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

