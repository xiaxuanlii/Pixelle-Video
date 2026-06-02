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
Content input components for web UI (left column)

Web UI 左列组件：内容录入区模块。
负责渲染模式选择、主题录入、BGM 选择和一些基础视频设定的表单。
"""

import streamlit as st

from web.i18n import tr
from web.utils.async_helpers import get_project_version


def render_content_input():
    """
    渲染左侧内容录入表单。
    包含单任务模式和批处理模式两种交互视图。
    """
    with st.container(border=True):
        st.markdown(f"**{tr('section.content_input')}**")
        
        # ====================================================================
        # Step 1: Batch mode toggle (highest priority)
        # ====================================================================
        batch_mode = st.checkbox(
            tr("batch.mode_label"),
            value=False,
            help=tr("batch.mode_help")
        )
        
        if not batch_mode:
            # ================================================================
            # Single task mode (original logic, unchanged)
            # 单一任务生成模式
            # ================================================================
            # 处理模式选择 (AI发散模式 or 固定台词模式)
            mode = st.radio(
                "Processing Mode",
                ["generate", "fixed"],
                horizontal=True,
                format_func=lambda x: tr(f"mode.{x}"),
                label_visibility="collapsed"
            )
            
            # 根据模式自适应渲染提示文本和高度
            text_placeholder = tr("input.topic_placeholder") if mode == "generate" else tr("input.content_placeholder")
            text_height = 120 if mode == "generate" else 200
            text_help = tr("input.text_help_generate") if mode == "generate" else tr("input.text_help_fixed")
            
            text = st.text_area(
                tr("input.text"),
                placeholder=text_placeholder,
                height=text_height,
                help=text_help
            )
            
            # 分镜拆分策略选择 (仅在 fixed 固定模式下可见)
            if mode == "fixed":
                split_mode_options = {
                    "paragraph": tr("split.mode_paragraph"),
                    "line": tr("split.mode_line"),
                    "sentence": tr("split.mode_sentence"),
                }
                split_mode = st.selectbox(
                    tr("split.mode_label"),
                    options=list(split_mode_options.keys()),
                    format_func=lambda x: split_mode_options[x],
                    index=0,  # 默认使用段落分割
                    help=tr("split.mode_help")
                )
            else:
                split_mode = "paragraph"  # generate 模式下用不到此参数
            
            # 视频标题 (可选)
            title = st.text_input(
                tr("input.title"),
                placeholder=tr("input.title_placeholder"),
                help=tr("input.title_help")
            )
            
            # 目标分镜数量设定 (仅在 generate 发散模式下有意义)
            if mode == "generate":
                n_scenes = st.slider(
                    tr("video.frames"),
                    min_value=3,
                    max_value=30,
                    value=5,
                    help=tr("video.frames_help"),
                    label_visibility="collapsed"
                )
                st.caption(tr("video.frames_label", n=n_scenes))
            else:
                # 固定模式下，分镜数由传入文本长度和切割策略决定
                n_scenes = 5
                st.info(tr("video.frames_fixed_mode_hint"))
            
            return {
                "batch_mode": False,
                "mode": mode,
                "text": text,
                "title": title,
                "n_scenes": n_scenes,
                "split_mode": split_mode
            }
        
        else:
            # ================================================================
            # Batch mode (simplified YAGNI version)
            # 批量多任务矩阵生成模式
            # ================================================================
            st.markdown(f"**{tr('batch.section_title')}**")
            
            # 批量任务输入规则提示
            st.info(f"""
