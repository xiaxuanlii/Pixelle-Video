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
OS utilities for file and path management

操作系统及文件路径管理工具模块。
为系统提供标准化、安全的目录解析和文件管理服务。
支持覆盖机制（如：优先从用户的 data/ 目录加载自定义素材，再降级到系统预置库）。
"""

import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Literal


def get_pixelle_video_root_path() -> str:
    """
    获取 Pixelle-Video 的项目根目录路径。
    
    优先检查 `PIXELLE_VIDEO_ROOT` 环境变量。这确保了无论是通过源码运行
    还是被打包安装后执行，都能准确找到资源和配置文件所在的工作区。
    
    Returns:
        str: 项目的绝对根路径。
    """
    # Check environment variable (required for reliable operation)
    env_root = os.environ.get("PIXELLE_VIDEO_ROOT")
    if env_root and Path(env_root).exists():
        return str(Path(env_root).resolve())
    
    # 如果环境变量未设置，则降级使用当前执行目录 (CWD)
    return str(Path.cwd())


def ensure_pixelle_video_root_path() -> str:
    """
    确保 Pixelle-Video 根路径及其必须的 output 目录存在。
    
    Returns:
        str: 根路径字符串。
    """
    root_path = get_pixelle_video_root_path()
    root_path_obj = Path(root_path)
    output_dir = root_path_obj / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return root_path


def get_root_path(*paths: str) -> str:
    """
    基于项目根目录拼接并获取绝对路径。
    
    Args:
        *paths: 路径子组件。
    
    Returns:
        str: 拼接后的绝对路径。
    """
    root_path = ensure_pixelle_video_root_path()
    if paths:
        return os.path.join(root_path, *paths)
    return root_path


def get_temp_path(*paths: str) -> str:
    """
    获取 temp 临时文件夹下的路径，并确保该目录存在。
    
    Args:
        *paths: 路径子组件。
    
    Returns:
        str: 临时目录或文件的绝对路径。
    """
    temp_path = get_root_path("temp")
    
    # Ensure temp directory exists
    os.makedirs(temp_path, exist_ok=True)
    
    if paths:
        return os.path.join(temp_path, *paths)
    return temp_path


def get_data_path(*paths: str) -> str:
    """
    获取 data 用户数据文件夹下的路径，并确保该目录存在。
    用于挂载 Docker 数据卷存放用户的自定义资源。

    Args:
        *paths: 路径子组件。
    
    Returns:
        str: 数据目录或文件的绝对路径。
    """
    data_path = get_root_path("data")

    # Ensure data directory exists
    os.makedirs(data_path, exist_ok=True)
    
    if paths:
        return os.path.join(data_path, *paths)
    return data_path


def get_output_path(*paths: str) -> str:
    """
    获取 output 生成结果文件夹下的路径，并确保该目录存在。

    Args:
        *paths: 路径子组件。
    
    Returns:
        str: 输出目录或文件的绝对路径。
    """
    output_path = get_root_path("output")

    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    if paths:
        return os.path.join(output_path, *paths)
    return output_path


def save_bytes_to_file(data: bytes, file_path: str) -> str:
    """
    将二进制字节流保存为物理文件，并自动创建缺失的父级目录。
    
    Args:
        data: 二进制数据。
        file_path: 目标保存路径。
    
    Returns:
        str: 保存成功的文件的绝对路径。
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write binary data
    with open(file_path, "wb") as f:
        f.write(data)
    
    return os.path.abspath(file_path)


def ensure_dir(path: str) -> str:
    """
    确保指定目录存在，不存在则递归创建。
    
    Args:
        path: 目标目录路径。
    
    Returns:
        str: 该目录的绝对路径。
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


# ========== Task Directory Management / 任务目录管理 ==========

def create_task_id() -> str:
    """
    生成一个全局唯一的任务 ID (时间戳 + 随机后缀)。
    
    格式: {YYYYMMDD}_{HHMMSS}_{random_hex}
    示例: "20251028_143052_ab3d"
    
    Returns:
        str: 生成的任务 ID。
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = f"{random.randint(0, 0xFFFF):04x}"  # 4 位十六进制数 (0000-ffff)
    return f"{timestamp}_{random_suffix}"


def create_task_output_dir(task_id: Optional[str] = None) -> Tuple[str, str]:
    """
    为单次视频生成任务创建一个独立的隔离目录结构。
    
    创建的目录结构示例:
        output/{task_id}/
        ├── final.mp4           # 最终合成的长视频
        ├── frames/             # 中间切片与分镜素材
        │   ├── 01_audio.mp3
        │   ├── 01_image.png
        │   ├── 01_composed.png
        │   ├── 01_segment.mp4
        │   └── ...
        └── metadata.json       # 记录执行元数据
    
    Args:
        task_id: 可选。指定任务 ID，未指定则自动生成。
    
    Returns:
        Tuple[str, str]: (任务的绝对根目录, 任务ID)
    """
    if task_id is None:
        task_id = create_task_id()
    
    task_dir = get_output_path(task_id)
    frames_dir = os.path.join(task_dir, "frames")
    
    # Create directories
    os.makedirs(frames_dir, exist_ok=True)
    
    return task_dir, task_id


