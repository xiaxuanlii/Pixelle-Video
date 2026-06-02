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
Workflow Path Resolver

工作流解析与定位辅助模块。
为各种需要调用底层的系统工作流（例如图像分析、视频生成、TTS 转换等）
制定标准化的文件查找命名规约和后备机制。

规约格式为: {source}/{service}.json
例如:
    - 图像反推提示词: selfhost/analyse_image.json 或 runninghub/analyse_image.json
    - AI 生图: runninghub/image.json
"""

from typing import Literal

WorkflowSource = Literal['runninghub', 'selfhost']


def resolve_workflow_path(
    service_name: str,
    source: WorkflowSource = 'runninghub'
) -> str:
    """
    根据服务名和来源动态组装出工作流文件的相对路径。
    
    Args:
        service_name: 底层服务名称关键字 (如 "analyse_image", "video")。
        source: 工作流托管模式：'runninghub'（云端）或 'selfhost'（私有化本地部署）。
    
    Returns:
        str: 拼接好的路径标识字符串 "{source}/{service_name}.json"
    """
    return f"{source}/{service_name}.json"


def get_default_source() -> WorkflowSource:
    """
    获取全局默认的工作流服务提供商策略。
    
    Returns:
        Literal: 当前框架倾向于使用 'runninghub' 作为默认值以降低初学者的部署门槛。
    """
    return 'runninghub'