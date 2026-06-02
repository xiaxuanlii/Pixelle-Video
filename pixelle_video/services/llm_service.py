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
LLM (Large Language Model) Service - Direct OpenAI SDK implementation

大语言模型（LLM）服务层 - 基于 OpenAI SDK 的直接封装。
为系统提供文本续写、角色扮演对话以及结构化数据提取等能力。
支持通过 `response_type` 参数（传入 Pydantic 模型）来强制输出结构化 JSON 数据。
"""

import json
import re
from typing import Optional, Type, TypeVar, Union

from openai import AsyncOpenAI
from pydantic import BaseModel
from loguru import logger


# 定义泛型 T，用于约束和推断返回的 Pydantic 模型类型
T = TypeVar("T", bound=BaseModel)


class LLMService:
    """
    大语言模型 (LLM) 核心服务类。
    
    直接使用官方的 openai-python SDK 进行封装，不需要经过中间件（ComfyKit 等）。
    通过配置不同的 `base_url` 和 `api_key`，天然兼容市面上所有兼容 OpenAI 接口规范的模型提供商：
    - OpenAI 官方 (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
    - 阿里云通义千问 Qwen (qwen-max, qwen-plus, qwen-turbo)
    - Anthropic Claude (claude-sonnet-3-5)
    - 深度求索 DeepSeek (deepseek-chat)
    - 月之暗面 Kimi (moonshot-v1-8k 等)
    - Ollama 本地开源大模型 (llama3, qwen2, mistral) - 免费且支持完全离线！
    
    使用示例:
        # 直接进行文本问答
        answer = await pixelle_video.llm("解释一下什么是原子习惯")
        
        # 携带超参数
        answer = await pixelle_video.llm(
            prompt="用三句话总结《百年孤独》的剧情",
            temperature=0.7,
            max_tokens=2000
        )
    """
    
    def __init__(self, config: dict):
        """
        初始化 LLM 服务。
        
        Args:
            config: 完整的应用程序配置字典（为了向后兼容而保留参数签名）。
        """
        # 注意：此处不再将配置缓存在实例属性中，而是每次调用时实时从全局 config_manager 中读取。
        # 这样设计是为了支持在不重启服务的情况下进行配置热重载（Hot Reload）。
        self._client: Optional[AsyncOpenAI] = None
    
    def _get_config_value(self, key: str, default=None):
        """
        从全局单例 config_manager 中动态读取配置项的值。
        
        Args:
            key: 配置键名（例如 "api_key", "base_url"）。
            default: 如果配置中未找到该键，返回的默认值。
        
        Returns:
            获取到的配置值。
        """
        from pixelle_video.config import config_manager
        return getattr(config_manager.config.llm, key, default)
    
    def _create_client(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> AsyncOpenAI:
        """
        创建 AsyncOpenAI 异步 HTTP 客户端实例。
        
        Args:
            api_key: (可选) 会话级 API 密钥。若不提供，则使用系统全局配置。
            base_url: (可选) 会话级 Base URL。若不提供，则使用系统全局配置。
        
        Returns:
            AsyncOpenAI 客户端实例。
        """
        # 获取最终使用的 API Key（优先级：方法传参 > 全局配置 > 占位符）
        final_api_key = (
            api_key
            or self._get_config_value("api_key")
            or "dummy-key"  # 针对本地 Ollama 等不需要密钥的环境，提供占位符避免 SDK 报错
        )
        
        # 获取最终使用的 Base URL（优先级：方法传参 > 全局配置）
        final_base_url = (
            base_url
            or self._get_config_value("base_url")
        )
        
        # 初始化客户端
        client_kwargs = {"api_key": final_api_key}
        if final_base_url:
            client_kwargs["base_url"] = final_base_url
        
        return AsyncOpenAI(**client_kwargs)
    
    async def __call__(
        self,
        prompt: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_type: Optional[Type[T]] = None,
        **kwargs
    ) -> Union[str, T]:
        """
        核心调用方法：向大语言模型发送请求并获取回复。
        
        Args:
            prompt: 发送给大模型的提示词（问题或指令）。
            api_key: 覆盖当前请求的 API Key。
            base_url: 覆盖当前请求的 Base URL。
            model: 覆盖当前请求的模型名称。
            temperature: 采样温度（0.0-2.0）。值越低，输出越稳定、保守；值越高，输出越具有创造性和随机性。
            max_tokens: 允许生成的最大 Token 数量。
            response_type: (核心特性) 指定一个 Pydantic 数据模型类。如果提供，
                           底层会引导模型输出符合该结构的 JSON，并自动反序列化为该类实例返回。
            **kwargs: 其他支持传递给底层 SDK 的高级参数。
        
        Returns:
            Union[str, T]: 默认返回字符串文本。如果提供了 `response_type`，则返回对应的 Pydantic 模型实例。
        
        Examples:
            # 基础文本生成
            answer = await pixelle_video.llm("解释一下原子习惯")
            
            # 结构化数据输出 (Structured output)
            class MovieReview(BaseModel):
                title: str
                rating: int
                summary: str
            
            review = await pixelle_video.llm(
                prompt="请为电影《盗梦空间》写一篇短评",
                response_type=MovieReview
            )
            print(review.title)  # 以面向对象的方式安全访问结果
        """
        # 每次调用都创建新实例，以完美支持并发时不同请求携带不同配置的需求
        client = self._create_client(api_key=api_key, base_url=base_url)
        
        # 获取要调用的具体模型（优先级：方法传参 > 全局配置 > 默认兜底）
        final_model = (
            model
            or self._get_config_value("model")
            or "gpt-3.5-turbo"
        )
        
        logger.debug(f"LLM call: model={final_model}, base_url={client.base_url}, response_type={response_type}")
        
        try:
            if response_type is not None:
                # 开启结构化输出模式：引导模型按需输出 JSON，并执行解析
                return await self._call_with_structured_output(
                    client=client,
                    model=final_model,
                    prompt=prompt,
                    response_type=response_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                # 标准纯文本输出模式
                response = await client.chat.completions.create(
                    model=final_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                result = response.choices[0].message.content
                logger.debug(f"LLM response length: {len(result)} chars")
                
                return result
        
        except Exception as e:
            logger.error(f"LLM call error (model={final_model}, base_url={client.base_url}): {e}")
            raise
    
    async def _call_with_structured_output(
        self,
        client: AsyncOpenAI,
        model: str,
        prompt: str,
        response_type: Type[T],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> T:
        """
        内部方法：支持广泛兼容性的结构化数据生成机制。
        
        考虑到除了 OpenAI 官方以外，很多兼容厂商（如 Qwen, DeepSeek, Ollama）
        并不完全支持原生的 `beta.chat.completions.parse` 强约束协议。
        为了最大化兼容性，我们采用“软约束”策略：将 Pydantic 模型的 JSON Schema
        转换为强硬的指令词（Prompt），并追加到用户输入之后。
        
        Args:
            client: OpenAI 客户端实例。
            model: 模型名称。
            prompt: 原始提示词。
            response_type: 目标 Pydantic 数据模型类。
            temperature: 采样温度。
            max_tokens: 最大生成数量。
            **kwargs: 额外透传参数。
        
        Returns:
            目标 Pydantic 模型类的实例化对象。
        """
        # 构建 JSON Schema 结构描述指令，并硬塞到用户的提示词之后
        json_schema_instruction = self._get_json_schema_instruction(response_type)
        enhanced_prompt = f"{prompt}\n\n{json_schema_instruction}"
        
        # 发起常规对话请求
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": enhanced_prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        content = response.choices[0].message.content
        
        logger.debug(f"Structured output response length: {len(content)} chars")
        
        # 将返回的文本执行容错解析并实例化为 Pydantic 对象
        return self._parse_response_as_model(content, response_type)
    
    def _get_json_schema_instruction(self, response_type: Type[T]) -> str:
        """
        内部辅助方法：提取 Pydantic 模型的 Schema，并生成指导大模型输出的指令。
        
        Args:
            response_type: 目标 Pydantic 模型类。
        
        Returns:
            str: 格式化好的系统级指令词。
        """
        try:
            # 提取规范的 JSON Schema 结构
            schema = response_type.model_json_schema()
            schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
            
            return f"""## 重要指示：必须使用 JSON 格式输出
你必须只返回一个有效的 JSON 对象（不需要使用 markdown 代码块，不需要任何多余的解释文本）。
返回的 JSON 结构必须严格符合以下 Schema 定义：

```json
{schema_str}
```

请再次确认：只输出 JSON 对象本身，不要包含其他任何字符。"""
        except Exception as e:
            logger.warning(f"Failed to generate JSON schema: {e}")
            return """## 重要指示：必须使用 JSON 格式输出
你必须只返回一个有效的 JSON 对象（不需要使用 markdown 代码块，不需要任何多余的解释文本）。"""
    
    def _parse_response_as_model(self, content: str, response_type: Type[T]) -> T:
        """
        内部辅助方法：带有多重容错机制的 JSON 提取与解析器。
        
        因为各种大模型的智商参差不齐，有时候会忽略指令，在 JSON 前后带上废话。
        这个方法会尝试多种正则策略，把真正的 JSON 对象“扣”出来。
        
        Args:
            content: 大模型返回的原始文本。
            response_type: 需要反序列化的目标 Pydantic 类。
        
        Returns:
            反序列化成功的 Pydantic 实例。
            
        Raises:
            ValueError: 所有的提取尝试都失败时抛出。
        """
        # 策略 1: 模型很听话，返回的就是纯净的 JSON 字符串
        try:
            data = json.loads(content)
            return response_type.model_validate(data)
        except json.JSONDecodeError:
            pass
        
        # 策略 2: 模型使用了 Markdown 语法把 JSON 包起来了（如 ```json ... ```）
        json_pattern = r'```(?:json)?\s*([\s\S]+?)\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return response_type.model_validate(data)
            except json.JSONDecodeError:
                pass
        
        # 策略 3: 最暴力的提取，直接寻找第一对最外层的大括号 {}
        brace_start = content.find('{')
        brace_end = content.rfind('}')
        if brace_start != -1 and brace_end > brace_start:
            try:
                json_str = content[brace_start:brace_end + 1]
                data = json.loads(json_str)
                return response_type.model_validate(data)
            except json.JSONDecodeError:
                pass
        
        # 实在救不回来了
        raise ValueError(f"Failed to parse LLM response as {response_type.__name__}: {content[:200]}...")
    
    @property
    def active(self) -> str:
        """
        获取当前正处于激活配置状态的大模型名称。
        
        Returns:
            当前生效的模型标识。
        """
        return self._get_config_value("model", "gpt-3.5-turbo")
    
    def __repr__(self) -> str:
        """调试时友好的对象字符串表示"""
        model = self.active
        base_url = self._get_config_value("base_url", "default")
        return f"<LLMService model={model!r} base_url={base_url!r}>"

