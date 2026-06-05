import asyncio
import sys
import os
from pathlib import Path

# 将项目根目录添加到系统路径，确保能导入 pixelle_video 模块
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from pixelle_video.service import PixelleVideoCore
from pixelle_video.utils.content_generators import generate_narrations_from_topic
from loguru import logger

# 配置日志级别为 DEBUG 以便看到详细过程
logger.remove()
logger.add(sys.stderr, level="DEBUG")

async def test_narration_generation():
    print("\n" + "="*50)
    print("🚀 开始调试: 视频脚本生成模块")
    print("="*50 + "\n")

    # 1. 初始化核心引擎
    # 它会自动加载项目根目录下的 config.yaml 配置文件
    print("Step 1: 正在初始化 PixelleVideoCore...")
    try:
        core = PixelleVideoCore()
        # ！！！关键点：必须调用 initialize() 才会真正创建 llm, tts 等服务对象 ！！！
        await core.initialize()
        
        llm_service = core.llm
        if llm_service is None:
            raise ValueError("llm_service 依然为 None，请检查 config.yaml 是否配置了 LLM 部分。")
            
        print("✅ 核心引擎初始化成功\n")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print("请检查项目目录下是否存在有效的 config.yaml 且 LLM 配置正确。")
        return

    # 2. 准备测试参数
    test_topic = "如何增加被动收入"
    n_scenes = 5
    
    print(f"Step 2: 准备调用 generate_narrations_from_topic")
    print(f"   - 主题: {test_topic}")
    print(f"   - 分镜数量: {n_scenes}")
    print("   - 正在请求 LLM，请稍候...\n")

    # 3. 执行目标函数
    try:
        results = await generate_narrations_from_topic(
            llm_service=llm_service,
            topic=test_topic,
            n_scenes=n_scenes,
            min_words=10,
            max_words=50
        )

        # 4. 展示生成结果
        print("="*50)
        print("✨ LLM 生成脚本成功:")
        print("="*50)
        for i, narration in enumerate(results, 1):
            print(f"【分镜 {i}】")
            print(f"内容: {narration}")
            print("-" * 20)
        print("="*50)

    except Exception as e:
        print(f"❌ 执行出错: {str(e)}")
        print("\n提示: 如果报 API 错误，请检查您的网络连接或 config.yaml 中的 LLM API Key 是否有效。")

if __name__ == "__main__":
    asyncio.run(test_narration_generation())
