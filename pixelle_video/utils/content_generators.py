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
Content generation utility functions

内容生成工具函数模块。
提供一组纯函数（无状态），用于封装与大语言模型（LLM）的各种交互场景
（如生成标题、发散旁白、根据脚本切割分镜、推断画面提示词等）。
这些函数可以在不同的生成流水线中被复用。
"""

import json
import re
from typing import List, Optional, Literal

from loguru import logger


async def generate_title(
    llm_service,
    content: str,
    strategy: Literal["auto", "direct", "llm"] = "auto",
    max_length: int = 15
) -> str:
    """
    根据给定的内容提取或生成视频标题。
    
    Args:
        llm_service: LLM 服务实例。
        content: 源内容（主题或完整剧本）。
        strategy: 生成策略：
            - "auto": 自动决定（如果内容足够短则直接使用，否则调用 LLM 生成，默认值）。
            - "direct": 直接使用源内容（如果超长将被截断）。
            - "llm": 强制调用大模型对内容进行总结提炼。
        max_length: 允许的最大标题长度（默认 15 个字符）。
    
    Returns:
        str: 最终生成的精简标题。
    """
    if strategy == "direct":
        content = content.strip()
        return content[:max_length] if len(content) > max_length else content
    
    if strategy == "auto":
        if len(content.strip()) <= 15:
            return content.strip()
        # Fall through to LLM
    
    # Use LLM to generate title
    from pixelle_video.prompts import build_title_generation_prompt
    
    # Pass max_length to prompt so LLM knows the character limit
    prompt = build_title_generation_prompt(content, max_length=max_length)
    response = await llm_service(prompt, temperature=0.7, max_tokens=50)
    
    # Clean up response
    title = response.strip()
    
    # Remove quotes if present
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1]
    if title.startswith("'") and title.endswith("'"):
        title = title[1:-1]
    
    # Remove trailing punctuation
    title = title.rstrip('.,!?;:\'"')
    
    # Safety: if still over limit, truncate smartly
    if len(title) > max_length:
        # Try to truncate at word boundary
        truncated = title[:max_length]
        last_space = truncated.rfind(' ')
        
        # Only use word boundary if it's not too far back (at least 60% of max_length)
        if last_space > max_length * 0.6:
            title = truncated[:last_space]
        else:
            title = truncated
        
        # Remove any trailing punctuation after truncation
        title = title.rstrip('.,!?;:\'"')
    
    logger.debug(f"Generated title: '{title}' (length: {len(title)})")
    return title


async def generate_narrations_from_topic(
    llm_service,
    topic: str,
    n_scenes: int = 5,
    min_words: int = 5,
    max_words: int = 20,
    max_retries: int = 3
) -> List[str]:
    """
    使用大模型根据简短的主题发散生成多个分镜的旁白。
    
    Args:
        llm_service: LLM 服务实例。
        topic: 用于生成旁白的主题或核心立意。
        n_scenes: 期望生成的分镜/旁白段数。
        min_words: 每段旁白的最小字数限制。
        max_words: 每段旁白的最大字数限制。
        max_retries: 解析失败或截断时的最大重试次数。
    
    Returns:
        List[str]: 生成的旁白文本列表。
    """
    from pixelle_video.prompts import build_topic_narration_prompt
    
    logger.info(f"Generating {n_scenes} narrations from topic: {topic}")
    
    prompt = build_topic_narration_prompt(
        topic=topic,
        n_storyboard=n_scenes,
        min_words=min_words,
        max_words=max_words
    )
    
    for attempt in range(1, max_retries + 1):
        try:
            response = await llm_service(
                prompt=prompt,
                temperature=0.8,
                max_tokens=2000
            )
            
            logger.debug(f"LLM response: {response[:200]}...")
            
            # Parse JSON
            result = _parse_json(response)
            
            if "narrations" not in result:
                raise ValueError("Invalid response format: missing 'narrations' key")
            
            narrations = result["narrations"]
            
            # Validate count
            if len(narrations) > n_scenes:
                logger.warning(f"Got {len(narrations)} narrations, taking first {n_scenes}")
                narrations = narrations[:n_scenes]
            elif len(narrations) < n_scenes:
                raise ValueError(f"Expected {n_scenes} narrations, got only {len(narrations)}")
            
            logger.info(f"Generated {len(narrations)} narrations successfully")
            return narrations
            
        except Exception as e:
            logger.warning(f"✗ Narration generation attempt {attempt} failed: {e}")
            if attempt >= max_retries:
                raise
            logger.info(f"Retrying narration generation...")


async def generate_narrations_from_content(
    llm_service,
    content: str,
    n_scenes: int = 5,
    min_words: int = 5,
    max_words: int = 20
) -> List[str]:
    """
    使用大模型将用户提供的长篇内容拆分和改写为适合视频朗读的旁白。
    
    Args:
        llm_service: LLM 服务实例。
        content: 用户提供的源内容材料。
        n_scenes: 期望拆分出的旁白段数。
        min_words: 每段旁白的最小字数限制。
        max_words: 每段旁白的最大字数限制。
    
    Returns:
        List[str]: 拆分改写后的旁白文本列表。
    """
    from pixelle_video.prompts import build_content_narration_prompt
    
    logger.info(f"Generating {n_scenes} narrations from content ({len(content)} chars)")
    
    prompt = build_content_narration_prompt(
        content=content,
        n_storyboard=n_scenes,
        min_words=min_words,
        max_words=max_words
    )
    
    response = await llm_service(
        prompt=prompt,
        temperature=0.8,
        max_tokens=2000
    )
    
    # Parse JSON
    result = _parse_json(response)
    
    if "narrations" not in result:
        raise ValueError("Invalid response format: missing 'narrations' key")
    
    narrations = result["narrations"]
    
    # Validate count
    if len(narrations) > n_scenes:
        logger.warning(f"Got {len(narrations)} narrations, taking first {n_scenes}")
        narrations = narrations[:n_scenes]
    elif len(narrations) < n_scenes:
        raise ValueError(f"Expected {n_scenes} narrations, got only {len(narrations)}")
    
    logger.info(f"Generated {len(narrations)} narrations successfully")
    return narrations


async def split_narration_script(
    script: str,
    split_mode: Literal["paragraph", "line", "sentence"] = "paragraph",
) -> List[str]:
    """
    根据预定的符号或规则，将用户提供的固定脚本直接切分为各个分镜的旁白（不使用大模型）。
    
    Args:
        script: 固定的旁白长文本脚本。
        split_mode: 拆分策略：
            - "paragraph": 按双换行符 (\\n\\n) 拆分（推荐用于段落结构的剧本）。
            - "line": 按单换行符 (\\n) 拆分（每一行作为一个分镜旁白）。
            - "sentence": 按句子结尾标点符号（如 。.!?！？）进行断句拆分。
    
    Returns:
        List[str]: 拆分后的旁白段落列表。
    """
    logger.info(f"Splitting script (mode={split_mode}, length={len(script)} chars)")
    
    narrations = []
    
    if split_mode == "paragraph":
        # Split by double newline (paragraph mode)
        # Preserve single newlines within paragraphs
        paragraphs = re.split(r'\n\s*\n', script)
        for para in paragraphs:
            # Only strip leading/trailing whitespace, preserve internal newlines
            cleaned = para.strip()
            if cleaned:
                narrations.append(para)
        logger.info(f"✅ Split script into {len(narrations)} segments (by paragraph)")
    
    elif split_mode == "line":
        # Split by single newline (original behavior)
        narrations = [line.strip() for line in script.split('\n') if line.strip()]
        logger.info(f"✅ Split script into {len(narrations)} segments (by line)")
    
    elif split_mode == "sentence":
        # Split by sentence-ending punctuation
        # Supports Chinese (。！？) and English (.!?)
        # Use regex to split while keeping sentences intact
        cleaned = re.sub(r'\s+', ' ', script.strip())
        # Split on sentence-ending punctuation, keeping the punctuation with the sentence
        sentences = re.split(r'(?<=[。.!?！？])\s*', cleaned)
        narrations = [s.strip() for s in sentences if s.strip()]
        logger.info(f"✅ Split script into {len(narrations)} segments (by sentence)")
    
    else:
        # Fallback to line mode
        logger.warning(f"Unknown split_mode '{split_mode}', falling back to 'line'")
        narrations = [line.strip() for line in script.split('\n') if line.strip()]
    
    # Log statistics
    if narrations:
        lengths = [len(s) for s in narrations]
        logger.info(f"   Min: {min(lengths)} chars, Max: {max(lengths)} chars, Avg: {sum(lengths)//len(lengths)} chars")
    
    return narrations


async def generate_image_prompts(
    llm_service,
    narrations: List[str],
    min_words: int = 30,
    max_words: int = 60,
    batch_size: int = 10,
    max_retries: int = 3,
    progress_callback: Optional[callable] = None
) -> List[str]:
    """
    根据已有的旁白列表，利用大模型批量推理生成对应的画面提示词（用于生图）。
    包含自动分批处理和错误重试机制。
    
    Args:
        llm_service: LLM 服务实例。
        narrations: 旁白文本列表。
        min_words: 每个提示词的最小长度。
        max_words: 每个提示词的最大长度。
        batch_size: 每批次同时交给大模型处理的最大旁白数量（默认 10）。
        max_retries: 每批次允许失败重试的最大次数（默认 3）。
        progress_callback: 进度的回调函数 (completed, total, message)。
    
    Returns:
        List[str]: 画面提示词列表（基础提示词，未加上全局的前缀修饰语）。
    """
    from pixelle_video.prompts import build_image_prompt_prompt
    
    logger.info(f"Generating image prompts for {len(narrations)} narrations (batch_size={batch_size})")
    
    # Split narrations into batches
    batches = [narrations[i:i + batch_size] for i in range(0, len(narrations), batch_size)]
    logger.info(f"Split into {len(batches)} batches")
    
    all_prompts = []
    
    # Process each batch
    for batch_idx, batch_narrations in enumerate(batches, 1):
        logger.info(f"Processing batch {batch_idx}/{len(batches)} ({len(batch_narrations)} narrations)")
        
        # Retry logic for this batch
        for attempt in range(1, max_retries + 1):
            try:
                # Generate prompts for this batch
                prompt = build_image_prompt_prompt(
                    narrations=batch_narrations,
                    min_words=min_words,
                    max_words=max_words
                )
                
                response = await llm_service(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=8192
                )
                
                logger.debug(f"Batch {batch_idx} attempt {attempt}: LLM response length: {len(response)} chars")
                
                # Parse JSON
                result = _parse_json(response)
                
                if "image_prompts" not in result:
                    raise KeyError("Invalid response format: missing 'image_prompts'")
                
                batch_prompts = result["image_prompts"]
                
                # Validate count
                if len(batch_prompts) != len(batch_narrations):
                    error_msg = (
                        f"Batch {batch_idx} prompt count mismatch (attempt {attempt}/{max_retries}):\n"
                        f"  Expected: {len(batch_narrations)} prompts\n"
                        f"  Got: {len(batch_prompts)} prompts"
                    )
                    logger.warning(error_msg)
                    
                    if attempt < max_retries:
                        logger.info(f"Retrying batch {batch_idx}...")
                        continue
                    else:
                        raise ValueError(error_msg)
                
                # Success!
                logger.info(f"✅ Batch {batch_idx} completed successfully ({len(batch_prompts)} prompts)")
                all_prompts.extend(batch_prompts)
                
                # Report progress
                if progress_callback:
                    progress_callback(
                        len(all_prompts),
                        len(narrations),
                        f"Batch {batch_idx}/{len(batches)} completed"
                    )
                
                break
                
            except json.JSONDecodeError as e:
                logger.error(f"Batch {batch_idx} JSON parse error (attempt {attempt}/{max_retries}): {e}")
                if attempt >= max_retries:
                    raise
                logger.info(f"Retrying batch {batch_idx}...")
    
    logger.info(f"✅ Generated {len(all_prompts)} image prompts carry prefix")
    return all_prompts


async def generate_video_prompts(
    llm_service,
    narrations: List[str],
    min_words: int = 30,
    max_words: int = 60,
    batch_size: int = 10,
    max_retries: int = 3,
    progress_callback: Optional[callable] = None
) -> List[str]:
    """
    根据已有的旁白列表，利用大模型批量推理生成对应的视频动态描述提示词（用于生视频）。
    包含自动分批处理和错误重试机制。
    
    Args:
        llm_service: LLM 服务实例。
        narrations: 旁白文本列表。
        min_words: 每个动态提示词的最小长度。
        max_words: 每个动态提示词的最大长度。
        batch_size: 每批次同时交给大模型处理的最大旁白数量（默认 10）。
        max_retries: 每批次允许失败重试的最大次数（默认 3）。
        progress_callback: 进度的回调函数。
    
    Returns:
        List[str]: 视频动态画面提示词列表。
    """
    from pixelle_video.prompts.video_generation import build_video_prompt_prompt
    
    logger.info(f"Generating video prompts for {len(narrations)} narrations (batch_size={batch_size})")
    
    # Split narrations into batches
    batches = [narrations[i:i + batch_size] for i in range(0, len(narrations), batch_size)]
    logger.info(f"Split into {len(batches)} batches")
    
    all_prompts = []
    
    # Process each batch
    for batch_idx, batch_narrations in enumerate(batches, 1):
        logger.info(f"Processing batch {batch_idx}/{len(batches)} ({len(batch_narrations)} narrations)")
        
        # Retry logic for this batch
        for attempt in range(1, max_retries + 1):
            try:
                # Generate prompts for this batch
                prompt = build_video_prompt_prompt(
                    narrations=batch_narrations,
                    min_words=min_words,
                    max_words=max_words
                )
                
                response = await llm_service(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=8192
                )
                
                logger.debug(f"Batch {batch_idx} attempt {attempt}: LLM response length: {len(response)} chars")
                
                # Parse JSON
                result = _parse_json(response)
                
                if "video_prompts" not in result:
                    raise KeyError("Invalid response format: missing 'video_prompts'")
                
                batch_prompts = result["video_prompts"]
                
                # Validate batch result
                if len(batch_prompts) != len(batch_narrations):
                    raise ValueError(
                        f"Prompt count mismatch: expected {len(batch_narrations)}, got {len(batch_prompts)}"
                    )
                
                # Success - add to all_prompts
                all_prompts.extend(batch_prompts)
                logger.info(f"✓ Batch {batch_idx} completed: {len(batch_prompts)} video prompts")
                
                # Report progress
                if progress_callback:
                    completed = len(all_prompts)
                    total = len(narrations)
                    progress_callback(completed, total, f"Batch {batch_idx}/{len(batches)} completed")
                
                break  # Success, move to next batch
            
            except Exception as e:
                logger.warning(f"✗ Batch {batch_idx} attempt {attempt} failed: {e}")
                if attempt >= max_retries:
                    raise
                logger.info(f"Retrying batch {batch_idx}...")
    
    logger.info(f"✅ Generated {len(all_prompts)} video prompts")
    return all_prompts


def _parse_json(text: str) -> dict:
    """
    高兼容性的内部 JSON 解析器，使用 json_repair 库修复由于大模型输出的不规范格式。
    Args:
        text: 包含目标 JSON 的原始文本。
        
    Returns:
        解析后的 JSON 字典对象。
        
    Raises:
        json.JSONDecodeError: 所有的提取尝试都失败时抛出。
        ValueError: 当传入的文本为空时抛出，通常是因为 LLM 调用彻底失败或网络截断。
    """
    if not text or not text.strip():
        raise ValueError("LLM returned an empty response. Please check your API key, network connection, or balance.")
        
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n(.*?)\n```$", r"\1", text, flags=re.DOTALL | re.IGNORECASE).strip()
        
    # Try direct parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.debug(f"Standard JSON parse failed, attempting repair. Error: {e}")
        try:
            import json_repair
            repaired_json = json_repair.repair_json(text, return_objects=True)
            if repaired_json is not None:
                 # Check if the returned object is actually a string instead of dict/list.
                 # json_repair sometimes returns a string if it's completely unparsable,
                 # but typically we expect a dict here.
                 if isinstance(repaired_json, (dict, list)):
                     return repaired_json
                 else:
                     raise json.JSONDecodeError("json_repair returned a non-object", text, 0)
            else:
                 raise json.JSONDecodeError("json_repair could not repair the JSON", text, 0)
        except Exception as repair_error:
            error_msg = f"No valid JSON found and repair failed: {repair_error}"
            logger.error(f"{error_msg}. Raw text: {text}")
            raise json.JSONDecodeError(error_msg, text, 0) from e


