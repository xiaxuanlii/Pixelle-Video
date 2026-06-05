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
ComfyUI Base Service - Common logic for ComfyUI-based services

ComfyUI 基底类 - 将所有调用到 ComfyUI 的通用逻辑模块封装沉淀。
提供给后续派生的如图像处理，画画等专职类直接集成扩展。
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from comfykit import ComfyKit
from loguru import logger

from pixelle_video.utils.os_util import (
    get_resource_path,
    list_resource_files,
    list_resource_dirs
)


class ComfyBaseService:
    """
    负责统一调度处理围绕工作流文件系统（workflow JSON）的各种解析基石操作的抽象类。
    
    子类应根据自身具体领域补充覆写如下变量:
    - WORKFLOW_PREFIX: 此服务的专属配置前置标记名 (例如: "image_", "tts_")
    - DEFAULT_WORKFLOW: 当前应用服务强制要求使用的默认首选预制配置文件。
    - WORKFLOWS_DIR: 解析入口，系统通常统一默认存放在 "workflows" 目录下。
    """
    
    WORKFLOW_PREFIX: str = ""  # Must be overridden by subclass
    DEFAULT_WORKFLOW: str = ""  # Must be overridden by subclass
    WORKFLOWS_DIR: str = "workflows"
    
    def __init__(self, config: dict, service_name: str, core=None):
        """
        将上方的全局配置大块分割切片绑定至具体的内部应用。
        
        Args:
            config: 原生的深层次树形全局字典配置。
            service_name: 本服务专属对应在 yaml 树中的分支节点名称（例如: "tts", "image"）。
            core: PixelleVideoCore 全局生命周期实例托管桥接（使各单独服务也能按需互相联动并直接利用到并发共享的 ComfyKit Web Socket 池链接）。
        """
        comfyui_config = config.get("comfyui", {})
        self.config = comfyui_config.get(service_name, {})
        self.global_config = comfyui_config
        self.service_name = service_name
        self._workflows_cache: Optional[List[str]] = None
        self.core = core
    
    def _scan_workflows(self) -> List[Dict[str, Any]]:
        """
        Scan workflows/source/*.json files from all source directories (merged from workflows/ and data/workflows/)
        基于约定的 WORKFLOW_PREFIX 从多层次结构中组合搜索符合当前业务领域的工作流清单库，并提取属性。

        Results are cached after first scan to avoid repeated filesystem I/O.
        合并自内置文件夹 `workflows/` 与挂载重写的用户专属夹 `data/workflows/`

        Returns:
            List[Dict[str, Any]]: 解析梳理后的对象级属性库大纲
        """
        if self._workflows_cache is not None:
            return self._workflows_cache

        workflows = []
        source_dirs = list_resource_dirs("workflows")
        
        if not source_dirs:
            logger.warning("No workflow source directories found")
            return workflows
        
        for source_name in source_dirs:
            workflow_files = list_resource_files("workflows", source_name)
            matching_files = [
                f for f in workflow_files 
                if f.startswith(self.WORKFLOW_PREFIX) and f.endswith('.json')
            ]
            
            for filename in matching_files:
                try:
                    file_path = Path(get_resource_path("workflows", source_name, filename))
                    workflow_info = self._parse_workflow_file(file_path, source_name)
                    workflows.append(workflow_info)
                    logger.debug(f"Found workflow: {workflow_info['key']}")
                except Exception as e:
                    logger.error(f"Failed to parse workflow {source_name}/{filename}: {e}")
        
        # Sort by key (source/name) and cache / 按键排序并缓存
        self._workflows_cache = sorted(workflows, key=lambda w: w["key"])
        return self._workflows_cache
    
    def _parse_workflow_file(self, file_path: Path, source: str) -> Dict[str, Any]:
        """
        进入物理本地内部深度阅读某个目标组件配置内容，将内置包裹的特别 API 请求目标如 "workflow_id" 等重要标记暴露输出到浅层结果上。
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        workflow_info = {
            "name": file_path.name,
            "display_name": f"{file_path.name} - {source.title()}",
            "source": source,
            "path": str(file_path),
            "key": f"{source}/{file_path.name}"
        }
        
        if "source" in content:
            if "workflow_id" in content:
                workflow_info["workflow_id"] = content["workflow_id"]
        
        return workflow_info
    
    def _get_default_workflow(self) -> str:
        """从配置提取针对自身工作业务领域必须的一定存在配置值的缺省调用模式。"""
        default_workflow = self.config.get("default_workflow")
        
        if not default_workflow:
            raise ValueError(
                f"No default workflow configured for {self.service_name}. "
                f"Please set 'default_workflow' in config.yaml under '{self.service_name}' section. "
                f"Available workflows: {', '.join(self.available)}"
            )
        
        return default_workflow
    
    def _resolve_workflow(self, workflow: Optional[str] = None) -> Dict[str, Any]:
        """
        负责翻译转化类似于 "runninghub/image_flux.json" 的路径为具体要推向 ComfyKit 执行包的真正内部组件参数的聚合类方法。
        
        Raises:
            ValueError: 给出的标记在任何系统中都查无音讯。
        """
        if workflow is None:
            workflow = self._get_default_workflow()
        
        available_workflows = self._scan_workflows()
        
        for wf_info in available_workflows:
            if wf_info["key"] == workflow:
                logger.info(f"🎬 Using {self.service_name} workflow: {workflow}")
                return wf_info
        
        available_keys = [wf["key"] for wf in available_workflows]
        available_str = ", ".join(available_keys) if available_keys else "none"
        raise ValueError(
            f"Workflow '{workflow}' not found. "
            f"Available workflows: {available_str}"
        )
    
    def _prepare_comfykit_config(
        self,
        comfyui_url: Optional[str] = None,
        runninghub_api_key: Optional[str] = None,
        runninghub_instance_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        动态将系统级别设定的常量和单次执行特需的独立强约束常量执行安全组合拼装。
        提供用于独立调起 ComfyKit 处理大引擎包专用的授权请求构建集。
        """
        kit_config = {}
        
        final_comfyui_url = (
            comfyui_url 
            or self.global_config.get("comfyui_url")
            or os.getenv("COMFYUI_BASE_URL")
            or "http://127.0.0.1:8188"
        )
        kit_config["comfyui_url"] = final_comfyui_url
        
        final_rh_key = (
            runninghub_api_key
            or self.global_config.get("runninghub_api_key")
            or os.getenv("RUNNINGHUB_API_KEY")
        )
        if final_rh_key:
            kit_config["runninghub_api_key"] = final_rh_key
        
        final_instance_type = (
            runninghub_instance_type
            or self.global_config.get("runninghub_instance_type")
            or os.getenv("RUNNINGHUB_INSTANCE_TYPE")
        )
        if final_instance_type and final_instance_type.strip():
            kit_config["runninghub_instance_type"] = final_instance_type
        
        logger.debug(f"ComfyKit config: {kit_config}")
        return kit_config
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """全量公开方法：将已探测出的本业务相关的可选用方案和扩展插件名称列表及参数包提供对外接口支持。"""
        return self._scan_workflows()
    
    @property
    def available(self) -> List[str]:
        """精简版可用大纲名称组合数组输出方法。"""
        workflows = self.list_workflows()
        return [wf["key"] for wf in workflows]
    
    def __repr__(self) -> str:
        default = self._get_default_workflow()
        available = ", ".join(self.available) if self.available else "none"
        return (
            f"<{self.__class__.__name__} "
            f"default={default!r} "
            f"available=[{available}]>"
        )
