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
TTS Voice Configuration

定义了本地免费的 Edge TTS 推理可用的音色集合及枚举标识。
"""

from typing import List, Dict, Any


# 微软 Edge TTS 官方提供的高质量免费配音员标识符
EDGE_TTS_VOICES: List[Dict[str, Any]] = [
    # Chinese voices
    {
        "id": "zh-CN-XiaoxiaoNeural",
        "label_key": "tts.voice.zh_CN_XiaoxiaoNeural",
        "locale": "zh-CN",
        "gender": "female"
    },
    {
        "id": "zh-CN-XiaoyiNeural",
        "label_key": "tts.voice.zh_CN_XiaoyiNeural",
        "locale": "zh-CN",
        "gender": "female"
    },
    {
        "id": "zh-CN-YunjianNeural",
        "label_key": "tts.voice.zh_CN_YunjianNeural",
        "locale": "zh-CN",
        "gender": "male"
    },
    {
        "id": "zh-CN-YunxiNeural",
        "label_key": "tts.voice.zh_CN_YunxiNeural",
        "locale": "zh-CN",
        "gender": "male"
    },
    {
        "id": "zh-CN-YunyangNeural",
        "label_key": "tts.voice.zh_CN_YunyangNeural",
        "locale": "zh-CN",
        "gender": "male"
    },
    {
        "id": "zh-CN-YunyeNeural",
        "label_key": "tts.voice.zh_CN_YunyeNeural",
        "locale": "zh-CN",
        "gender": "male"
    },
    {
        "id": "zh-CN-YunfengNeural",
        "label_key": "tts.voice.zh_CN_YunfengNeural",
        "locale": "zh-CN",
        "gender": "male"
    },
    {
        "id": "zh-CN-liaoning-XiaobeiNeural",
        "label_key": "tts.voice.zh_CN_liaoning_XiaobeiNeural",
        "locale": "zh-CN",
        "gender": "female"
    },
    {
        "id": "en-US-AriaNeural",
        "label_key": "tts.voice.en_US_AriaNeural",
        "locale": "en-US",
        "gender": "female"
    },
    {
        "id": "en-US-JennyNeural",
        "label_key": "tts.voice.en_US_JennyNeural",
        "locale": "en-US",
        "gender": "female"
    },
    {
        "id": "en-US-GuyNeural",
        "label_key": "tts.voice.en_US_GuyNeural",
        "locale": "en-US",
        "gender": "male"
    },
    {
        "id": "en-US-DavisNeural",
        "label_key": "tts.voice.en_US_DavisNeural",
        "locale": "en-US",
        "gender": "male"
    },
    {
        "id": "en-GB-SoniaNeural",
        "label_key": "tts.voice.en_GB_SoniaNeural",
        "locale": "en-GB",
        "gender": "female"
    },
    {
        "id": "en-GB-RyanNeural",
        "label_key": "tts.voice.en_GB_RyanNeural",
        "locale": "en-GB",
        "gender": "male"
    },
    {
        "id": "ko-KR-InJoonNeural",
        "label_key": "tts.voice.ko-KR-InJoonNeural",
        "locale": "ko-KR",
        "gender": "male"
    },
    {
        "id": "ko-KR-SunHiNeural",
        "label_key": "tts.voice.ko-KR-SunHiNeural",
        "locale": "ko-KR",
        "gender": "female"
    },
    {
        "id": "fr-FR-EloiseNeural",
        "label_key": "tts.voice.fr-FR-EloiseNeural",
        "locale": "fr-FR",
        "gender": "female"
    },
    {
        "id": "fr-FR-HenriNeural",
        "label_key": "tts.voice.fr-FR-HenriNeural",
        "locale": "fr-FR",
        "gender": "male"
    },
    {
        "id": "pt-PT-DuarteNeural",
        "label_key": "tts.voice.pt-PT-DuarteNeural",
        "locale": "pt-PT",
        "gender": "male"
    },
    {
        "id": "pt-PT-RaquelNeural",
        "label_key": "tts.voice.pt-PT-RaquelNeural",
        "locale": "pt-PT",
        "gender": "female"
    },
    {
        "id": "de-DE-AmalaNeural",
        "label_key": "tts.voice.de-DE-AmalaNeural",
        "locale": "de-DE",
        "gender": "female"
    },
    {
        "id": "de-DE-ConradNeural",
        "label_key": "tts.voice.de-DE-ConradNeural",
        "locale": "de-DE",
        "gender": "male"
    },
    
    # English voices
    {
        "id": "ru-RU-DmitryNeural",
        "label_key": "tts.voice.ru-RU-DmitryNeural",
        "locale": "ru-RU",
        "gender": "male"
    },
    {
        "id": "ru-RU-SvetlanaNeural",
        "label_key": "tts.voice.ru-RU-SvetlanaNeural",
        "locale": "ru-RU",
        "gender": "female"
    },
    {
        "id": "tr-TR-AhmetNeural",
        "label_key": "tts.voice.tr-TR-AhmetNeural",
        "locale": "tr-TR",
        "gender": "male"
    },
    {
        "id": "tr-TR-EmelNeural",
        "label_key": "tts.voice.tr-TR-EmelNeural",
        "locale": "tr-TR",
        "gender": "female"
    },
    {
        "id": "es-ES-AlvaroNeural",
        "label_key": "tts.voice.es-ES-AlvaroNeural",
        "locale": "es-ES",
        "gender": "male"
    },
    {
        "id": "es-ES-ElviraNeural",
        "label_key": "tts.voice.es-ES-ElviraNeural",
        "locale": "es-ES",
        "gender": "female"
    },
]


def get_voice_display_name(voice_id: str, tr_func=None, locale: str = "zh_CN") -> str:
    """
    获取音色的前端显示名称。
    
    如果提供了前端页面的国际化翻译函数则调用之，否则返回原始的英语 ID 标识。
    
    Args:
        voice_id: 音色 ID (如: "zh-CN-YunjianNeural")
        tr_func: 外部注入的多语言翻译器钩子
        locale: 当前用户语言
    
    Returns:
        适合页面渲染展示的美化名称。
    """
    # 匹配查找对应的字典结构
    voice_config = next((v for v in EDGE_TTS_VOICES if v["id"] == voice_id), None)
    
    if not voice_config:
        return voice_id
    
    # 中文环境下如果有提供翻译函数器则尝试获取中文可读别名
    if locale == "zh_CN" and tr_func:
        label_key = voice_config["label_key"]
        return tr_func(label_key)
    
    return voice_id


def speed_to_rate(speed: float) -> str:
    """
    将用户界面的浮点数倍数语速转换为底层库要求的百分比差值标识。
    
    Args:
        speed: 播放速度乘数倍率 (1.0 = 原速，1.2 = 快 20%)
    
    Returns:
        类似 "+20%", "-10%" 等字符串格式要求。
    """
    percentage = int((speed - 1.0) * 100)
    sign = "+" if percentage >= 0 else ""
    return f"{sign}{percentage}%"
