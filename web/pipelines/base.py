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
Pipeline UI Base & Registry

流水线前端交互界面的基类与系统注册表。
利用面向对象的形式提供了一个标准化扩展接口，方便插拔新的流水线专属界面（如“文字生视频”，“图片生视频”，“短剧系统”等）。
"""

from typing import Dict, Any, List, Type

class PipelineUI:
    """
    负责在网页中描述某个流水线独有表单属性和渲染逻辑的抽象基类插件。
    
    每一个新的流水线场景如果需要被前台用户触碰和发起交互，就必须派生此子类。
    并在其内部完成 `st.text_input()`, `st.button()` 等专属界面的勾勒工作。
    """
    name: str = "base"                          # 与后端的系统级 pipeline_name 强制对应
    display_name: str = "Base Pipeline"         # 选项卡上的简短展示名称
    icon: str = "🔌"                            # 选项卡的表情符号
    description: str = ""                       # 点进选项卡后首行说明的帮助文案
    
    def render(self, pixelle_video: Any):
        """
        该前端组件核心的页面组件绘制与表单状态维护代码。
        
        Args:
            pixelle_video: The initialized PixelleVideoCore instance. (底层能力调用网关)
        """
        raise NotImplementedError


# ==================== Registry (组件注册装配表) ====================

_pipeline_uis: Dict[str, PipelineUI] = {}

def register_pipeline_ui(ui_class: Type[PipelineUI]):
    """提供给所有子组件扫描挂载的入口，将组件暴露到大盘供 App 读取。"""
    instance = ui_class()
    _pipeline_uis[instance.name] = instance

def get_pipeline_ui(name: str) -> PipelineUI:
    """按标识取出已装配的唯一组件单例"""
    return _pipeline_uis.get(name)

def get_all_pipeline_uis() -> List[PipelineUI]:
    """批量交付所有的流水线视图供 Tab 组渲染"""
    return list(_pipeline_uis.values())
