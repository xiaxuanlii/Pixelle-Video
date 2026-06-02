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
Content generation endpoints

此模块定义了与智能内容生成（大语言模型辅助创作）相关的 API 路由端点。
包含了长文本拆分生成旁白、根据旁白生成画面提示词，以及智能提取标题的接口。
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.schemas.content import (
    NarrationGenerateRequest,
    NarrationGenerateResponse,
    ImagePromptGenerateRequest,
    ImagePromptGenerateResponse,
    TitleGenerateRequest,
    TitleGenerateResponse,
)
from pixelle_video.utils.content_generators import (
    generate_narrations_from_topic,
    generate_image_prompts,
    generate_title,
)

# 创建带有 "/content" 前缀的 APIRouter，并在 Swagger 中归类为 "Content Generation"
router = APIRouter(prefix="/content", tags=["Content Generation"])


@router.post("/narration", response_model=NarrationGenerateResponse)
async def generate_narration(
    request: NarrationGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    旁白生成端点。
    
    使用大语言模型（LLM）将输入的长文本或主题拆分并改写成多个连贯的短句（旁白片段），
    每个片段将对应视频中的一个分镜画面。
    
    请求参数说明：
    - **text**: 原始文本或要生成内容的主题。
    - **n_scenes**: 期望拆分生成的分镜/旁白总数。
    - **min_words**: 每个旁白片段的最小字数。
    - **max_words**: 每个旁白片段的最大字数。
    
    返回：
        NarrationGenerateResponse: 包含生成的旁白文本列表（字符串数组）。
    """
    try:
        logger.info(f"Generating {request.n_scenes} narrations from text")
        
        # Call narration generator utility function / 调用工具类执行实际的生成逻辑
        narrations = await generate_narrations_from_topic(
            llm_service=pixelle_video.llm,
            topic=request.text,
            n_scenes=request.n_scenes,
            min_words=request.min_words,
            max_words=request.max_words
        )
        
        return NarrationGenerateResponse(
            narrations=narrations
        )
        
    except Exception as e:
        logger.error(f"Narration generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image-prompt", response_model=ImagePromptGenerateResponse)
async def generate_image_prompt(
    request: ImagePromptGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    画面提示词生成端点。
    
    使用大语言模型（LLM）根据已经生成的旁白列表，为每个旁白推断出最适合表现其内容的画面描述（Prompt）。
    生成的 Prompt 将直接投喂给绘图引擎（如 Stable Diffusion / ComfyUI）生成对应的视频帧。
    
    请求参数说明：
    - **narrations**: 已生成的旁白列表。
    - **min_words**: 每个画面提示词的最小长度。
    - **max_words**: 每个画面提示词的最大长度。
    
    返回：
        ImagePromptGenerateResponse: 包含生成的画面提示词列表（与旁白一一对应）。
    """
    try:
        logger.info(f"Generating image prompts for {len(request.narrations)} narrations")
        
        # Call image prompt generator utility function / 调用工具类执行提示词推断逻辑
        image_prompts = await generate_image_prompts(
            llm_service=pixelle_video.llm,
            narrations=request.narrations,
            min_words=request.min_words,
            max_words=request.max_words
        )
        
        return ImagePromptGenerateResponse(
            image_prompts=image_prompts
        )
        
    except Exception as e:
        logger.error(f"Image prompt generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/title", response_model=TitleGenerateResponse)
async def generate_title_endpoint(
    request: TitleGenerateRequest,
    pixelle_video: PixelleVideoDep
):
    """
    标题生成端点。
    
    使用大语言模型（LLM）对输入的原始文本进行总结和提炼，生成一个吸引人的短标题。
    
    请求参数说明：
    - **text**: 原始长文本。
    - **style**: (可选) 期望的标题风格，如“引人入胜”、“学术”、“悬疑”等。
    
    返回：
        TitleGenerateResponse: 包含生成的单个标题字符串。
    """
    try:
        logger.info("Generating title from text")
        
        # Call title generator utility function / 调用工具类执行标题提炼逻辑
        # 这里指定了 strategy="llm" 来强制使用 AI 模型生成，而不是简单的截取
        title = await generate_title(
            llm_service=pixelle_video.llm,
            content=request.text,
            strategy="llm"
        )
        
        return TitleGenerateResponse(
            title=title
        )
        
    except Exception as e:
        logger.error(f"Title generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

