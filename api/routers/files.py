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
File service endpoints

此模块提供了一个静态文件代理服务路由，用于向外部客户端暴露服务器本地生成的或预置的静态文件。
支持访问生成的视频、图片、音频以及系统自带的 HTML 模板、工作流配置和背景音乐等资源。
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

# 创建带有 "/files" 前缀的 APIRouter，并在 Swagger 中归类为 "Files"
router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{file_path:path}")
async def get_file(file_path: str):
    """
    静态文件访问端点。
    
    为了安全起见，此接口严格限制了能够访问的本地目录白名单。
    允许访问的目录包括：
    - `output/` - 系统生成的动态文件（如最终的视频、图片帧、语音文件等）。
    - `workflows/` - ComfyUI 的工作流 JSON 配置文件。
    - `templates/` - 预置的 HTML 视频排版模板。
    - `bgm/` - 预置的背景音乐。
    - `data/bgm/` - 用户自定义的背景音乐。
    - `data/templates/` - 用户自定义的 HTML 模板。
    - `resources/` - 其他静态资源（如图标、字体、背景图等）。
    
    请求参数说明：
    - **file_path**: 相对于上述白名单目录的文件路径。
    
    路由解析示例：
    - "abc123.mp4" → 将默认解析为 `output/abc123.mp4`（兼容旧版路径）。
    - "workflows/runninghub/image_flux.json" → 解析为本地的 `workflows/runninghub/image_flux.json`。
    - "templates/1080x1920/image_default.html" → 解析为本地的 `templates/1080x1920/image_default.html`。
    - "bgm/default.mp3" → 解析为本地的 `bgm/default.mp3`。
    - "resources/example.png" → 解析为本地的 `resources/example.png`。
    
    返回：
        FileResponse: 用于浏览器内联预览或直接下载的文件流。
    """
    try:
        # 定义允许访问的安全目录前缀列表（按优先级排列）
        allowed_prefixes = [
            "output/",
            "workflows/",
            "templates/",
            "bgm/",
            "data/bgm/",
            "data/templates/",
            "resources/",
        ]
        
        # 检查传入的文件路径是否包含上述安全前缀
        full_path = None
        for prefix in allowed_prefixes:
            if file_path.startswith(prefix):
                full_path = file_path
                break
        
        # 兼容性处理：如果路径没有匹配任何已知前缀，则默认它位于 output 目录下
        if full_path is None:
            full_path = f"output/{file_path}"
        
        # 将相对路径转换为绝对路径（基于项目的当前工作目录）
        abs_path = Path.cwd() / full_path
        
        if not abs_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        if not abs_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {file_path}")
        
        # 目录越权安全检查：防止利用 ../ 等方式跳出工作目录读取敏感系统文件
        try:
            # 确认该文件的实际解析路径仍在当前工作目录之内
            rel_path = abs_path.relative_to(Path.cwd())
            rel_path_str = str(rel_path)
            
            # 再次确保最终访问的文件确实在允许的目录列表下
            is_allowed = any(rel_path_str.startswith(prefix.rstrip('/')) for prefix in allowed_prefixes)
            
            if not is_allowed:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied: only {', '.join(p.rstrip('/') for p in allowed_prefixes)} directories are accessible"
                )
        except ValueError:
            # relative_to 抛出 ValueError 说明该路径不在当前工作目录中
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine media type / 根据文件后缀推断 MIME 类型，以便浏览器正确渲染或提示下载
        suffix = abs_path.suffix.lower()
        media_types = {
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.html': 'text/html',
            '.json': 'application/json',
        }
        media_type = media_types.get(suffix, 'application/octet-stream')
        
        # 使用 inline disposition 来支持浏览器内联预览（而不是强制下载）
        return FileResponse(
            path=str(abs_path),
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{abs_path.name}"'
            }
        )
        
    except HTTPException:
        # 直接抛出 FastAPI 预定义的异常
        raise
    except Exception as e:
        logger.error(f"File access error: {e}")
        # 其他未知异常包装为 500 错误
        raise HTTPException(status_code=500, detail=str(e))