**{tr('batch.rules_title')}**
- ✅ {tr('batch.rule_1')}
- ✅ {tr('batch.rule_2')}
- ✅ {tr('batch.rule_3')}
            """)
            
            # 主题录入大文本框
            text_input = st.text_area(
                tr("batch.topics_label"),
                height=300,
                placeholder=tr("batch.topics_placeholder"),
                help=tr("batch.topics_help")
            )
            
            # 尝试通过换行符切分各个独立任务
            if text_input:
                topics = [
                    line.strip() 
                    for line in text_input.strip().split('\n') 
                    if line.strip()
                ]
                
                if topics:
                    # 保护限制，单次最多 100 个批量任务
                    if len(topics) > 100:
                        st.error(tr("batch.count_error", count=len(topics)))
                        topics = []
                    else:
                        st.success(tr("batch.count_success", count=len(topics)))
                        
                        # 展示识别出多少个主题队列
                        with st.expander(tr("batch.preview_title"), expanded=False):
                            for i, topic in enumerate(topics, 1):
                                st.markdown(f"`{i}.` {topic}")
                else:
                    topics = []
            else:
                topics = []
            
            st.markdown("---")
            
            # 批量统一使用的视频标题前缀
            title_prefix = st.text_input(
                tr("batch.title_prefix_label"),
                placeholder=tr("batch.title_prefix_placeholder"),
                help=tr("batch.title_prefix_help")
            )
            
            # 所有批量任务共享的分镜长度参数
            n_scenes = st.slider(
                tr("batch.n_scenes_label"),
                min_value=3,
                max_value=30,
                value=5,
                help=tr("batch.n_scenes_help")
            )
            st.caption(tr("batch.n_scenes_caption", n=n_scenes))
            
            st.info(f"📌 {tr('batch.config_info')}")
            
            return {
                "batch_mode": True,
                "topics": topics,
                "mode": "generate",  # 批量时强制设为发散模式
                "title_prefix": title_prefix,
                "n_scenes": n_scenes,
            }


def render_bgm_section(key_prefix=""):
    """
    渲染全局 BGM (背景音乐) 选项组件。
    自动探测系统中的 `bgm` 与挂载目录中的音频文件。
    """
    with st.container(border=True):
        st.markdown(f"**{tr('section.bgm')}**")
        
        with st.expander(tr("help.feature_description"), expanded=False):
            st.markdown(f"**{tr('help.what')}**")
            st.markdown(tr("bgm.what"))
            st.markdown(f"**{tr('help.how')}**")
            st.markdown(tr("bgm.how"))
        
        # 动态扫描两个潜在路径下的音乐素材
        from pixelle_video.utils.os_util import list_resource_files
        
        try:
            all_files = list_resource_files("bgm")
            audio_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg')
            bgm_files = sorted([f for f in all_files if f.lower().endswith(audio_extensions)])
        except Exception as e:
            st.warning(f"Failed to load BGM files: {e}")
            bgm_files = []
        
        bgm_options = [tr("bgm.none")] + bgm_files
        
        # 默认高亮选择名为 default 的内置音乐
        default_index = 0
        if "default.mp3" in bgm_files:
            default_index = bgm_options.index("default.mp3")
        
        bgm_choice = st.selectbox(
            "BGM",
            bgm_options,
            index=default_index,
            label_visibility="collapsed",
            key=f"{key_prefix}bgm_selector"
        )
        
        # 仅当挑选了具体音乐后，才弹出音量滑块调节栏
        if bgm_choice != tr("bgm.none"):
            bgm_volume = st.slider(
                tr("bgm.volume"),
                min_value=0.0,
                max_value=0.5,
                value=0.2,
                step=0.01,
                format="%.2f",
                key=f"{key_prefix}bgm_volume_slider",
                help=tr("bgm.volume_help")
            )
        else:
            bgm_volume = 0.2
        
        # 仅当挑选了具体音乐后，才渲染网页端内的快速试听按钮组件
        if bgm_choice != tr("bgm.none"):
            if st.button(tr("bgm.preview"), key=f"{key_prefix}preview_bgm", width="stretch"):
                from pixelle_video.utils.os_util import get_resource_path, resource_exists
                try:
                    if resource_exists("bgm", bgm_choice):
                        bgm_file_path = get_resource_path("bgm", bgm_choice)
                        st.audio(bgm_file_path)
                    else:
                        st.error(tr("bgm.preview_failed", file=bgm_choice))
                except Exception as e:
                    st.error(f"{tr('bgm.preview_failed', file=bgm_choice)}: {e}")
        
        bgm_path = None if bgm_choice == tr("bgm.none") else bgm_choice
    
    return {
        "bgm_path": bgm_path,
        "bgm_volume": bgm_volume
    }


def render_version_info():
    """在底侧栏显示本系统的版本号标识与给 Star 的超链接"""
    with st.container(border=True):
        st.markdown(f"**{tr('version.title')}**")
        version = get_project_version()
        github_url = "https://github.com/AIDC-AI/Pixelle-Video"
        badge_url = "https://img.shields.io/github/stars/AIDC-AI/Pixelle-Video"

        st.markdown(
            f'{tr("version.current")}: `{version}` &nbsp;&nbsp; '
            f'<a href="{github_url}" target="_blank">'
            f'<img src="{badge_url}" alt="GitHub stars" style="vertical-align: middle;">'
            f'</a>',
            unsafe_allow_html=True)
