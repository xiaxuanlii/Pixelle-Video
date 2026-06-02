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
Template utility functions for size parsing and template management

模板引擎相关的辅助工具模块。
提供对 HTML 模板的目录扫描、视频尺寸及类型推断的元数据解析功能，
是连接业务层配置与前端展示控件的核心桥梁。
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field
import logging

from pixelle_video.utils.os_util import (
    get_resource_path,
    list_resource_files,
    list_resource_dirs,
    resource_exists
)

logger = logging.getLogger(__name__)


def parse_template_size(template_path: str) -> Tuple[int, int]:
    """
    从模板的目录名称中提取目标生成视频的分辨率尺寸。
    
    模板存放的标准规约约定，模板文件必须放在表示尺寸的文件夹内（如 `1080x1920/default.html`）。
    
    Args:
        template_path: 模板的相对路径标识。
    
    Returns:
        Tuple[int, int]: (宽度, 高度) 像素值。
    
    Raises:
        ValueError: 当目录名称格式不是规范的 "WIDTHxHEIGHT" 时抛出。
    """
    path = Path(template_path)
    
    # 获取父级目录名，理论上该名称即为尺寸标识
    dir_name = path.parent.name
    
    if dir_name == "templates":
        raise ValueError(
            f"Invalid template path format: {template_path}. "
            f"Expected format: 'WIDTHxHEIGHT/template.html' or 'templates/WIDTHxHEIGHT/template.html'"
        )
    
    # 强制验证尺寸格式
    if 'x' not in dir_name:
        raise ValueError(
            f"Invalid size format in path: {template_path}. "
            f"Directory name should be 'WIDTHxHEIGHT' (e.g., '1080x1920')"
        )
    
    try:
        width_str, height_str = dir_name.split('x')
        width = int(width_str)
        height = int(height_str)
        
        # 边界与理智检查防呆
        if width < 100 or height < 100 or width > 10000 or height > 10000:
            raise ValueError(f"Invalid size dimensions: {width}x{height}")
        
        return (width, height)
    except ValueError as e:
        raise ValueError(
            f"Failed to parse size from path: {template_path}. "
            f"Expected format: 'WIDTHxHEIGHT/template.html' (e.g., '1080x1920/default.html'). "
            f"Error: {e}"
        )


def list_available_sizes() -> List[str]:
    """
    合并列出系统中支持的所有排版尺寸规格。
    
    Returns:
        List[str]: 形如 ["1080x1080", "1080x1920"] 的字符串列表。
    """
    # Use new resource API to merge default and custom directories
    all_dirs = list_resource_dirs("templates")
    
    # Filter to only valid size formats (WIDTHxHEIGHT)
    sizes = []
    for dir_name in all_dirs:
        if 'x' in dir_name:
            try:
                width, height = dir_name.split('x')
                int(width)
                int(height)
                sizes.append(dir_name)
            except (ValueError, AttributeError):
                # 跳过格式不正确的冗余目录
                continue
    
    return sorted(sizes)


def list_templates_for_size(size: str) -> List[str]:
    """
    获取某个特定尺寸目录下所有可用的 HTML 排版模板名称。
    
    Args:
        size: 尺寸标识符。
    
    Returns:
        List[str]: 文件名列表。
    """
    # Use new resource API to merge default and custom templates
    all_files = list_resource_files("templates", size)
    
    # Filter to only HTML files
    templates = [f for f in all_files if f.endswith('.html')]
    
    return sorted(templates)


def get_template_full_path(size: str, template_name: str) -> str:
    """
    通过底层 os_util 函数级联查询，获得某个尺寸下特定模板的绝对物理路径。
    """
    # Use new resource API to search custom first, then default
    try:
        return get_resource_path("templates", size, template_name)
    except FileNotFoundError:
        available_templates = list_templates_for_size(size)
        raise FileNotFoundError(
            f"Template not found: {size}/{template_name}\n"
            f"Available templates for size {size}: {available_templates}"
        )


class TemplateDisplayInfo(BaseModel):
    """用于前端展示和渲染交互选项卡的模板元数据对象"""
    
    name: str = Field(..., description="模板文件名")
    size: str = Field(..., description="所属的分辨率尺寸目录名称")
    width: int = Field(..., description="最终视频画面宽度")
    height: int = Field(..., description="最终视频画面高度")
    orientation: Literal['portrait', 'landscape', 'square'] = Field(
        ..., 
        description="画幅朝向标识 (竖屏、横屏、方屏)"
    )
    is_standard: bool = Field(
        ..., 
        description="该尺寸规格是否为常见的主流标准规格（用于 UI 置顶等）"
    )


class TemplateInfo(BaseModel):
    """完整的带有 API 交互路径标识的模板描述模型"""
    
    template_path: str = Field(..., description="系统内部使用的带有尺寸前缀的请求路径")
    display_info: TemplateDisplayInfo = Field(..., description="供前端展示解析的具体配置元数据")


def format_template_display_info(template_name: str, size: str) -> TemplateDisplayInfo:
    """
    提取并格式化有关模板和尺寸信息的展示元数据。
    """
    # Keep full template name with .html extension
    name = template_name
    
    # Parse size
    width, height = map(int, size.split('x'))
    
    # Detect orientation
    if height > width:
        orientation = 'portrait'
    elif width > height:
        orientation = 'landscape'
    else:
        orientation = 'square'
    
    # Check if it's a standard size (only these three)
    is_standard = (width, height) in [(1080, 1920), (1920, 1080), (1080, 1080)]
    
    return TemplateDisplayInfo(
        name=name,
        size=size,
        width=width,
        height=height,
        orientation=orientation,
        is_standard=is_standard
    )


