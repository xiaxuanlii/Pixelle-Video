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
Asset-based video script generation prompt

针对“资产驱动生成”工作流（AssetBasedPipeline）专属的 LLM 提示词构建器。
将系统探测出的已有素材特征与用户的带货宣发意图结合，指导大模型编纂具有对应关联性的脚本分镜。
"""


ASSET_SCRIPT_GENERATION_PROMPT = """你是一个专业的视频短剧脚本编剧。基于用户的营销意图和系统现有的媒体资产清单，请为一个时长约为 {duration} 秒的短视频编写营销脚本。非常关键的一点：在生成之前，请先侦测用户输入的自然语言语种，如果用户的意图描述是英文，你后续的所有旁白和台词都必须完全使用纯英文输出；如果是中文，则使用中文。请严格对齐多语言的输出！

## 生成约束
{title_section}- 视频营销意图/目的: {intent}
- 期望视频总时长: 约 {duration} 秒

## 可用媒体素材资产库 (请在输出中原样引用提取出的精确路径)
{assets_text}

## 创作指引
1. 语言绝对一致性：输入的意图是什么语种，你的旁白输出必须是什么语种
2. 合理估计时长：推断以实现目标 {duration} 秒大概需要切分多少个镜头 (每个镜头建议 5-15 秒左右为宜)
3. 自动归位匹配：为每一个镜头分配一个最能表达当前文案意境的素材资产
4. 旁白设计：每个镜头允许包含 1 到 3 句短句作为台词旁白
5. 丰富使用库内素材：尽量把素材库中的视频和图片用全，但遇到不够用的情况允许特定资产在多镜头被重复借用展示
6. 严格校对最终时长的总和应当与 {duration} 秒期望值保持大体相近
{title_instruction}

## 语言风格一致性警告 (必须遵守)
- 若视频意图是用中文描述，所有的配音台词必须是中文
- 若视频意图是用纯正英语描述，你不得混用语言，旁白必须地道地表现为全英语

## 结构化输出规范
你必须且只能输出包含以下字段的 JSON 数组，每个对象对应一个镜头：
- scene_number: 镜头序列号 (从 1 开始)
- asset_path: 从上方素材库中挑出来的绝对或相对文件路径字符串
- narrations: 一个存放 1-3 句短台词的字符串数组
- duration: 你预估该镜头朗读这些文字所需的大约秒数

现在请立刻开始创作 JSON 格式的脚本数据:"""


def build_asset_script_prompt(
    intent: str,
    duration: int,
    assets_text: str,
    title: str = ""
) -> str:
    """
    组装资产型脚本的智能推断构建提示词。
    
    Args:
        intent: 核心视频宣发诉求
        duration: 要求的视频整体持续时间
        assets_text: 已经整理好的所有图片/视频的路径与预探测分析描述的字符串快照
        title: (可选) 提供的一个短标题来约束文案风格方向
    
    Returns:
        str: 给大语言模型食用的提示词全文
    """
    title_section = f"- 核心标题约束: {title}\n" if title else ""
    title_instruction = f"6. 生成的主干旁白内容应该尽量向视频核心标题看齐并收拢立意: {title}\n" if title else ""
    
    return ASSET_SCRIPT_GENERATION_PROMPT.format(
        duration=duration,
        title_section=title_section,
        intent=intent,
        assets_text=assets_text,
        title_instruction=title_instruction
    )
