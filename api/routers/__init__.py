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
API Routers

API 路由包的初始化文件。
集中导入并重命名了所有子模块中定义的 APIRouter 实例，
方便在主应用文件 (`api/app.py`) 中以 `app.include_router()` 的形式统一挂载。
"""

from api.routers.health import router as health_router
from api.routers.llm import router as llm_router
from api.routers.tts import router as tts_router
from api.routers.image import router as image_router
from api.routers.content import router as content_router
from api.routers.video import router as video_router
from api.routers.tasks import router as tasks_router
from api.routers.files import router as files_router
from api.routers.resources import router as resources_router
from api.routers.frame import router as frame_router

__all__ = [
    "health_router",      # 健康检查路由
    "llm_router",         # 大语言模型对话路由
    "tts_router",         # 语音合成路由
    "image_router",       # 图片生成路由
    "content_router",     # 智能内容(标题/旁白/提示词)生成路由
    "video_router",       # 视频合成生成路由
    "tasks_router",       # 异步任务管理路由
    "files_router",       # 静态文件访问路由
    "resources_router",   # 可用资源查询路由
    "frame_router",       # 模板单帧渲染路由
]

