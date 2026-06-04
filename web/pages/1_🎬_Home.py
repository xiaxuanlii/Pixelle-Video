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
Home Page - Main video generation interface

首页 - 视频生成主控工作台。
"""

import sys
from pathlib import Path

# 将项目根目录添加到系统路径中
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

# 导入状态管理与国际化组件
from web.state.session import init_session_state, init_i18n, get_pixelle_video

# 导入 UI 组件模块
from web.components.header import render_header
from web.components.settings import render_advanced_settings
from web.components.faq import render_faq_sidebar

# 页面级配置
st.set_page_config(
    page_title="Home - Pixelle-Video",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    """主页面渲染入口"""
    # 1. 初始化会话状态存储和多语言系统 (i18n)
    init_session_state()
    init_i18n()
    
    # 2. 渲染顶导 (包含 Logo 标题和右侧语言切换器)
    render_header()
    
    # 3. 在左侧隐藏的边栏中渲染帮助文档与 FAQ
    render_faq_sidebar()
    
    # 4. 获取全局唯一初始化的 PixelleVideoCore 核心引擎对象
    pixelle_video = get_pixelle_video()
    
    # 5. 渲染系统底层的高级配置抽屉 (LLM 与 ComfyUI 授权配置等)
    render_advanced_settings()
    
    # ========================================================================
    # Pipeline Selection & Delegation / 流水线选项卡分发控制台
    # ========================================================================
    from web.pipelines import get_all_pipeline_uis
    
    # 从注册表中动态获取所有挂载的前端流水线交互界面
    pipelines = get_all_pipeline_uis()
    
    # 构建顶部的选项卡（Tabs）
    tab_labels = [f"{p.icon} {p.display_name}" for p in pipelines]
    tabs = st.tabs(tab_labels)
    
    # 遍历并在各自的选项卡内触发具体的 PipelineUI 进行渲染分发
    for i, pipeline in enumerate(pipelines):
        with tabs[i]:
            # 展示针对该流水线的简介说明
            if pipeline.description:
                st.caption(pipeline.description)
            
            # 将 Core 引擎句柄传递下去并请求组件自行渲染复杂的专属布局
            pipeline.render(pixelle_video)


if __name__ == "__main__":
    main()
