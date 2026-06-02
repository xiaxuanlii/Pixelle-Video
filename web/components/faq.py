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
FAQ component for displaying frequently asked questions

侧边栏帮助与支持组件 (FAQ)。
自动根据当前的国际化语言状态 (i18n) 加载不同的说明 Markdown 文件。
"""

import re
from pathlib import Path
from typing import Optional

import streamlit as st
from loguru import logger

from web.i18n import get_language, tr


def load_faq_content(language: str) -> Optional[str]:
    """
    根据给定的语言标识符载入对应的 Markdown 文件作为 FAQ 源内容。
    
    Args:
        language: 语种编码 (例如 "zh_CN", "en_US")。
    
    Returns:
        解析出的原始 Markdown 文本字符串。
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    
    if language.startswith("zh"):
        faq_file = project_root / "docs" / "FAQ_CN.md"
    else:
        faq_file = project_root / "docs" / "FAQ.md"
    
    try:
        if faq_file.exists():
            with open(faq_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"Loaded FAQ from: {faq_file}")
            return content
        else:
            logger.warning(f"FAQ file not found: {faq_file}")
            return None
    except Exception as e:
        logger.error(f"Failed to load FAQ file {faq_file}: {e}")
        return None


def parse_faq_sections(content: str) -> list[tuple[str, str]]:
    """
    基于 Markdown 大纲规范将 FAQ 文本拆解为问题与答案组 (Section)。
    
    依赖特征：每遇到一行以 `### ` (三级标题) 开始的内容，即认为开启了一个新的问答卡片。
    """
    # 丢弃头部的文档标题信息，直接寻找实质正文
    lines = content.split('\n')
    if lines and lines[0].startswith('#') and not lines[0].startswith('##'):
        content = '\n'.join(lines[1:])
    
    pattern = r'^###\s+(.+?)$'
    
    sections = []
    current_question = None
    current_answer_lines = []
    
    for line in content.split('\n'):
        match = re.match(pattern, line)
        if match:
            # 当匹配到下一个问题时，保存前一组缓冲好的提问与解答文本
            if current_question is not None:
                answer = '\n'.join(current_answer_lines).strip()
                sections.append((current_question, answer))
            
            # 开始读取捕捉新问题
            current_question = match.group(1).strip()
            current_answer_lines = []
        else:
            current_answer_lines.append(line)
    
    # 闭合补存最后一个读到的卡片组
    if current_question is not None:
        answer = '\n'.join(current_answer_lines).strip()
        sections.append((current_question, answer))
    
    return sections


def render_faq_sidebar():
    """
    渲染展开式的问答侧边栏组件库。
    """
    with st.sidebar:
        current_language = get_language()
        
        faq_content = load_faq_content(current_language)
        
        if faq_content:
            with st.expander(tr('faq.expand_to_view', fallback='FAQ'), expanded=True):
                sections = parse_faq_sections(faq_content)
                
                # 嵌套多级的可手风琴折叠展开块，每一个折叠卡内嵌单个问题
                for question, answer in sections:
                    with st.expander(question, expanded=False):
                        st.markdown(answer, unsafe_allow_html=True)
            
            st.markdown(
                f"💡 {tr('faq.more_help', fallback='Need more help?')} "
                f"[GitHub Issues](https://github.com/AIDC-AI/Pixelle-Video/issues)"
            )
        else:
            # 文件缺失时的保底回退静态呈现
            st.markdown(f"### 💡 {tr('faq.more_help', fallback='Need help?')}")
            st.markdown(
                f"[GitHub Issues](https://github.com/AIDC-AI/Pixelle-Video/issues) | "
                f"[Documentation](https://aidc-ai.github.io/Pixelle-Video)"
            )
