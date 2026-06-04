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
Session state management for web UI

Web UI 前端全局会话状态 (Session State) 管理模块。
负责控制和初始化用户的语言偏好，以及全局核心实例 `PixelleVideoCore` 的挂载与缓存。
"""

import streamlit as st
from loguru import logger

from web.i18n import get_language, set_language
from web.utils.async_helpers import run_async


def init_session_state():
    """
    初始化基本的 Streamlit 会话状态变量。
    主要用于在用户首次进入页面时设定默认的语言标识。
    """
    if "language" not in st.session_state:
        # 使用自动嗅探到的操作系统语言作为默认语言
        st.session_state.language = get_language()


def init_i18n():
    """
    初始化国际化 (i18n) 翻译系统环境。
    将用户的会话语言应用到后台的语言字典渲染引擎上。
    """
    if "language" not in st.session_state:
        st.session_state.language = get_language()
    
    # 强制刷新当前语言的翻译文本库
    set_language(st.session_state.language)


def get_pixelle_video():
    """
    获取全局唯一的 Pixelle-Video 核心服务实例。
    
    采用带缓存保护和智能热重载的单例提取机制。
    如果发现底层配置文件中影响核心连接的项（如 ComfyUI 的连接 URL 或 API 密钥）发生了更改，
    会主动触发并销毁旧的 websocket 会话，重新创建并挂载一个干净的核心引擎实例。
    
    Returns:
        PixelleVideoCore: 初始化完毕的核心业务引擎对象。
    """
    from pixelle_video.service import PixelleVideoCore
    from pixelle_video.config import config_manager
    
    # 计算当前关键配置的 Hash 值，用于比对判断是否需要热重载整个引擎
    import hashlib
    import json
    config_dict = config_manager.config.to_dict()
    # 仅仅追踪 ComfyUI 的环境配置。其他的设置 (如 LLM 等) 是运行时读取的，不需要破坏重启长连接实例
    comfyui_config = config_dict.get("comfyui", {})
    config_hash = hashlib.md5(json.dumps(comfyui_config, sort_keys=True).encode()).hexdigest()
    
    # 检测是否需要初次创建或因配置变更而重建
    need_recreate = False
    if 'pixelle_video' not in st.session_state:
        need_recreate = True
        logger.info("Creating new PixelleVideoCore instance (first time)")
    elif st.session_state.get('pixelle_video_config_hash') != config_hash:
        need_recreate = True
        logger.info("Configuration changed, recreating PixelleVideoCore instance")
        # 优雅地清理关闭前一个实例中持有的协程或连接资源
        old_core = st.session_state.pixelle_video
        try:
            run_async(old_core.cleanup())
        except Exception as e:
            logger.warning(f"Failed to cleanup old PixelleVideoCore: {e}")
    
    if need_recreate:
        # 创建新的核心实例并触发异步初始化方法
        pixelle_video = PixelleVideoCore()
        run_async(pixelle_video.initialize())
        
        # 将最新的实例与 Hash 锚点固化到会话中
        st.session_state.pixelle_video = pixelle_video
        st.session_state.pixelle_video_config_hash = config_hash
        logger.info("✅ PixelleVideoCore initialized and cached")
    else:
        # 正常直接复用已有的引擎，速度极快
        pixelle_video = st.session_state.pixelle_video
        logger.debug("Reusing cached PixelleVideoCore instance")
    
    return pixelle_video
