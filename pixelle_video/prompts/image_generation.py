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
Image prompt generation template

画面提示词生成提示模板。
负责通过已确定的旁白脚本为底层的 Stable Diffusion/ComfyUI 等生图引擎
推理出高质量的英文（多数生图大模型只懂英文）画面描述词。
"""

import json
from typing import List, Optional


# ==================== PRESET IMAGE STYLES ====================
# 为不同业务场景预置的全局默认画面美术风格修饰语字典

IMAGE_STYLE_PRESETS = {
    "stick_figure": {
        "name": "火柴人草图 (Stick Figure Sketch)",
        "description": "stick figure style sketch, black and white lines, pure white background, minimalist hand-drawn feel",
        "use_case": "通用解说、哲学、搞笑等各类简明直观的小短剧场景"
    },
    
    "minimal": {
        "name": "极简抽象风 (Minimalist Abstract)",
        "description": "minimalist abstract art, geometric shapes, clean composition, modern design, soft pastel colors",
        "use_case": "高深理论、科技向、现代感氛围"
    },
    
    "concept": {
        "name": "概念隐喻风 (Conceptual Visual)",
        "description": "conceptual visual metaphors, symbolic elements, thought-provoking imagery, artistic interpretation",
        "use_case": "深度思考、悬疑、复杂哲学与社科分析等引人深思的话题"
    },
}

# 系统默认初始风格
DEFAULT_IMAGE_STYLE = "stick_figure"


IMAGE_PROMPT_GENERATION_PROMPT = """# 角色定义
你是一个世界顶级的视觉创意设计师。你极度擅长为视频脚本的台词设计极具表现力和绝佳隐喻的画面 Prompt 提示词，你能把极其抽象和枯燥的理论概念瞬间具象化为极具张力的视觉场景。

# 核心任务
目前，一套分镜脚本的旁白台词已经确定。请基于这套旁白，为每一句话/每一段大纲推理出对应的 **英文 (English)** 画面生成提示词 (Image Prompts)。
你的画面设计必须能够完美辅助讲述旁白的含义，并加深观众的记忆点和观看体验。

**关键约束: 用户提供的输入大纲数组中包含有 {narrations_count} 段旁白。你必须绝对一一对应地生成 {narrations_count} 个画面提示词。**

# 输入的分镜旁白列表
{narrations_json}

# 输出规格要求

## 画面提示词 (Image Prompt) 规则
- 语言要求: **必须使用纯正的英文输出** (因为这是给 Stable Diffusion、Flux 等国外 AI 绘画大模型识别的)
- 描写结构规范: 具体场景 (Scene) + 人物姿态/动作 (Action) + 面部神态/情绪 (Emotion) + 象征物/画面特效元素 (Symbolic elements)
- 提示词长度建议: 请保证画面的描绘详尽而充满创意，推荐长度控制在 50-100 个英文单词之间

## 视觉与创意指引
- 画面的具体内容必须精准地响应其对应旁白所要传递的信息
- 【高级技巧】善用“物化隐喻”来表达抽象主题（例如：用布满荆棘分岔路口表示人生的选择困境；用沉重的锁链或者背负的巨石来表达精神内耗的压力）
- 场景应该充满张力，即使没有画面动效也能通过视觉构图传递“动态的错觉”和“丰沛的情绪”
- 构图和前景排版要大胆，拒绝枯燥直白的无聊元素罗列

## 关键英文 Prompt 句式与词汇参考
- 象征元素: symbolic elements (e.g., shattered clocks, floating bubbles)
- 情绪面貌: expression / facial expression (e.g., contemplative, anxious, enlightened)
- 肢体动作: action / gesture / movement (e.g., reaching out, standing at the edge, observing closely)
- 场景布置: scene / setting (e.g., abandoned industrial hall, vast empty space, surreal floating island)
- 氛围渲染: atmosphere / mood (e.g., cyberpunk lighting, cinematic moody lighting, ethereal glow)

## 视听协和法则 (音画同步)
- 画面始终服务于解说文案，是你传递观点最有力的“辅助作证画面”
- 杜绝一切与配音台词中明显相悖或导致跳戏的视觉元素
- 把最难懂的文字通过最易懂、最震撼的视觉画面抛给观众

## 分类创意套路指导
1. **揭露现象类文案**: 画一个非常直观且略带夸张的社会现实冲突场景。
2. **原因剖析类文案**: 通过强烈的视觉隐喻 (Visual metaphors) 展现因果关系的内耗。
3. **严重后果类文案**: 利用废墟、毁灭、巨大的对比落差场景来放大后果的可怕。
4. **深度思辨类文案**: 将非常抽象的哲学概念做宏大化的超现实空间具象处理。
5. **金句总结类文案**: 画面需要走向开阔、光明，通过引导性的标志物 (如光芒、通天大门) 来传递获得新生的启迪感。

# 输出格式强制规定
你只能以标准纯粹的 JSON 格式输出结果，且**内部包含的 image_prompts 数组字符串必须完全是英文！**

```json
{{
  "image_prompts": [
    "[第一句旁白对应的高质量细致英文画面描述词]",
    "[第二句旁白对应的高质量细致英文画面描述词]"
  ]
}}
```

# 关键防出错检查表 (重要！)
1. 你的返回中只准有这个 JSON 对象，没有任何其他的引导性废话或 Markdown 格式解释。
2. 确保你的 JSON 能直接被程序的 `json.loads` 解析无报错。
3. 返回 JSON 永远并且只能是 {{"image_prompts": [ 字符串数组 ]}} 的单一形式。
4. **仔细核对：你输出的数组长度必须不多不少刚好等于 {narrations_count} 个，千万不要合并或者漏下！**
5. **再次警告：画面提示词必须全部是纯英文 (English)**。
6. 不允许偷懒，不允许每个镜头使用差不多完全相似的场景词。
7. 拒绝无聊的构图，通过光影、夸张的比例和极具情感色彩的词汇加强图片的感染力。

现在，请立刻为上面提供的 {narrations_count} 句旁白推导出对应的 {narrations_count} 个英文视觉绘图咒语。只准输出最终 JSON 文本！
"""


def build_image_prompt_prompt(
    narrations: List[str],
    min_words: int,
    max_words: int
) -> str:
    """
    基于各分镜旁白列表智能反推适合 SD/Flux 大模型绘图的高维英文提示词。
    
    注意：系统层面的前缀修饰语（如 "masterpiece, anime style"）将会在稍后代码中强制组合，
    此处的 Prompt 只负责让大模型依据上下文构思画面的“主体核心内容”。
    
    Args:
        narrations: 已完成分割的旁白句子集合
        min_words: 对单一画面提示词的最小词数约束
        max_words: 对单一画面提示词的最大词数约束
    
    Returns:
        str: 送给大模型分析构思的 Prompt
    """
    # 将包含多级双引号单引号等容易出问题的旁白内容转换为极度安全的 json 字符串快照
    narrations_json = json.dumps(
        {"narrations": narrations},
        ensure_ascii=False,
        indent=2
    )
    
    return IMAGE_PROMPT_GENERATION_PROMPT.format(
        narrations_json=narrations_json,
        narrations_count=len(narrations),
        min_words=min_words,
        max_words=max_words
    )