def get_task_path(task_id: str, *paths: str) -> str:
    """
    获取指定任务目录下的某个子路径。
    
    Args:
        task_id: 任务 ID。
        *paths: 路径子组件。
    
    Returns:
        str: 绝对路径。
    """
    task_dir = get_output_path(task_id)
    if paths:
        return os.path.join(task_dir, *paths)
    return task_dir


def get_task_frame_path(
    task_id: str, 
    frame_index: int, 
    file_type: Literal["audio", "image", "video", "composed", "segment"]
) -> str:
    """
    获取某个任务中特定分镜素材的规范化保存路径。
    
    为保证目录排序和可读性，分镜文件名统一使用 01 起步的两位数补零索引。
    
    Args:
        task_id: 任务 ID。
        frame_index: 内部数组的分镜索引（从 0 开始）。
        file_type: 素材类型枚举。
    
    Returns:
        str: 物理文件的绝对存放路径。
    """
    ext_map = {
        "audio": "mp3",
        "image": "png",
        "video": "mp4",
        "composed": "png",
        "segment": "mp4"
    }
    
    # Frame number starts from 01 for better human readability
    filename = f"{frame_index + 1:02d}_{file_type}.{ext_map[file_type]}"
    return get_task_path(task_id, "frames", filename)


def get_task_final_video_path(task_id: str) -> str:
    """快捷获取任务最终输出的合并视频路径"""
    return get_task_path(task_id, "final.mp4")


# ========== Resource Management (Templates/BGM/Workflows) / 资源库级联管理 ==========

def get_resource_path(resource_type: Literal["bgm", "templates", "workflows"], *paths: str) -> str:
    """
    获取系统素材的真实物理路径（带有自定义重写支持的级联搜索）。
    
    搜索优先级:
        1. data/{resource_type}/*paths  (位于用户的数据挂载区，优先级更高)
        2. {resource_type}/*paths       (系统出厂自带的预置库)
    
    Args:
        resource_type: 资源大类 ("bgm", "templates", "workflows")
        *paths: 资源相对于大类的具体层级路径。
    
    Returns:
        str: 匹配成功的资源绝对路径。
    
    Raises:
        FileNotFoundError: 当两处目录均无法找到该资源时抛出。
    """
    # Build custom path (data/*)
    custom_path = get_data_path(resource_type, *paths)
    
    # Build default path (root/*)
    default_path = get_root_path(resource_type, *paths)
    
    # Priority: custom > default
    if os.path.exists(custom_path):
        return custom_path
    
    if os.path.exists(default_path):
        return default_path
    
    # Not found in either location
    raise FileNotFoundError(
        f"Resource not found: {os.path.join(resource_type, *paths)}\n"
        f"  Searched locations:\n"
        f"    1. {custom_path} (custom)\n"
        f"    2. {default_path} (default)"
    )


def list_resource_files(
    resource_type: Literal["bgm", "templates", "workflows"],
    subdir: str = ""
) -> list[str]:
    """
    合并列出某个资源类型目录下的所有文件。
    
    如果同名文件同时存在于默认库和用户挂载库，用户库 (data/) 的文件将覆盖系统默认的文件。
    
    Args:
        resource_type: 资源大类。
        subdir: 可选的具体子级目录。
    
    Returns:
        list[str]: 经去重并排序后的文件名列表。
    """
    files = {}  # Use dict to track source priority: {filename: path}
    
    # Build directory paths
    default_dir = Path(get_root_path(resource_type, subdir)) if subdir else Path(get_root_path(resource_type))
    custom_dir = Path(get_data_path(resource_type, subdir)) if subdir else Path(get_data_path(resource_type))
    
    # Scan default directory first (lower priority)
    if default_dir.exists() and default_dir.is_dir():
        for item in default_dir.iterdir():
            if item.is_file():
                files[item.name] = str(item)
    
    # Scan custom directory (higher priority, overwrites)
    if custom_dir.exists() and custom_dir.is_dir():
        for item in custom_dir.iterdir():
            if item.is_file():
                files[item.name] = str(item)  # Overwrite if exists
    
    return sorted(files.keys())


def list_resource_dirs(
    resource_type: Literal["bgm", "templates", "workflows"]
) -> list[str]:
    """
    合并列出某个资源类型目录下的所有子目录名（去重）。
    
    Returns:
        list[str]: 排序后的子文件夹名称集合。
    """
    dirs = set()
    
    # Build directory paths
    default_dir = Path(get_root_path(resource_type))
    custom_dir = Path(get_data_path(resource_type))
    
    # Scan default directory
    if default_dir.exists() and default_dir.is_dir():
        for item in default_dir.iterdir():
            if item.is_dir():
                dirs.add(item.name)
    
    # Scan custom directory
    if custom_dir.exists() and custom_dir.is_dir():
        for item in custom_dir.iterdir():
            if item.is_dir():
                dirs.add(item.name)
    
    return sorted(dirs)


def resource_exists(resource_type: Literal["bgm", "templates", "workflows"], *paths: str) -> bool:
    """
    判断目标资源文件是否存在（涵盖系统预置库和用户数据库）。
    
    Returns:
        bool: 存在返回 True。
    """
    custom_path = get_data_path(resource_type, *paths)
    default_path = get_root_path(resource_type, *paths)
    
    return os.path.exists(custom_path) or os.path.exists(default_path)