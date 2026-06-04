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
Web UI pipelines package

Web UI 流水线视图层集合包。
注册所有受支持的视频生成交互入口。
"""

from web.pipelines.base import PipelineUI, get_pipeline_ui, get_all_pipeline_uis
from web.pipelines.standard import StandardPipelineUI

__all__ = [
    "PipelineUI",
    "get_pipeline_ui",
    "get_all_pipeline_uis",
    "StandardPipelineUI"
]
