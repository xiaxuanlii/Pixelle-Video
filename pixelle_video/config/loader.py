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
Configuration loader - Pure YAML

配置文件加载器模块 (纯 YAML 处理)。
负责从磁盘中读取和保存系统全局的 `config.yaml` 配置文件。
"""
from pathlib import Path
import yaml
from loguru import logger


def load_config_dict(config_path: str = "config.yaml") -> dict:
    """
    从指定的 YAML 文件中读取并加载为 Python 字典。
    
    如果文件不存在或加载失败，系统不会崩溃，而是会安全地回退到一个空字典，
    并在后续流程中依赖 Pydantic 的默认值。
    
    Args:
        config_path: 配置文件的相对或绝对路径。
        
    Returns:
        dict: 配置文件解析出的字典数据。
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_path}")
        logger.info("Using default configuration")
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        logger.info(f"Configuration loaded from {config_path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def save_config_dict(config: dict, config_path: str = "config.yaml"):
    """
    将 Python 字典数据安全地写入和保存为 YAML 文件。
    
    Args:
        config: 待保存的配置字典。
        config_path: 目标写入路径。
        
    Raises:
        Exception: 写入磁盘失败时向上抛出异常。
    """
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            # 开启 allow_unicode 以确保中文字符不被转义，sort_keys 保持用户原本的节点顺序
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise
