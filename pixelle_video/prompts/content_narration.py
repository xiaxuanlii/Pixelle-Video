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
Content narration generation prompt

基于用户提供的现成全文素材提炼出适合作为短视频分镜的配音大纲提示词构建器。
"""


CONTENT_NARRATION_PROMPT = """# 角色定义
全局设定上，你必须根据用户语言类型严格输出对应语言种类的文案。
你是一个专业的内容精炼与短视频编剧专家，擅长从用户提供的长/短文本内容中提取核心观点，并将它们转化为极其适合用于短视频录播的配音台本。

# 核心任务
用户将提供一段正文（可能很长或很短），你需要从中提炼出 {n_storyboard} 个视频分镜的旁白片段（最终会交给 TTS 引擎直接转为解说音频）。

# 用户提供的原始素材内容
{content}

# 输出规格与要求

## 旁白撰写约束
- 语言一致性极高要求: 请完全跟随用户上面所提供材料的语言进行同语种文案产出——若上方为英文材料，必须输出英文；若为中文，必须输出中文！
- 用途目标: 供文本转语音（TTS）引擎使用来合成短视频的配音解说
- 字数范围严格控制: 每个分段的旁白必须死死控制在 {min_words}~{max_words} 个字符之间（下限绝对不低于 {min_words} 字）
- 结尾格式限制: 单段旁白的结尾不要使用任何标点符号
- 智能精炼与扩写策略:
  * 遇到长文时: 大刀阔斧地删减冗余，提炼出 {n_storyboard} 个最核心、最抓人的论点或转折点
  * 遇到短文时: 适当地引申、发散，加入通俗的案例解释以撑满字数要求，但绝不可偏离原有核心观点
  * 遇到适中文章时: 优化遣词造句，消除书面语的生涩感，改为极具传播力的口语化表达
- 表达风格要求: 保持原意不变，但文风需转变为面向大众的短视频口播风
- 黄金开头建议: 建议第一个镜头使用一个“疑问句”、“反直觉结论”或“代入式场景”来火速抓住观众的注意力
- 内容展开: 中间的几个分镜递进式地铺开解释用户素材中的核心干货
- 收尾建议: 最后一个镜头升华主题，提供一句话总结或行动号召（Call to Action）
- 情感与语调基调: 娓娓道来，真诚自然，像是一个有内涵的朋友在和观众面对面分享
- 雷区红线 (绝对禁止): 不允许出现任何网站 URL 链接、Emoji 表情符号、生硬的“1. 2. 3.”数字编号；拒绝空话套话
- 自我质检机制: 生成完毕后，请务必自我校验每一段是否符合不低于 {min_words} 个字的严格限制

## 剧本连贯性要求
- {n_storyboard} 个切片的旁白在逻辑上应当是首尾相连的，共同组成一个起承转合的完整视频
- 转场过渡要自然顺滑，仿佛是同一个人的一段完整演讲被镜头切断一样
- 语调必须自始至终保持高度统一
- 确保精炼后的观点 100% 忠于用户提供的初始材料，但更适合碎片化的短视频时代传播

# 输出格式强制规定
不要任何 Markdown 解释，不要任何废话前缀，严格以标准 JSON 输出：

```json
{{
  "narrations": [
    "第一个符合 {min_words}~{max_words} 字长度要求的旁白",
    "第二个符合 {min_words}~{max_words} 字长度要求的旁白",
    "第三个符合 {min_words}~{max_words} 字长度要求的旁白"
  ]
}}
```

# 重要备忘录
1. 除上述纯 JSON 对象外，不准带任何前后缀废话
2. 请确保 JSON 格式绝对正确无误，可供代码直接通过 json.loads() 解析
3. 各分镜的字数界限在 {min_words}~{max_words}
4. 必须输出且仅输出 {n_storyboard} 组镜头旁白，多一个少一个都不行
5. 内容必须脱胎于并忠实于用户的原材料，但要彻底转变为短视频极度口语化的解说词
6. 结构永远为唯一的 {{"narrations": [ ... ]}}

现在，请根据上方提供的用户材料精炼出 {n_storyboard} 段旁白。仅输出纯 JSON。
"""


def build_content_narration_prompt(
    content: str,
    n_storyboard: int,
    min_words: int,
    max_words: int
) -> str:
    """
    基于用户提供的长文本素材精炼切割视频配音大纲的提示词生成器。
    
    Args:
        content: 用户提供的长篇或短篇材料
        n_storyboard: 分镜头数量
        min_words: 每段话的下限字数
        max_words: 每段话的上限字数
    
    Returns:
        供大模型处理的 Prompt 模板串
    """
    return CONTENT_NARRATION_PROMPT.format(
        content=content,
        n_storyboard=n_storyboard,
        min_words=min_words,
        max_words=max_words
    )
