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
Storyboard data models for video generation

视频生成的分镜剧本数据模型模块。
记录了从全局配置、元数据到每一个独立分镜的图、文、音数据的整个核心数据链路。
是贯穿整个生成 Pipeline 乃至持久化落盘的核心对象。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class StoryboardConfig:
    """Storyboard 分镜剧本的全局生成策略配置项"""
    
    # Required parameters / 核心必填尺寸配置（根据模板分析得来）
    media_width: int                           # 内嵌媒体区域预期宽度 (像素)
    media_height: int                          # 内嵌媒体区域预期高度 (像素)
    
    # Task isolation / 任务隔离信息
    task_id: Optional[str] = None              # 用于独立持久化隔离文件的全局 Task ID
    
    # 控制大模型生成的各项阈值
    n_storyboard: int = 5                      # 期望分镜总数
    min_narration_words: int = 5               # 旁白最小字数
    max_narration_words: int = 20              # 旁白最大字数
    min_image_prompt_words: int = 30           # 绘图提示词最小长度
    max_image_prompt_words: int = 60           # 绘图提示词最大长度
    
    # Video parameters / 视频流媒体编码属性
    video_fps: int = 30                        # 帧率 (尺寸实际由 frame_template 约束)
    
    # Audio parameters / TTS 语音设置
    tts_inference_mode: str = "local"          # TTS 推理模式: "local" 或 "comfyui"
    voice_id: Optional[str] = None             # 音色 ID（边缘TTS音色名，或是 ComfyUI 工作流所需节点值）
    tts_workflow: Optional[str] = None         # 针对云端的高级 TTS 配置文件
    tts_speed: Optional[float] = None          # 语速调节倍率 (1.0 为正常)
    ref_audio: Optional[str] = None            # 声音克隆功能所需的参考录音
    
    # Media workflow / 底层 AI 绘画/生视频的引擎配置
    media_workflow: Optional[str] = None       # Media workflow filename (image or video, None = use default)
    api_video_params: Optional[Dict[str, Any]] = None  # Extra direct API video generation parameters
    
    # Frame template / HTML 排版画框模板
    frame_template: str = "1080x1920/image_default.html"  # 模板路径 (必须带尺寸前缀以便正确解析缩放)
    template_params: Optional[Dict[str, Any]] = None  # 提供给模板解析替换的动态扩展变量字典 (如改背景色)


@dataclass
class StoryboardFrame:
    """单一分镜画面的基础单元模型"""
    index: int                                 # 分镜的绝对序列号 (从 0 计)
    narration: str                             # 文本旁白/台词
    image_prompt: str                          # 翻译推断出的绘画提示词 (如果是纯文本模板或固定资产则为空)
    
    # Generated resource paths / 执行流程中不断被填充的物理文件足迹
    audio_path: Optional[str] = None           # 旁白录音存放路径
    media_type: Optional[str] = None           # 这帧使用的核心媒体属性: "image" 或 "video"
    image_path: Optional[str] = None           # 原始生成背景图片的路径
    video_path: Optional[str] = None           # 原始生成视频流的路径（尚未处理或混合声音前）
    composed_image_path: Optional[str] = None  # 经过 HTML 无头渲染挂载排版样式的成品静态长图
    video_segment_path: Optional[str] = None   # 将排版和音轨最后合并好的单分镜长视频片段
    
    # Metadata / 元数据
    duration: float = 0.0                      # 该单帧的理论播放时长（秒，通常由 TTS 生成的录音长度决定）
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ContentMetadata:
    """
    内容的补充元数据对象。
    
    用于在前端或者排版模板中填充一些辅助字段 (如书名、作者)。
    """
    title: str                                 # 标题
    author: Optional[str] = None               # 作者
    subtitle: Optional[str] = None             # 副标题
    genre: Optional[str] = None                # 分类/体裁
    summary: Optional[str] = None              # 简介摘要
    publication_year: Optional[str] = None     # 出版或发布年份
    cover_url: Optional[str] = None            # 外部封面/缩略图链接


@dataclass
class Storyboard:
    """
    完整的分镜剧本聚合大纲。
    包含了剧本宏观元数据、约束配置以及各阶段帧数组。
    """
    title: str                                 # 项目标题
    config: StoryboardConfig                   # 配置策略参数
    frames: List[StoryboardFrame] = field(default_factory=list) # 帧列表序列
    
    # Content metadata (optional)
    content_metadata: Optional[ContentMetadata] = None
    
    # Final output / 总结输出
    final_video_path: Optional[str] = None     # 所有工作完成后生成的完整合并视频位置
    total_duration: float = 0.0                # 所有子片段累加后的整体时长（秒）
    
    # Metadata / 生命周期时间戳
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_completed(self) -> bool:
        """检查内部是否所有的帧段都已经顺利产出视频文件"""
        return all(
            frame.video_segment_path is not None
            for frame in self.frames
        )
    
    @property
    def progress(self) -> float:
        """返回各个分镜产出过程的总体百分比进度 (0.0-1.0)"""
        if not self.frames:
            return 0.0
        completed = sum(
            1 for frame in self.frames
            if frame.video_segment_path is not None
        )
        return completed / len(self.frames)


@dataclass
class VideoGenerationResult:
    """
    视频生成服务的最终标准交付物返回体。
    """
    video_path: str                            # 能供调用方访问的最终合成视频路径
    storyboard: Storyboard                     # 该生成作业中蕴含的完整剧本上下文（供调试与页面重演）
    duration: float                            # 视频总体持续时间
    file_size: int                             # 视频文件大小（字节 byte）
    created_at: datetime = field(default_factory=datetime.now)
