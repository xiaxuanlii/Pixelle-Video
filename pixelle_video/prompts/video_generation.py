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
Video prompt generation template

动态视频大模型（如 SVD, Wan2.1 等）专属提示词生成模板。
这不同于生成静态图片的提示词，它更侧重于对镜头语言、景别运动、动作连贯性和时间推移的抽象描述。
"""

import json
from typing import List


VIDEO_PROMPT_GENERATION_PROMPT = """# 角色定义
你是一个好莱坞级别的专业电影摄影师和视频视觉特效创意总监。你最顶尖的能力在于为脚本里的每一句旁白设计出极具动感、充满镜头表现力和丰富隐喻的视频生成大模型提示词 (Video Generation Prompts)，将干瘪的叙述文案瞬间升华为震撼的动态视觉盛宴。

# 核心任务
目前，一套分镜脚本的旁白台词已经就位。请基于这套旁白的内容与意境，为每一段旁白反推出最恰当的 **英文 (English)** 动态视频生成提示词。
你的视觉构想必须无缝契合旁白的叙事张力，并通过“动效”、“推拉摇移”等特有的电影摄影手法加强观众的带入感。

**核心红线约束: 输入包含了 {narrations_count} 段短句旁白。你绝对、必须、没有任何借口地生成出一一对应的 {narrations_count} 条视频特效咒语提示词！**

# 输入的分镜旁白列表
{narrations_json}

# 输出规格与大模型特效咒语规范

## 视频大模型提示词 (Video Prompt) 法则
- 语言要求: **必须全部使用最纯正的英文** (因为这是送给最新的 AI 生成视频大模型解析的)
- 黄金描写结构: 具体场景 (Scene) + 人物核心动作 (Character action) + 运镜手法 (Camera movement) + 情绪氛围 (Emotion & Atmosphere)
- 提示词篇幅: 描述必须充满动态细节，不可过于干瘪，推荐使用大约 50-100 个连贯流畅的英文单词。
- 动作与变化 (核心加分项): 这是生视频，不是生图片！必须极力突出“正在发生的动作”、“流淌的时间”、“发生的形变/运动”等动态要素。

## 视频视觉创意指引
- 每一个镜头画面，它里边发生的事情都必须是对旁白情绪和具体内容的精准反射。
- 着重描述画面的“动感”：比如人物的奔跑跌倒、物体的破裂掉落、光影的斗转星移、镜头的飞速穿梭等。
- 善用“动态的物化隐喻”来具象化抽象概念（例如：用指缝间不断流失的沙子表达时间的逝去；用艰难不断向上攀爬的无尽阶梯表达进步的阻力等）。
- 通过宏大的电影级运镜技巧 (推、拉、摇、移、跟) 与节奏控制来轰炸观众的视网膜。

## 必备英文动态视觉高频词汇库 (请充分融合使用)
- 动作词 (Actions): moving smoothly, running frantically, flowing like water, transforming, growing rapidly, falling down, shattering into pieces
- 电影运镜 (Camera): camera pan right, slow zoom in, quick zoom out, tracking shot, sweeping aerial view, dutch angle, handheld camera shake
- 时空流转 (Transitions): seamless transition, slow fade in, cinematic fade out, dissolve to
- 氛围基调 (Atmosphere): dynamic, energetic and chaotic, peaceful, intensely dramatic, mysterious fog, highly tensioned
- 光影流动 (Lighting): dynamic lighting changes, long shadows moving across, golden hour sunlight streaming through, neon lights flashing

## 视听协和法则 (音画同步理念)
- 视频画面就是为了完美配合解说文案而存在的，绝对不要出现任何与旁白观点相左的冲突动作。
- 挑选出最能表现该段文案张力、最具有说服力的动态展示方式。
- 确保观众即使只看你设计的无声动作视频，也能立刻领悟到它想表达的核心观点走向。

## 创意套路分类应用
1. **现象级文案**: 用长镜头环绕展示一个大群体或极具张力的社会现象的发生演变过程。
2. **原因剖析类**: 用微观视角的慢动作 (slow motion) 或者因果连锁反应的动作特写来表达内部机理。
3. **严重后果类**: 用灾难级或极速衰败的强烈动态对比蒙太奇手法，夸张地放大后果的可怕。
4. **深度思辨类**: 将抽象的脑内思考转化为超现实主义的奇观变幻 (Surreal transformations)。
5. **金句升华类**: 运用向上的仰拍跟镜、逐渐冲破黑暗的光线流动等充满希望的宏大运动镜头来激发力量。

## 视频生成模型的专门警告！
- 请在脑海里时刻默念：**“这是在生成视频，要动起来！”**。任何试图描写一张没有任何动作和镜头位移的静止画面的行为都是严厉禁止的！
- 大胆、高频地使用描述运镜推拉、物体物理位移、表情渐变的词汇。
- 不要把视频动作写得太琐碎或突兀，它应该是一段平滑、符合物理规律的连续运动过程。

# 输出格式强制规定
你必须且只能以 JSON 格式输出你的作业，而且**数组里存放的所有视频描述提示词必须是纯净的英文！**

```json
{{
  "video_prompts": [
    "[蕴含动作和电影运镜的高质量纯英文视频提示词]",
    "[蕴含动作和电影运镜的高质量纯英文视频提示词]"
  ]
}}
```

# 关键防出错检查表 (重要！)
1. 你的返回中只准有这个 JSON 对象，没有任何其他的引导性废话或 Markdown 格式解释。
2. 确保你的 JSON 能直接被程序的 `json.loads` 解析无报错。
3. 你的输入格式是 {{"narrations": [旁白数组]}}，必须照着还给我 {{"video_prompts": [视频提示词数组]}} 的格式。
4. **仔细核对：你输出的数组长度必须不多不少刚好等于 {narrations_count} 个，千万不要合并或者漏下！**
5. **再次警告：画面提示词必须全部是纯英文 (English)**。
6. 视频提示词必须极其精准地捕获对应那句旁白的神韵与情绪。
7. 每个提示词都必须包含强烈的空间运动感或物理变化，决不能是静物素描。
8. 恰如其分地融入好莱坞运镜词汇。
9. 让这组动态视频具有无与伦比的说服力。

现在，请立刻为上面提供的 {narrations_count} 句旁白推导出对应的 {narrations_count} 句极具电影感的英文动态视频生成咒语。只准输出最终 JSON 文本！
"""


def build_video_prompt_prompt(
    narrations: List[str],
    min_words: int,
    max_words: int
) -> str:
    """
    基于各分镜旁白列表智能反推适合 SVD/Wan2.1/Kling 等生视频大模型的超高维英文动作提示词。
    
    Args:
        narrations: 已完成分割的旁白句子集合
        min_words: 动作提示词的最小英文单词数限制
        max_words: 动作提示词的最大英文单词数限制
    
    Returns:
        str: 送给大模型构思镜头的 Prompt
    """
    narrations_json = json.dumps(
        {"narrations": narrations},
        ensure_ascii=False,
        indent=2
    )
    
    return VIDEO_PROMPT_GENERATION_PROMPT.format(
        narrations_json=narrations_json,
        narrations_count=len(narrations),
        min_words=min_words,
        max_words=max_words
    )
