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
Configuration schema with Pydantic models

系统配置对象的 Pydantic Schema 模块。
定义了整个应用的配置数据结构、参数类型校验规则以及系统默认的出厂配置。
这是唯一一份真实有效的配置结构约定（Single Source of Truth）。
"""
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """
    大语言模型 (LLM) 相关的配置。
    支持所有兼容 OpenAI 接口规范的 API (例如 Ollama, Qwen, DeepSeek 等)。
    """
    api_key: str = Field(default="", description="调用的 API 凭证 (如果是本地 Ollama 可任意填写)")
    base_url: str = Field(default="", description="大模型 API 服务的基础地址")
    model: str = Field(default="", description="需要具体调用的模型名标识")


class APIProviderCommonConfig(BaseModel):
    """Common API provider settings"""
    print_model_input: bool = Field(default=False, description="Print provider request parameters for debugging")
    local_proxy: str = Field(default="", description="Local HTTP proxy for providers that need it")


class APIKeyProviderConfig(BaseModel):
    """Provider settings with API key and optional base URL"""
    api_key: str = Field(default="", description="Provider API Key")
    base_url: str = Field(default="", description="Provider API Base URL")
    use_proxy: bool = Field(default=False, description="Route provider requests through common local proxy")


class AccessSecretProviderConfig(BaseModel):
    """Provider settings with access key / secret key credentials"""
    base_url: str = Field(default="", description="Provider API Base URL")
    access_key: str = Field(default="", description="Provider Access Key")
    secret_key: str = Field(default="", description="Provider Secret Key")
    use_proxy: bool = Field(default=False, description="Route provider requests through common local proxy")


class APIProvidersConfig(BaseModel):
    """Direct model provider API configuration"""
    common: APIProviderCommonConfig = Field(default_factory=APIProviderCommonConfig)
    openai: APIKeyProviderConfig = Field(default_factory=APIKeyProviderConfig)
    dashscope: APIKeyProviderConfig = Field(default_factory=APIKeyProviderConfig)
    deepseek: APIKeyProviderConfig = Field(default_factory=APIKeyProviderConfig)
    gemini: APIKeyProviderConfig = Field(default_factory=APIKeyProviderConfig)
    ark: APIKeyProviderConfig = Field(default_factory=APIKeyProviderConfig)
    kling: AccessSecretProviderConfig = Field(default_factory=AccessSecretProviderConfig)


class TTSLocalConfig(BaseModel):
    """本地轻量级文本转语音 (Edge TTS) 的专属配置。"""
    voice: str = Field(default="zh-CN-YunjianNeural", description="微软 Edge TTS 指定的默认音色")
    speed: float = Field(default=1.2, ge=0.5, le=2.0, description="默认语速倍率 (0.5 到 2.0 倍数范围)")


class TTSComfyUIConfig(BaseModel):
    """基于 ComfyUI/RunningHub 引擎的复杂 TTS 配置。"""
    default_workflow: Optional[str] = Field(default=None, description="调用 TTS 服务时默认选用的工作流模板名称")


class TTSSubConfig(BaseModel):
    """总汇 TTS 子配置树 (嵌套于 comfyui 节点下)"""
    inference_mode: str = Field(default="local", description="系统默认的 TTS 推理引擎模式 ('local' 或 'comfyui')")
    local: TTSLocalConfig = Field(default_factory=TTSLocalConfig, description="本地 Edge TTS 相关配置项")
    comfyui: TTSComfyUIConfig = Field(default_factory=TTSComfyUIConfig, description="云端 ComfyUI TTS 相关配置项")
    
    # 为了向下兼容那些还在根节点读取 default_workflow 的旧代码而设立的动态属性
    @property
    def default_workflow(self) -> Optional[str]:
        """获取默认的 ComfyUI 工作流"""
        return self.comfyui.default_workflow


class ImageSubConfig(BaseModel):
    """图像生成引擎专属子配置树 (嵌套于 comfyui 节点下)"""
    default_workflow: Optional[str] = Field(default=None, description="默认的 AI 绘画工作流名称")
    prompt_prefix: str = Field(
        default="Minimalist black-and-white matchstick figure style illustration, clean lines, simple sketch style",
        description="强制附加于所有生成提示词最前方的全局风格修饰词（常用于统一 IP 视觉风格）"
    )


class VideoSubConfig(BaseModel):
    """视频生成引擎专属子配置树 (嵌套于 comfyui 节点下)"""
    default_workflow: Optional[str] = Field(default=None, description="默认的生视频大模型工作流名称")
    prompt_prefix: str = Field(
        default="Minimalist black-and-white matchstick figure style illustration, clean lines, simple sketch style",
        description="附加于所有动态视频提示词的全局风格修饰词"
    )


class ComfyUIConfig(BaseModel):
    """
    图像与媒体引擎中心配置，主要针对 ComfyKit 底层的调用环境设置。
    """
    comfyui_url: str = Field(default="http://127.0.0.1:8188", description="本地私有化 ComfyUI 服务的监听地址")
    comfyui_api_key: Optional[str] = Field(default=None, description="如果本地服务器启用了鉴权则在此填写（可选）")
    runninghub_api_key: Optional[str] = Field(default=None, description="云端大厂算力服务商 RunningHub 的 API Key（可选）")
    runninghub_concurrent_limit: int = Field(default=1, ge=1, le=10, description="限制派发给 RunningHub 并发处理的任务最大数量 (1-10)")
    runninghub_instance_type: Optional[str] = Field(default=None, description="请求 RunningHub 分配的具体算力型号（如 'plus' 可获得 48GB 显存用于巨型任务）")
    tts: TTSSubConfig = Field(default_factory=TTSSubConfig, description="语音引擎相关配置")
    image: ImageSubConfig = Field(default_factory=ImageSubConfig, description="图像绘画相关配置")
    video: VideoSubConfig = Field(default_factory=VideoSubConfig, description="动态视频相关配置")


class TemplateConfig(BaseModel):
    """HTML 排版模板引擎配置"""
    default_template: str = Field(
        default="1080x1920/image_default.html",
        description="整个系统兜底使用的画面排版 HTML 模板"
    )


class PixelleVideoConfig(BaseModel):
    """
    Pixelle-Video 整个应用系统的终极配置根节点对象。
    它将上方的所有配置子树组合在一起，并提供了安全验证功能。
    """
    project_name: str = Field(default="Pixelle-Video", description="项目的名称标识")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    api_providers: APIProvidersConfig = Field(default_factory=APIProvidersConfig)
    comfyui: ComfyUIConfig = Field(default_factory=ComfyUIConfig)
    template: TemplateConfig = Field(default_factory=TemplateConfig)
    
    def is_llm_configured(self) -> bool:
        """快速检查大模型 API 相关的几个关键字段是否被妥善填写"""
        return bool(
            self.llm.api_key and self.llm.api_key.strip() and
            self.llm.base_url and self.llm.base_url.strip() and
            self.llm.model and self.llm.model.strip()
        )
    
    def validate_required(self) -> bool:
        """整个系统的可用性预检入口。目前最核心的是必须确保大模型接通。"""
        return self.is_llm_configured()
    
    def to_dict(self) -> dict:
        """
        导出为干净的字典结构，向下兼容整个 codebase 中直接以 config.get() 方式获取参数的旧逻辑。
        """
        return self.model_dump()
