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
Pixelle-Video Configuration System

系统配置中心包的初始化文件。
统一向外部业务模块暴露验证过的数据结构类型和操作方法。

Usage:
    from pixelle_video.config import config_manager
    
    # 类型安全地读取最新配置
    api_key = config_manager.config.llm.api_key
    
    # 高级合并写入与落盘
    config_manager.update({"llm": {"api_key": "xxx"}})
    config_manager.save()
    
    # 配置可用性探针
    if config_manager.validate():
        print("Config is valid!")
"""
from .schema import PixelleVideoConfig, LLMConfig, ComfyUIConfig, TTSSubConfig, ImageSubConfig, VideoSubConfig
from .manager import ConfigManager
from .loader import load_config_dict, save_config_dict

# 导出并实例化全局唯一的配置管理器，供系统其余部分 Import 及调用
config_manager = ConfigManager()

__all__ = [
    # 模型定义
    "PixelleVideoConfig",
    "LLMConfig", 
    "ComfyUIConfig",
    "TTSSubConfig",
    "ImageSubConfig",
    "VideoSubConfig",
    
    # 管理器与全局单例对象
    "ConfigManager",
    "config_manager",
    
    # 原生底层函数暴露
    "load_config_dict",
    "save_config_dict",
]