def get_all_templates_with_info() -> List[TemplateInfo]:
    """
    暴力的全局扫描器：获取并组合返回系统加载的所有模板的详细信息对象。
    """
    result = []
    sizes = list_available_sizes()
    
    for size in sizes:
        templates = list_templates_for_size(size)
        for template in templates:
            display_info = format_template_display_info(template, size)
            full_path = f"{size}/{template}"
            result.append(TemplateInfo(
                template_path=full_path,
                display_info=display_info
            ))
    
    return result


def get_templates_grouped_by_size() -> dict:
    """
    按尺寸分组返回所有的模板元数据（优先竖排显示）。
    """
    from collections import defaultdict
    
    templates = get_all_templates_with_info()
    grouped = defaultdict(list)
    
    for t in templates:
        grouped[t.display_info.size].append(t)
    
    # Sort groups by orientation priority: portrait > landscape > square
    orientation_priority = {'portrait': 0, 'landscape': 1, 'square': 2}
    
    sorted_grouped = {}
    for size in sorted(grouped.keys(), key=lambda s: (
        orientation_priority.get(grouped[s][0].display_info.orientation, 3),
        s
    )):
        sorted_grouped[size] = sorted(grouped[size], key=lambda t: t.display_info.name)
    
    return sorted_grouped


def resolve_template_path(template_input: Optional[str]) -> str:
    """
    将松散的用户输入解析/猜测为服务器上真实的模板本地物理路径。
    
    兼容并支持的输入形式:
        - None: 系统将自动回退使用默认的竖版图文模板 "1080x1920/image_default.html"。
        - "template.html": 仅传文件名时，将回退使用默认竖屏尺寸的同名模板。
        - "1080x1920/template.html": （推荐）标准的资源定位标识。
    
    Returns:
        str: 真实的绝对路径。
        
    Raises:
        FileNotFoundError: 未匹配到可用模板资源时。
    """
    # Default case
    if template_input is None:
        template_input = "1080x1920/image_default.html"
    
    # Parse input to extract size and template name
    size = None
    template_name = None
    
    # Handle different input formats
    if template_input.startswith("templates/") or template_input.startswith("data/templates/"):
        # Legacy full path format - extract size and name
        parts = Path(template_input).parts
        if len(parts) >= 3:
            size = parts[-2]
            template_name = parts[-1]
    elif '/' in template_input and 'x' in template_input.split('/')[0]:
        # "1080x1920/template.html" format
        size, template_name = template_input.split('/', 1)
    else:
        # Just template name - use default size
        size = "1080x1920"
        template_name = template_input
    
    # Backward compatibility: migrate "default.html" to "image_default.html"
    if template_name == "default.html":
        migrated_name = "image_default.html"
        try:
            # Try migrated name first
            path = get_resource_path("templates", size, migrated_name)
            logger.info(f"Backward compatibility: migrated '{template_input}' to '{size}/{migrated_name}'")
            return path
        except FileNotFoundError:
            # Fall through to try original name
            logger.warning(f"Migrated template '{size}/{migrated_name}' not found, trying original name")
    
    # Use resource API to resolve path (custom > default)
    try:
        return get_resource_path("templates", size, template_name)
    except FileNotFoundError:
        available_sizes = list_available_sizes()
        raise FileNotFoundError(
            f"Template not found: {size}/{template_name}\n"
            f"Available sizes: {available_sizes}\n"
            f"Hint: Use format 'SIZExSIZE/template.html' (e.g., '1080x1920/image_default.html')"
        )


def get_template_type(template_name: str) -> Literal['static', 'image', 'video']:
    """
    通过文件名命名前缀探测模板对于底层媒体资产消耗的诉求类型。
    
    命名规约:
    - static_*.html: 纯文本/静态排版，跳过耗时耗钱的大模型背景图和视频的生成。
    - image_*.html: 标准视频，需要调用 AI 绘画引擎生成与之匹配的背景底图。
    - video_*.html: 动态模板，需要调用更高级的视频模型生成动态背景素材。
    
    Args:
        template_name: 模板文件名。
    
    Returns:
        探测出的类型枚举标识。
    """
    name = Path(template_name).name
    
    if name.startswith("static_"):
        return "static"
    elif name.startswith("video_"):
        return "video"
    elif name.startswith("image_"):
        return "image"
    else:
        # Fallback: try to detect from legacy names
        logger.warning(
            f"Template '{template_name}' doesn't follow naming convention (static_/image_/video_). "
            f"Defaulting to 'image' type."
        )
        return "image"


def filter_templates_by_type(
    templates: List[TemplateInfo], 
    template_type: Literal['static', 'image', 'video']
) -> List[TemplateInfo]:
    """过滤只留下符合指定前缀类型的模板列表"""
    filtered = []
    for t in templates:
        template_name = t.display_info.name
        if get_template_type(template_name) == template_type:
            filtered.append(t)
    return filtered


def get_templates_grouped_by_size_and_type(
    template_type: Optional[Literal['static', 'image', 'video']] = None
) -> dict:
    """提供带有类型过滤功能的分组抓取模板元数据集的服务函数"""
    from collections import defaultdict
    
    templates = get_all_templates_with_info()
    
    # Filter by type if specified
    if template_type is not None:
        templates = filter_templates_by_type(templates, template_type)
    
    grouped = defaultdict(list)
    
    for t in templates:
        grouped[t.display_info.size].append(t)
    
    # Sort groups by orientation priority: portrait > landscape > square
    orientation_priority = {'portrait': 0, 'landscape': 1, 'square': 2}
    
    sorted_grouped = {}
    for size in sorted(grouped.keys(), key=lambda s: (
        orientation_priority.get(grouped[s][0].display_info.orientation, 3),
        s
    )):
        sorted_grouped[size] = sorted(grouped[size], key=lambda t: t.display_info.name)
    
    return sorted_grouped