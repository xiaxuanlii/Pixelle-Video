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
LLM Presets - Predefined configurations for popular LLM providers

用于向 Web UI 配置面板提供主流的大模型厂商接入参数自动填充方案。
只要服务商提供完全符合 OpenAI 官方规范标准接口的基地址，即可无缝接入本平台！
"""

from typing import Dict, Any, List


# 业界常用且高度兼容 OpenAI Protocol 的大模型供应商默认配置一键包
LLM_PRESETS: List[Dict[str, Any]] = [
    {
        "name": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
        "api_key_url": "https://bailian.console.aliyun.com/?tab=model#/api-key",
    },
    {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "api_key_url": "https://platform.openai.com/api-keys",
    },
    {
        "name": "Claude",
        "base_url": "https://api.anthropic.com/v1/",
        "model": "claude-sonnet-3-5",
        "api_key_url": "https://console.anthropic.com/settings/keys",
    },
    {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_url": "https://platform.deepseek.com/api_keys",
    },
    {
        "name": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "api_key_url": "https://ollama.com/download",
        "default_api_key": "ollama",  # 虽然被本地放行忽视，但是符合强类型约束以防空值错误
    },
    {
        "name": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "api_key_url": "https://platform.moonshot.cn/console/api-keys",
    },
]


def get_preset_names() -> List[str]:
    """返回预设模板厂商名称清单字典键集合"""
    return [preset["name"] for preset in LLM_PRESETS]


def get_preset(name: str) -> Dict[str, Any]:
    """根据大厂名称映射检索出具体的包含网址和模型型号的连接方案字典"""
    for preset in LLM_PRESETS:
        if preset["name"] == name:
            return preset
    return {}


def find_preset_by_base_url_and_model(base_url: str, model: str) -> str | None:
    """
    主要用于启动或重载读取后，向用户下拉框推测还原他现在用的是哪家的接口。
    
    Returns:
        如果完全吻合则返回对应的字符串标识 (如 'OpenAI' 或 'Qwen')。
    """
    for preset in LLM_PRESETS:
        if preset["base_url"] == base_url and preset["model"] == model:
            return preset["name"]
    return None
