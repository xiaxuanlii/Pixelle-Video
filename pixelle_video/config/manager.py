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
Configuration Manager - Singleton pattern

配置管理中心模块。
运用“单例模式”确保全系统在生命周期中共享同一份配置数据对象。
包含读取、内存热重载（hot reload）、深度合并（Deep Merge）并回写落盘的功能。
"""
from pathlib import Path
from typing import Any, Optional
from loguru import logger
from .schema import PixelleVideoConfig
from .loader import load_config_dict, save_config_dict


class ConfigManager:
    """
    全局配置管理器 (单例)。
    
    为各个组件（特别是后台的原子服务如 llm, tts, media）提供读取和修改配置的安全途径。
    该类实现了深合并特性，避免在仅修改一部分配置（例如仅修改 api_key）时，冲掉其他子配置的内容。
    """
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config.yaml"):
        # 保护逻辑，防止每次被 import 并重新实例化时重复读取磁盘
        if hasattr(self, '_initialized'):
            return
        
        self.config_path = Path(config_path)
        self.config: PixelleVideoConfig = self._load()
        self._initialized = True
    
    def _load(self) -> PixelleVideoConfig:
        """从磁盘装载 YAML 并实例化为严格的 Pydantic 模型对象"""
        data = load_config_dict(str(self.config_path))
        config = PixelleVideoConfig(**data)
        
        # 启动时执行一次对默认系统 HTML 模板的检测探针
        self._validate_template(config.template.default_template)
        
        return config
    
    def _validate_template(self, template_path: str):
        """探测默认的视频 HTML 排版模板文件是否处于可用就绪状态"""
        from pixelle_video.utils.template_util import resolve_template_path
        
        try:
            # 尝试调用解析方法查询路径
            resolved_path = resolve_template_path(template_path)
            logger.debug(f"Template validation passed: {template_path} -> {resolved_path}")
        except FileNotFoundError as e:
            # 即使不存在也不会报错退出，只是给予控制台警告并让它降级回退
            logger.warning(
                f"Configured default template '{template_path}' not found. "
                f"Will fall back to '1080x1920/default.html' if needed. Error: {e}"
            )
    
    def reload(self):
        """在不重启应用的情况下，要求服务重新从磁盘同步并应用最新的 `config.yaml`"""
        self.config = self._load()
        logger.info("Configuration reloaded")
    
    def save(self):
        """将当前内存中经过任何修改的配置树对象立刻保存落盘。"""
        save_config_dict(self.config.to_dict(), str(self.config_path))
    
    def update(self, updates: dict):
        """
        以增量（Patch）的方式递归深合并更新系统配置。
        
        Args:
            updates: 包含局部更新的数据字典。
                     例如仅提供 {"llm": {"api_key": "xxx"}}，
                     那么 llm 节点下的其他配置（如 base_url）及其他大节点均不会被擦除。
        """
        current = self.config.to_dict()
        
        # 内部递归合并函数
        def deep_merge(base: dict, updates: dict) -> dict:
            for key, value in updates.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        merged = deep_merge(current, updates)
        # 用最新合成好的字典重新灌入 Pydantic 进行一次类型安全校验
        self.config = PixelleVideoConfig(**merged)
    
    def get(self, key: str, default: Any = None) -> Any:
        """快捷提取方法，提供类似字典原生的 get 获取方式，方便跨老代码的兼容。"""
        return self.config.to_dict().get(key, default)
    
    def validate(self) -> bool:
        """触发模型内聚的安全预检逻辑（检查如 LLM 配置是否合规）"""
        return self.config.validate_required()
    
    def get_llm_config(self) -> dict:
        """从对象树中解包出 LLM 相关配置并组合为字典输出"""
        return {
            "api_key": self.config.llm.api_key,
            "base_url": self.config.llm.base_url,
            "model": self.config.llm.model,
        }
    
    def set_llm_config(self, api_key: str, base_url: str, model: str):
        """封装供外部 API 或配置界面使用的修改并立即刷新 LLM 节点的方法"""
        from pixelle_video.utils.llm_util import normalize_openai_base_url

        self.update({
            "llm": {
                "api_key": api_key,
                "base_url": normalize_openai_base_url(base_url),
                "model": model,
            }
        })
    
    def get_comfyui_config(self) -> dict:
        """从对象树解包出 ComfyUI 全局与分支的全部详细配置选项供面板展示"""
        return {
            "comfyui_url": self.config.comfyui.comfyui_url,
            "comfyui_api_key": self.config.comfyui.comfyui_api_key,
            "runninghub_api_key": self.config.comfyui.runninghub_api_key,
            "runninghub_concurrent_limit": self.config.comfyui.runninghub_concurrent_limit,
            "runninghub_instance_type": self.config.comfyui.runninghub_instance_type,
            "tts": {
                "default_workflow": self.config.comfyui.tts.default_workflow,
            },
            "image": {
                "default_workflow": self.config.comfyui.image.default_workflow,
                "prompt_prefix": self.config.comfyui.image.prompt_prefix,
            },
            "video": {
                "default_workflow": self.config.comfyui.video.default_workflow,
                "prompt_prefix": self.config.comfyui.video.prompt_prefix,
            }
        }

    def get_api_providers_config(self) -> dict:
        """Get direct API provider configuration as dict"""
        return self.config.api_providers.model_dump()

    def set_api_provider_config(self, provider: str, updates: dict):
        """Set configuration for a direct API provider"""
        self.update({"api_providers": {provider: updates}})
    
    def set_comfyui_config(
        self, 
        comfyui_url: Optional[str] = None,
        comfyui_api_key: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        runninghub_concurrent_limit: Optional[int] = None,
        runninghub_instance_type: Optional[str] = None
    ):
        """安全修改核心底层媒体生成引擎连接参数的服务"""
        updates = {}
        if comfyui_url is not None:
            updates["comfyui_url"] = comfyui_url
        if comfyui_api_key is not None:
            updates["comfyui_api_key"] = comfyui_api_key
        if runninghub_api_key is not None:
            updates["runninghub_api_key"] = runninghub_api_key
        if runninghub_concurrent_limit is not None:
            updates["runninghub_concurrent_limit"] = runninghub_concurrent_limit
        if runninghub_instance_type is not None:
            # Empty string means disable (treat as None for storage)
            # 如果传了空字符串则认定用户意图为清除/禁用该高级云算力型号的指定
            updates["runninghub_instance_type"] = runninghub_instance_type if runninghub_instance_type else None
        
        if updates:
            self.update({"comfyui": updates})
