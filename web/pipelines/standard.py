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
Standard Pipeline UI

经典标准流水线（Quick Create 模式）的交互界面组装层。
"""

import streamlit as st
from typing import Any
from web.i18n import tr

from web.pipelines.base import PipelineUI, register_pipeline_ui

# 导入复用的原子级公共表单区块
from web.components.content_input import render_content_input, render_bgm_section, render_version_info
from web.components.style_config import render_style_config
from web.components.output_preview import render_output_preview


class StandardPipelineUI(PipelineUI):
    """
    负责将标准图文转视频流水线拆分为逻辑清晰经典 3 列布局前端组件。
    包含入参采集列、高级选项配置列与进度重播监控区。
    """
    name = "quick_create"
    icon = "⚡"
    
    @property
    def display_name(self):
        return tr("pipeline.quick_create.name")
    
    @property
    def description(self):
        return tr("pipeline.quick_create.description")
    
    def render(self, pixelle_video: Any):
        # 强制利用 1:1:1 比例对齐切出三列结构
        left_col, middle_col, right_col = st.columns([1, 1, 1])
        
        # ====================================================================
        # Left Column: Content Input & BGM / 左列 - 核心正文录入与音轨
        # ====================================================================
        with left_col:
            # 返回用户填写的故事结构文本、模式等
            content_params = render_content_input()
            
            # 返回挑选配乐及其音量信息
            bgm_params = render_bgm_section()
            
            # 页脚放置版本和文档指引
            render_version_info()
        
        # ====================================================================
        # Middle Column: Style Configuration / 中列 - 风格配置（音色、模版排版和引擎）
        # ====================================================================
        with middle_col:
            style_params = render_style_config(pixelle_video)
        
        # ====================================================================
        # Right Column: Output Preview / 右列 - 控制启动按钮与大纲结果重放区
        # ====================================================================
        with right_col:
            # 汇集打包前面所有的配置为一整块负载传给大后方
            video_params = {
                "pipeline": self.name,
                **content_params,
                **bgm_params,
                **style_params
            }
            
            # 在此处渲染复杂的实时状态反馈轮询和生成成果大屏
            render_output_preview(pixelle_video, video_params)


# 主动注册告知系统装配表自己就绪
register_pipeline_ui(StandardPipelineUI)
