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
Streamlit helper functions

针对 Streamlit 框架页面级别的辅助黑魔法函数库。
提供诸如版本兼容的页面强制刷新、无视弹窗限制的原生浏览器 JS 警告等底层交互。
"""

import streamlit as st
import streamlit.components.v1 as components

from web.i18n import tr
from pixelle_video.config import config_manager


def safe_rerun():
    """
    提供跨越旧版与新版 Streamlit 版本 API 兼容性的强制页面重渲染指令。
    不论新老版本，只需调用此函数即可打断执行立刻刷新视图。
    """
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()


# ============================================================================
# SelfHost Workflow Warning - Using Native JavaScript Alert
# 本地私有化工作流安全警告 - 使用浏览器原生 JavaScript 拦截弹窗
# ============================================================================
# 由于 Streamlit 自带的 st.dialog 具有许多状态管理和渲染位置等硬伤和局限，
# 我们通过在渲染树末端直接下发并执行 `alert()` 脚本片段，提供绝对可靠的弹层。

def check_and_warn_selfhost_workflow(workflow_path: str):
    """
    侦测并警告：如果用户从下拉框将云端的引擎切换成了需要苛刻本地算力要求的私有化工作流，
    则立刻触发强阻断的安全告知弹窗。
    
    Args:
        workflow_path: 即将切换到的工作流标识 (例如 "selfhost/image_flux.json")
    """
    if not workflow_path:
        return
    
    # 嗅探是否正在尝试访问以 selfhost 开头的目录特征
    is_selfhost = workflow_path.startswith("selfhost/")
    
    # 只有处于这个特定动作时再将 js 发射到前台执行
    if is_selfhost:
        _show_js_alert(workflow_path)


def _show_js_alert(workflow_path: str):
    """
    构建具体的告警文本并通过 `components.html` 隧道将包含 JS 的不可见标签渲染到浏览器中触发弹窗。
    """
    comfyui_config = config_manager.get_comfyui_config()
    comfyui_url = comfyui_config.get("comfyui_url", "http://localhost:8188")
    
    # 构建国际化的系统提醒词
    title = tr("selfhost.warning.title")
    message = tr("selfhost.warning.message", 
                 comfyui_url=comfyui_url, 
                 workflow_path=f"workflows/{workflow_path}")
    hint = tr("selfhost.warning.hint")
    
    # 清理掉 Markdown 的富文本标记符号以匹配普通文本 Alert 的要求
    message = message.replace("**", "").replace("*", "")
    hint = hint.replace("**", "").replace("*", "")
    
    # 连接成一整段包含内部格式段落的文字块
    full_message = f"{title}\\n\\n{message}\\n\\n{hint}"
    
    # 对有可能产生 JS 代码逃逸或引发未封闭错误的字符进行严格的后端转义
    full_message = full_message.replace("'", "\\'").replace('"', '\\"')
    full_message = full_message.replace("\n", "\\n")
    
    js_code = f"""
    <script>
        alert("{full_message}");
    </script>
    """
    
    # 输出宽与高皆为 0 的纯代码容器使其在 DOM 中不占流式空间
    components.html(js_code, height=0, width=0)
