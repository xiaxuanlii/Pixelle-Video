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
Async helper functions for web UI

Web 前端异步辅助工具。
因为 Streamlit 本身是同步阻塞执行的框架，但在底层我们采用了高性能的 asyncio 异步开发，
所以在界面侧需要提供一些桥接辅助方法以在同步流程中安全运行异步函数。
"""

import asyncio
import sys
import tomllib
from pathlib import Path

from loguru import logger


def run_async(coro):
    """
    Run async coroutine in sync context.
    在同步上下文中阻塞运行一个异步协程直到返回结果。

    主要用于在 Streamlit 的按钮点击回调或页面加载流中调用后端异步引擎的方法。

    Args:
        coro: 等待执行的异步协程对象。

    Returns:
        异步函数的返回结果。
    """
    if sys.platform == "win32":
        # Streamlit/Tornado may switch the global asyncio policy to
        # WindowsSelectorEventLoopPolicy, which breaks subprocess-based
        # libraries such as Playwright on Windows. Use an explicit
        # Proactor loop here so this sync bridge does not depend on the
        # ambient global policy.
        loop = asyncio.ProactorEventLoop()
        try:
            return loop.run_until_complete(coro)
        finally:
            try:
                from pixelle_video.services.frame_html import HTMLFrameGenerator

                loop.run_until_complete(HTMLFrameGenerator.close_browser())
            except Exception as e:
                logger.debug(f"Failed to cleanup HTML frame browser before loop close: {e}")
            loop.close()
    return asyncio.run(coro)


def get_project_version() -> str:
    """
    动态解析项目的 `pyproject.toml` 读取当前最新的软件版本号。
    
    Returns:
        str: 诸如 "0.1.0" 的版本字符串，读取失败时返回 "Unknown"。
    """
    try:
        # 解析项目根目录路径
        web_dir = Path(__file__).resolve().parent.parent
        project_root = web_dir.parent
        pyproject_path = project_root / "pyproject.toml"
        
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
                return pyproject_data.get("project", {}).get("version", "Unknown")
    except Exception as e:
        logger.warning(f"Failed to read version from pyproject.toml: {e}")
    return "Unknown"
