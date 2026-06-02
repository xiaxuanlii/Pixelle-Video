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
Header components for web UI

Web UI 页面通用顶部导航头。
负责展示系统 Logo，并集成一个允许热切换多语言配置 (i18n) 的下拉选择器。
"""

import streamlit as st

from web.i18n import tr, get_available_languages, set_language
from web.utils.streamlit_helpers import safe_rerun


def render_header():
    """利用两列比例布局呈现顶导大字目标题与语言框"""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<h3>{tr('app.title')}</h3>", unsafe_allow_html=True)
    with col2:
        render_language_selector()


def render_language_selector():
    """获取并在右上角动态渲染语言列表清单与选择响应逻辑"""
    languages = get_available_languages()
    lang_options = [f"{code} - {name}" for code, name in languages.items()]
    
    current_lang = st.session_state.get("language", "zh_CN")
    current_index = list(languages.keys()).index(current_lang) if current_lang in languages else 0
    
    selected = st.selectbox(
        tr("language.select"),
        options=lang_options,
        index=current_index,
        label_visibility="collapsed"
    )
    
    selected_code = selected.split(" - ")[0]
    if selected_code != current_lang:
        st.session_state.language = selected_code
        set_language(selected_code)
        safe_rerun()  # 触发重新渲染使新的多语言包立地生效应用
