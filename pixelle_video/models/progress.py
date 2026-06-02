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
Progress event models for video generation

视频生成的结构化进度事件模型模块。
为 UI 渲染和交互层（或 WebSocket 推送）提供规范化、可解析的任务进度数据结构。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProgressEvent:
    """
    视频生成流水线的结构化进度事件对象。
    
    Attributes:
        event_type: 宏观事件类型标识 (例如: "generating_narrations", "frame_step", "concatenating")
        progress: 当前阶段的百分比进度 (0.0 到 1.0 之间)
        frame_current: (可选) 正在处理的当前分镜帧序号（从 1 开始计）
        frame_total: (可选) 剧本的总分镜数
        step: (可选) 针对处理单帧时的内部微小步序号 (如 1-4 表示音、图、排、视频合成)
        action: (可选) 当前子步骤的具体行为描述 (例如: "audio", "image", "compose", "video")
        extra_info: (可选) 追加传递的其他上下文文本信息（如批量提示词生成的剩余情况）
    
    Examples:
        # 简单事件：刚开始旁白生成
        ProgressEvent(event_type="generating_narrations", progress=0.05)
        
        # 复杂事件：正在为第 1 帧合成旁白录音
        ProgressEvent(
            event_type="frame_step",
            progress=0.23,
            frame_current=1,
            frame_total=5,
            step=1,
            action="audio"
        )
    """
    event_type: str
    progress: float
    
    # 可选的针对分镜维度的详情字段
    frame_current: Optional[int] = None
    frame_total: Optional[int] = None
    step: Optional[int] = None  # 1-4 for frame processing steps
    action: Optional[str] = None  # "audio", "image", "compose", "video"
    extra_info: Optional[str] = None  # 额外信息负载
    
    def __post_init__(self):
        """生命周期钩子：校验 progress 范围合法性"""
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError(f"Progress 必须介于 0.0 到 1.0 之间, 传入了 {self.progress}")
