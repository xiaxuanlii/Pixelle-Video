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
Edge TTS Utility - Temporarily not used

开源 Edge TTS (微软边缘浏览器文本转语音引擎) 交互工具。
目前已作为 `local` 模式的备用引擎保留在此。
"""

import asyncio
import ssl
import random
import certifi
import edge_tts as edge_tts_sdk
from edge_tts.exceptions import NoAudioReceived
from loguru import logger
from aiohttp import WSServerHandshakeError, ClientResponseError


# 使用 certifi 提供的 SSL 证书集以防止某些环境下 SSL 握手失败
_USE_CERTIFI_SSL = True

# 针对微软接口严格的限流和偶发性 401 鉴权错误的重试配置
_RETRY_COUNT = 5           # 默认最大重试次数
_RETRY_BASE_DELAY = 1.0     # 指数退避的基准延迟（秒）
_MAX_RETRY_DELAY = 10.0     # 允许的最大重试间隔（秒）

# 并发限流控制配置
_REQUEST_DELAY = 0.5        # 两次请求之间的强制最小安全间隔（秒）
_MAX_CONCURRENT_REQUESTS = 3  # 全局允许的最大并发请求数

# 用于在事件循环中全局控制限流的信号量
_request_semaphore = None
_semaphore_loop = None


def _get_request_semaphore():
    """获取或初始化当前事件循环绑定的限流信号量"""
    global _request_semaphore, _semaphore_loop
    
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        # 如果没有运行中的事件循环则当场创建一个新的信号量
        return asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
    
    # 保证信号量是属于当前事件循环的（防止跨线程或跨事件循环时引发异常）
    if _request_semaphore is None or _semaphore_loop != current_loop:
        _request_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
        _semaphore_loop = current_loop
    
    return _request_semaphore


async def edge_tts(
    text: str,
    voice: str = "[Chinese] zh-CN Yunjian",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    output_path: str = None,
    retry_count: int = _RETRY_COUNT,
    retry_base_delay: float = _RETRY_BASE_DELAY,
) -> bytes:
    """
    调用微软 Edge 浏览器内置的免费 TTS 接口生成语音。
    
    此服务完全免费且无需 API Key。包含超过 100 种语言和 400 种音色。
    自带支持指数退避的重试机制，以优雅应对网络波动和被微软服务器限流拦截的情况。
    
    Args:
        text: 待转换的文本。
        voice: 音色标识名。
        rate: 语速偏移量 (格式如: +0%, +50%, -20%)。
        volume: 音量偏移量 (格式如: +0%, +50%, -20%)。
        pitch: 音高偏移量 (格式如: +0Hz, +10Hz, -5Hz)。
        output_path: (可选) 如果提供，生成完毕后自动写入到此本地文件。
        retry_count: 遇到网络或认证失败时的最大重试次数。
        retry_base_delay: 每次重试等待时间的递增基数。
    
    Returns:
        bytes: MP3 格式的音频二进制数据。
        
    常用的中文音色:
    - [Chinese] zh-CN Yunjian (男声, 默认, 偏解说)
    - [Chinese] zh-CN Xiaoxiao (女声)
    - [Chinese] zh-CN Yunxi (男声)
    - [Chinese] zh-CN Xiaoyi (女声)
    """
    logger.debug(f"Calling Edge TTS with voice: {voice}, rate: {rate}, retry_count: {retry_count}")
    
    # Use semaphore to limit concurrent requests
    request_semaphore = _get_request_semaphore()
    async with request_semaphore:
        # Add a small random delay before each request to avoid rate limiting
        pre_delay = _REQUEST_DELAY + random.uniform(0, 0.3)
        logger.debug(f"Waiting {pre_delay:.2f}s before request (rate limiting)")
        await asyncio.sleep(pre_delay)
        
        last_error = None
        
        # Retry loop
        for attempt in range(retry_count + 1):  # +1 because first attempt is not a retry
            if attempt > 0:
                # Exponential backoff with jitter
                # delay = base * (2 ^ attempt) + random jitter
                exponential_delay = retry_base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, retry_base_delay)
                retry_delay = min(exponential_delay + jitter, _MAX_RETRY_DELAY)
                
                logger.info(f"🔄 Retrying Edge TTS (attempt {attempt + 1}/{retry_count + 1}) after {retry_delay:.2f}s delay...")
                await asyncio.sleep(retry_delay)
            
            try:
                # Create communicate instance with certifi SSL context
                if _USE_CERTIFI_SSL:
                    if attempt == 0:  # Only log info once
                        logger.debug("Using certifi SSL certificates for secure Edge TTS connection")
                    # Create SSL context with certifi bundle
                    import certifi
                    ssl_context = ssl.create_default_context(cafile=certifi.where())
                else:
                    ssl_context = None
                
                # Create communicate instance
                communicate = edge_tts_sdk.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                )
                
                # Collect audio chunks
                audio_chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
                
                audio_data = b"".join(audio_chunks)
                
                if attempt > 0:
                    logger.success(f"✅ Retry succeeded on attempt {attempt + 1}")
                
                logger.info(f"Generated {len(audio_data)} bytes of audio data")
                
                # Save to file if output_path is provided
                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    logger.info(f"Audio saved to: {output_path}")
                
                return audio_data
            
            except (WSServerHandshakeError, ClientResponseError) as e:
                # Network/authentication errors - retry
                last_error = e
                error_code = getattr(e, 'status', 'unknown')
                error_msg = str(e)
                
                # Log more detailed information for 401 errors
                if error_code == 401 or '401' in error_msg:
                    logger.warning(f"⚠️  Edge TTS 401 Authentication Error (attempt {attempt + 1}/{retry_count + 1})")
                    logger.debug(f"Error details: {error_msg}")
                    logger.debug(f"This is usually caused by rate limiting. Will retry with exponential backoff...")
                else:
                    logger.warning(f"⚠️  Edge TTS error (attempt {attempt + 1}/{retry_count + 1}): {error_code} - {e}")
                
                if attempt >= retry_count:
                    # Last attempt failed
                    logger.error(f"❌ All {retry_count + 1} attempts failed. Last error: {error_code}")
                    raise
                # Otherwise, continue to next retry
            
            except NoAudioReceived as e:
                # NoAudioReceived is often a temporary issue - retry with longer delay
                last_error = e
                logger.warning(f"⚠️  Edge TTS NoAudioReceived (attempt {attempt + 1}/{retry_count + 1})")
                logger.debug(f"This is usually a temporary Microsoft service issue. Will retry with longer delay...")
                
                if attempt >= retry_count:
                    logger.error(f"❌ All {retry_count + 1} attempts failed due to NoAudioReceived")
                    raise
                # Add extra delay for NoAudioReceived errors
                await asyncio.sleep(2.0)
            
            except Exception as e:
                # Other errors - don't retry, raise immediately
                logger.error(f"Edge TTS error (non-retryable): {type(e).__name__} - {e}")
                raise
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        else:
            raise RuntimeError("Edge TTS failed without error (unexpected)")


def get_audio_duration(audio_path: str) -> float:
    """
    基于探测机制安全地获取音频文件的确切时长。
    
    Args:
        audio_path: 音频物理文件路径。
    
    Returns:
        float: 时长（秒）。
    """
    try:
        # Try using ffmpeg-python
        import ffmpeg
        probe = ffmpeg.probe(audio_path)
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        logger.warning(f"Failed to get audio duration: {e}, using estimate")
        # Fallback: estimate based on file size (very rough)
        import os
        file_size = os.path.getsize(audio_path)
        # Assume ~16kbps for MP3, so 2KB per second
        estimated_duration = file_size / 2000
        return max(1.0, estimated_duration)  # At least 1 second


async def list_voices(locale: str = None, retry_count: int = _RETRY_COUNT, retry_base_delay: float = _RETRY_BASE_DELAY) -> list[str]:
    """
    枚举查询并返回 Edge TTS 支持的所有可用音色。
    
    内置自动重试与并发限流保护以防止查询被拒。
    
    Args:
        locale: (可选) 指定按国家语言前缀过滤（如 "zh-CN", "en-US"）。
        retry_count: 最大重试次数。
        retry_base_delay: 基础退避时间。
    
    Returns:
        List[str]: 获取到的系统音色标识列表。
    """
    logger.debug(f"Fetching Edge TTS voices, locale filter: {locale}, retry_count: {retry_count}")
    
    # Use semaphore to limit concurrent requests
    request_semaphore = _get_request_semaphore()
    async with request_semaphore:
        # Add a small random delay before each request to avoid rate limiting
        pre_delay = _REQUEST_DELAY + random.uniform(0, 0.3)
        logger.debug(f"Waiting {pre_delay:.2f}s before request (rate limiting)")
        await asyncio.sleep(pre_delay)
        
        last_error = None
        
        # Retry loop
        for attempt in range(retry_count + 1):
            if attempt > 0:
                # Exponential backoff with jitter
                exponential_delay = retry_base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, retry_base_delay)
                retry_delay = min(exponential_delay + jitter, _MAX_RETRY_DELAY)
                
                logger.info(f"🔄 Retrying list voices (attempt {attempt + 1}/{retry_count + 1}) after {retry_delay:.2f}s delay...")
                await asyncio.sleep(retry_delay)
            
            try:
                # Get all voices (edge-tts handles SSL internally)
                voices = await edge_tts_sdk.list_voices()
                
                # Filter by locale if specified
                if locale:
                    voices = [v for v in voices if v["Locale"].startswith(locale)]
                
                # Extract voice IDs (ShortName)
                voice_ids = [voice["ShortName"] for voice in voices]
                
                if attempt > 0:
                    logger.success(f"✅ Retry succeeded on attempt {attempt + 1}")
                
                logger.info(f"Found {len(voice_ids)} voices" + (f" for locale '{locale}'" if locale else ""))
                return voice_ids
            
            except (WSServerHandshakeError, ClientResponseError) as e:
                # Network/authentication errors - retry
                last_error = e
                error_code = getattr(e, 'status', 'unknown')
                error_msg = str(e)
                
                # Log more detailed information for 401 errors
                if error_code == 401 or '401' in error_msg:
                    logger.warning(f"⚠️  Edge TTS 401 Authentication Error (list_voices attempt {attempt + 1}/{retry_count + 1})")
                    logger.debug(f"Error details: {error_msg}")
                    logger.debug(f"This is usually caused by rate limiting. Will retry with exponential backoff...")
                else:
                    logger.warning(f"⚠️  List voices error (attempt {attempt + 1}/{retry_count + 1}): {error_code} - {e}")
                
                if attempt >= retry_count:
                    logger.error(f"❌ All {retry_count + 1} attempts failed. Last error: {error_code}")
                    raise
            
            except Exception as e:
                # Other errors - don't retry, raise immediately
                logger.error(f"List voices error (non-retryable): {type(e).__name__} - {e}")
                raise
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        else:
            raise RuntimeError("List voices failed without error (unexpected)")
