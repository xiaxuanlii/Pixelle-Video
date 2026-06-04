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
Pixelle-Video Web UI - Main Entry Point

Pixelle-Video Web 前端 - 主程序入口。
这是 Streamlit 多页面应用程序的引导文件。
使用 `st.navigation` 定义了左侧边栏页面，并将首页设置为默认入口。
"""

import sys
from pathlib import Path

# 将项目根目录添加到系统路径中，以便 Streamlit 能正确导入本地模块
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

# 全局页面配置（注意：这必须是任何 Streamlit 应用的第一条执行命令）
st.set_page_config(
    page_title="Pixelle-Video - AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",  # 默认收起左侧边栏以留出最大工作区
)


def main():
    """主程序入口与导航路由设置"""
    # 使用 st.Page 定义各个子页面
    home_page = st.Page(
        "pages/1_🎬_Home.py",
        title="Home",
        icon="🎬",
        default=True
    )
    
    history_page = st.Page(
        "pages/2_📚_History.py",
        title="History",
        icon="📚"
    )
    
    # 建立导航并挂载运行
    pg = st.navigation([home_page, history_page])
    pg.run()


if __name__ == "__main__":
    main()
