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
LLM utility functions for model discovery and connection testing.

大语言模型连接测试与探测工具库。
使用兼容 OpenAI API 规范的 `/v1/models` 端点探测服务可用性及当前后端的模型列表。
"""

from typing import List, Tuple
import httpx
from loguru import logger


def fetch_available_models(api_key: str, base_url: str, timeout: float = 10.0) -> List[str]:
    """
    探测目标 API 节点上所有可以提供调用的大模型列表。
    
    使用标准的 GET /v1/models 端点，并采用传入的 api_key 进行 Bearer 验证。
    
    Args:
        api_key: 验证密钥。
        base_url: 基础地址 (例如 https://api.openai.com/v1)。
        timeout: 超时时间（秒）。
    
    Returns:
        List[str]: 模型标识名称列表。
        
    Raises:
        httpx.HTTPStatusError: 网络请求返回非 2xx 状态码时。
        httpx.RequestError: 网络完全不通时。
    """
    # Normalize base_url - ensure it ends with /v1 or similar
    base_url = base_url.rstrip("/")
    
    # Build the models endpoint URL
    # Handle cases where base_url might or might not include /v1
    if base_url.endswith("/v1"):
        models_url = f"{base_url}/models"
    else:
        models_url = f"{base_url}/v1/models"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    logger.debug(f"Fetching models from: {models_url}")
    
    with httpx.Client(timeout=timeout) as client:
        response = client.get(models_url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        models = [model["id"] for model in data.get("data", [])]
        
        # Sort models alphabetically for better UX
        models.sort()
        
        logger.debug(f"Fetched {len(models)} models")
        return models


def test_llm_connection(api_key: str, base_url: str, timeout: float = 10.0) -> Tuple[bool, str, int]:
    """
    全面测试 LLM 服务的连通性。
    
    尝试调用模型列表接口。根据不同的报错类型进行分类拦截，并返回友好的中文调试信息。
    主要用于在 Web UI 控制台中展示服务器的连接状态，帮助用户排查配置错误。
    
    Args:
        api_key: 验证密钥。
        base_url: 基础地址。
        timeout: 超时时间（秒）。
    
    Returns:
        Tuple[bool, str, int]:
        - success: 成功为 True。
        - message: 带有可读性的提示反馈文本。
        - model_count: 探测到的可用模型数量。
    """
    try:
        models = fetch_available_models(api_key, base_url, timeout)
        return True, f"Connection successful! {len(models)} models available.", len(models)
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code == 401:
            return False, "Authentication failed: Invalid API Key", 0
        elif status_code == 403:
            return False, "Access forbidden: Check your API Key permissions", 0
        elif status_code == 404:
            return False, "API endpoint not found: Check your Base URL", 0
        else:
            return False, f"API error: HTTP {status_code}", 0
    except httpx.ConnectError:
        return False, "Connection failed: Cannot reach the server", 0
    except httpx.TimeoutException:
        return False, "Connection timeout: Server did not respond in time", 0
    except Exception as e:
        logger.error(f"LLM connection test error: {e}")
        return False, f"Error: {str(e)}", 0