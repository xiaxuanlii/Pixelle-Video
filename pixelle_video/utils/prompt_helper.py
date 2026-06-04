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
Prompt helper utilities

提示词构建辅助工具。
用于在将用户/AI 生成的基础提示词发送给画图引擎之前，进行格式化和前缀修饰。
"""


def build_image_prompt(prompt: str, prefix: str = "") -> str:
    """
    将基础提示词与全局风格前缀安全拼接。
    
    Args:
        prompt: 用户或 AI 生成的原始图像描述提示词。
        prefix: (可选) 需要加在最前面的风格修饰词 (如 "anime style", "masterpiece")。
    
    Returns:
        str: 拼接好的最终提示词。
    
    Examples:
        >>> build_image_prompt("a cat", "")
        'a cat'
        
        >>> build_image_prompt("a cat", "anime style")
        'anime style, a cat'
        
        >>> build_image_prompt("a cat", "  anime style  ")
        'anime style, a cat'
    """
    prefix = prefix.strip() if prefix else ""
    prompt = prompt.strip() if prompt else ""
    
    if prefix and prompt:
        return f"{prefix}, {prompt}"
    elif prefix:
        return prefix
    else:
        return prompt
