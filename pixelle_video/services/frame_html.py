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
HTML-based Frame Generator Service

基于 HTML 模板的单帧画面渲染服务。
利用 Playwright（无头浏览器技术）将 HTML/CSS 排版渲染为静态的 PNG 帧图像。
这种方案使得视频的排版和字幕样式极其灵活，完全兼容 Web 前端的 CSS 动效和布局能力。

Linux 环境运行要求:
    - 必须安装 fontconfig 字体配置包。
    - 建议安装基本的中英文字体（如 fonts-liberation, fonts-noto-cjk 等），否则渲染出的文字可能是豆腐块。
    
    Ubuntu/Debian 依赖安装指令: sudo apt-get install -y fontconfig fonts-liberation fonts-noto-cjk
    CentOS/RHEL 依赖安装指令: sudo yum install -y fontconfig liberation-fonts google-noto-cjk-fonts
    
    Playwright 浏览器环境安装指令: playwright install --with-deps chromium
"""

import asyncio
import os
import re
import tempfile
import uuid
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from pixelle_video.utils.template_util import parse_template_size


class HTMLFrameGenerator:
    """
    基于 HTML 技术的帧画面渲染器。
    
    负责加载 HTML 模板，进行变量和参数的替换注入，最终调用 Playwright 
    启动无头 Chromium 浏览器，将整个网页截图保存下来，形成带有透明通道或底图的完美排版帧。
    
    使用示例:
        >>> generator = HTMLFrameGenerator("templates/modern.html")
        >>> frame_path = await generator.generate_frame(
        ...     title="为什么阅读如此重要",
        ...     text="阅读能在你的大脑中建立新的神经通路...",
        ...     image="/path/to/generated_background.png",
        ...     ext={"accent_color": "#ff0000", "show_logo": True}
        ... )
    """
    
    _browser = None
    _playwright = None
    _browser_loop = None

    def __init__(self, template_path: str):
        """
        初始化帧画面生成器。
        
        Args:
            template_path: HTML 模板文件所在路径 (例如: "templates/1080x1920/default.html")。
        """
        self.template_path = template_path
        self.template = self._load_template(template_path)
        
        # Parse video size from template path
        self.width, self.height = parse_template_size(template_path)
        
        self._check_linux_dependencies()
        logger.debug(f"Loaded HTML template: {template_path} (size: {self.width}x{self.height})")
    
    
    def _check_linux_dependencies(self):
        """自动检查当前 Linux 宿主系统中关于字体的依赖项（防止中文字符乱码）"""
        if os.name != 'posix':
            return
        
        try:
            import subprocess
            
            result = subprocess.run(
                ['fc-list'], 
                capture_output=True, 
                timeout=2
            )
            
            if result.returncode != 0:
                logger.warning(
                    "fontconfig not found or not working properly. "
                    "Install with: sudo apt-get install -y fontconfig fonts-liberation fonts-noto-cjk"
                )
            elif not result.stdout:
                logger.warning(
                    "No fonts detected by fontconfig. "
                    "Install fonts with: sudo apt-get install -y fonts-liberation fonts-noto-cjk"
                )
            else:
                logger.debug(f"Fontconfig detected {len(result.stdout.splitlines())} fonts")
                
        except FileNotFoundError:
            logger.warning(
                "fontconfig (fc-list) not found on system. "
                "Install with: sudo apt-get install -y fontconfig"
            )
        except Exception as e:
            logger.debug(f"Could not check fontconfig status: {e}")
    
    def _load_template(self, template_path: str) -> str:
        """从磁盘加载 HTML 文件为内存字符串"""
        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"Template loaded: {len(content)} chars")
        return content
    
    def _parse_media_size_from_meta(self) -> tuple[Optional[int], Optional[int]]:
        """
        通过 BeautifulSoup 提取模板内部对预期嵌套媒体尺寸的约束要求（meta 标签声明）。
        
        例如:
        <meta name="template:media-width" content="1024">
        
        Returns:
            Tuple[Optional[int], Optional[int]]: 解析出的宽度和高度。
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(self.template, 'html.parser')
            
            width_meta = soup.find('meta', attrs={'name': 'template:media-width'})
            height_meta = soup.find('meta', attrs={'name': 'template:media-height'})
            
            if width_meta and height_meta:
                width = int(width_meta.get('content', 0))
                height = int(height_meta.get('content', 0))
                
                if width > 0 and height > 0:
                    logger.debug(f"Found media size in meta tags: {width}x{height}")
                    return width, height
            
            return None, None
            
        except Exception as e:
            logger.warning(f"Failed to parse media size from meta tags: {e}")
            return None, None
    
    def get_media_size(self) -> tuple[int, int]:
        """
        获取为了适配该 HTML 模板排版所必须生成的图像/视频底层素材尺寸。
        
        Returns:
            Tuple[int, int]: 宽度和高度（像素），如果未标记则使用兜底值 1024x1024。
        """
        media_width, media_height = self._parse_media_size_from_meta()
        
        if media_width and media_height:
            return media_width, media_height
        
        logger.warning(f"No media size meta tags found in template {self.template_path}, using fallback 1024x1024")
        return 1024, 1024
    
    def parse_template_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        解析模板源代码中内嵌的自定义占位符（可供用户修改的高级排版配置）。
        
        支持的自定义 DSL 语法: {{param:type=default}}
        - {{param}} -> string text 类型，无默认值。
        - {{param=value}} -> text 类型，有默认值。
        - {{param:type}} -> 强制声明类型。
        - {{param:type=value}} -> 同时声明类型和初始默认值。
        
        Returns:
            Dict: 用于给前端构建动态控制表单的字典描述。
        """
        PRESET_PARAMS = {'title', 'text', 'image', 'index'}
        
        PARAM_PATTERN = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-z]+))?(?:=([^}]+))?\}\}'
        
        params = {}
        
        for match in re.finditer(PARAM_PATTERN, self.template):
            param_name = match.group(1)
            param_type = match.group(2) or 'text'
            default_value = match.group(3)
            
            # 跳过系统的内置必填保留字
            if param_name in PRESET_PARAMS:
                continue
            
            if param_name in params:
                continue
            
            if param_type not in {'text', 'number', 'color', 'bool'}:
                logger.warning(f"Unknown parameter type '{param_type}' for '{param_name}', defaulting to 'text'")
                param_type = 'text'
            
            parsed_default = self._parse_default_value(param_type, default_value)
            
            params[param_name] = {
                'type': param_type,
                'default': parsed_default,
                'label': param_name,
            }
        
        if params:
            logger.debug(f"Parsed {len(params)} custom parameter(s) from template: {list(params.keys())}")
        
        return params
    
    def _parse_default_value(self, param_type: str, value_str: Optional[str]) -> Any:
        """根据探测出的声明类型转换默认值字符串为 Python 数据类型"""
        if value_str is None:
            return {
                'text': '',
                'number': 0,
                'color': '#000000',
                'bool': False,
            }.get(param_type, '')
        
        if param_type == 'number':
            try:
                if '.' in value_str:
                    return float(value_str)
                else:
                    return int(value_str)
            except ValueError:
                logger.warning(f"Invalid number value '{value_str}', using 0")
                return 0
        
        elif param_type == 'bool':
            return value_str.lower() in {'true', '1', 'yes', 'on'}
        
        elif param_type == 'color':
            if value_str.startswith('#'):
                return value_str
            else:
                return f'#{value_str}'
        
        else:  # text
            return value_str
    
    def _replace_parameters(self, html: str, values: Dict[str, Any]) -> str:
        """
        使用实际的参数值来正式替换 HTML 字符串内的所有 DSL 占位符变量。
        
        Args:
            html: HTML 模板字符串。
            values: 上层业务传来的有效参数字典。
        
        Returns:
            str: 已经注入好参数值的标准 HTML 文本。
        """
        PARAM_PATTERN = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-z]+))?(?:=([^}]+))?\}\}'
        
        def replacer(match):
            param_name = match.group(1)
            param_type = match.group(2) or 'text'
            default_value_str = match.group(3)
            
            if param_name in values:
                value = values[param_name]
                if isinstance(value, bool):
                    return 'true' if value else 'false'
                return str(value) if value is not None else ''
            
            elif default_value_str:
                return default_value_str
            
            else:
                return ''
        
        return re.sub(PARAM_PATTERN, replacer, html)

    @classmethod
    async def _ensure_browser(cls):
        """Lazily initialize a shared Playwright browser instance / 懒加载初始化并在整个应用级别共享一个 Playwright 实例（减小开销）"""
        current_loop = asyncio.get_running_loop()
        browser_usable = (
            cls._browser is not None
            and cls._browser_loop is current_loop
            and cls._browser.is_connected()
        )

        if not browser_usable:
            if cls._browser is not None and cls._browser_loop is not current_loop:
                logger.warning(
                    "Detected cross-loop Playwright browser reuse attempt; "
                    "recreating browser for current event loop"
                )

            cls._browser = None
            cls._playwright = None
            from playwright.async_api import async_playwright
            cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                ]
            )
            cls._browser_loop = current_loop
            logger.debug("Initialized Playwright Chromium browser")
        return cls._browser

    @classmethod
    def _discard_browser_references(cls):
        """Drop stale Playwright objects that belong to another event loop."""
        cls._browser = None
        cls._playwright = None
        cls._browser_loop_id = None

    @classmethod
    async def _reset_browser(cls):
        """Best-effort reset for stale or broken Playwright connections."""
        if cls._browser:
            try:
                if cls._browser.is_connected():
                    await asyncio.wait_for(cls._browser.close(), timeout=5)
            except Exception as e:
                logger.debug(f"Ignoring error while closing stale browser: {e}")
            finally:
                cls._browser = None

        if cls._playwright:
            try:
                await asyncio.wait_for(cls._playwright.stop(), timeout=5)
            except Exception as e:
                logger.debug(f"Ignoring error while stopping stale Playwright: {e}")
            finally:
                cls._playwright = None
                cls._browser_loop_id = None

    @classmethod
    async def close_browser(cls):
        """关闭挂载在类属性上的无头浏览器（应用退出时调用以释放系统资源）"""
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
            cls._browser_loop = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
            logger.debug("Playwright browser closed")

    async def generate_frame(
        self,
        title: str,
        text: str,
        image: str,
        ext: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        渲染合并，产生包含全透明通道（或者有底图）的 PNG 素材图片供视频工具流叠加。
        
        Args:
            title: 视频的总标题。
            text: 当前分镜应当显示的文字内容（旁白/字幕）。
            image: AI生成的原始素材图（或占位图）本地路径或 URI。
            ext: 用户提供的附加替换字典变量集合。
            output_path: 指定的图片输出位置（如果未指定系统会自动在 output 中随机一个）。
        
        Returns:
            str: 成功渲染产生的帧画面图片路径。
        """
        # 将传入的系统本地相对文件路径规范转换为支持被 Chromium 处理的标准的 URI 格式
        if image and not image.startswith(('http://', 'https://', 'data:', 'file://')):
            image_path = Path(image)
            if not image_path.is_absolute():
                image_path = Path.cwd() / image
            
            if not image_path.exists():
                logger.warning(f"Image file not found: {image_path}")
            else:
                image = image_path.as_uri()
                logger.debug(f"Converted image path to: {image}")
        
        context = {
            "title": title,
            "text": text,
            "image": image,
        }
        
        if ext:
            context.update(ext)
        
        html = self._replace_parameters(self.template, context)

        if output_path is None:
            from pixelle_video.utils.os_util import get_output_path
            output_filename = f"frame_{uuid.uuid4().hex[:16]}.png"
            output_path = get_output_path(output_filename)
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        logger.debug(f"Rendering HTML template to {output_path} (size: {self.width}x{self.height})")
        tmp_html_path = None
        page = None
        try:
            try:
                # 申请无头浏览器页面实例
                browser = await self._ensure_browser()
                page = await browser.new_page(
                    viewport={'width': self.width, 'height': self.height},
                    device_scale_factor=1,
                )
            except Exception as e:
                logger.warning(f"Playwright browser connection failed, restarting once: {e}")
                await self._reset_browser()
                browser = await self._ensure_browser()
                page = await browser.new_page(
                    viewport={'width': self.width, 'height': self.height},
                    device_scale_factor=1,
                )

            try:
                # 关键：我们必须把内存中替换好的 html 代码以物理文件的形式暂存到系统磁盘中。
                # 并且要使用 file:// 的 URL 协议要求浏览器导航到这个文件！
                # 这是因为浏览器具有严格的跨源隔离策略。如果单纯通过 set_content() 传递 HTML 字符串，
                # 那么内部的资源图片（基于 file:// 协议）将全部因为 CORS 安全被阻止加载。
                fd, tmp_html_path = tempfile.mkstemp(suffix='.html', prefix='pv_frame_')
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                await page.goto(Path(tmp_html_path).as_uri(), wait_until='networkidle')
                # 执行截图并允许剥离页面的 Background，保留原生的 CSS 透明色以便能在动态视频上透出来
                await page.screenshot(path=output_path, type='png', omit_background=True)
            finally:
                if page:
                    await page.close()
                if tmp_html_path and os.path.exists(tmp_html_path):
                    os.unlink(tmp_html_path)
            
            logger.info(f"Frame generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.exception("Failed to render HTML template")
            raise RuntimeError(
                f"HTML rendering failed: {type(e).__name__}: {e}"
            ) from e

