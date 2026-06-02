# Pixelle-Video 配置文件使用指南

本文档旨在说明 Pixelle-Video 项目中各个配置文件的作用及其关键配置项，帮助开发者和用户快速完成环境搭建。

## 1. 核心业务配置

### `config.yaml` / `config.example.yaml`
这是项目的**主配置文件**，控制着 AI 模型、视频渲染引擎和排版模板的全局行为。
- **作用**：定义 LLM (大语言模型) API、ComfyUI 服务地址、TTS (语音合成) 工作流以及默认视频模板。
- **配置重点**：
  - `llm`: 填写 API Key 和 Base URL。支持 OpenAI、阿里通义千问 (Qwen)、DeepSeek 等。
  - `comfyui`: 
    - `comfyui_url`: 本地部署的 ComfyUI 地址。
    - `runninghub_api_key`: 如果使用云端算力 (RunningHub)，在此填写 API Key。
  - `template.default_template`: 设置系统默认使用的 HTML 渲染模板。
- **注意**：正式运行时请将 `config.example.yaml` 复制为 `config.yaml`。`config.yaml` 已被 Git 忽略，请勿提交包含密钥的配置文件。

---

## 2. Python 依赖与包管理

### `pyproject.toml`
这是现代 Python 项目的标准配置文件。
- **作用**：
  - 定义项目元数据（名称、版本、作者、许可证）。
  - 列出项目运行所需的所有核心依赖库（如 `streamlit`, `fastapi`, `moviepy`, `playwright`）。
  - 配置开发工具设置（如 `ruff` 代码检查器的规则）。
  - 定义命令行入口点（`pixelle-video` 命令）。
- **工具支持**：兼容 `uv`, `pip`, `poetry` 等包管理工具。

### `uv.lock`
- **作用**：由 `uv` 工具自动生成的锁定文件。
- **内容**：记录了当前环境下所有依赖包的**精确版本号**及其哈希值，确保在不同机器上安装的依赖环境完全一致。
- **注意**：请勿手动修改此文件。

---

## 3. 容器化与环境隔离

### `Dockerfile`
- **作用**：定义项目的 Docker 镜像构建规则。包含基础环境选择、系统组件（如 `ffmpeg`）安装、依赖下载及启动命令。

### `docker-compose.yml`
- **作用**：多容器编排文件。
- **用途**：一键启动包含 API 服务、Web UI 的完整环境，并配置端口映射、磁盘卷挂载（持久化 output 目录）以及环境变量。

### `.dockerignore`
- **作用**：在构建 Docker 镜像时排除不必要的文件（如 `venv`, `.git`, `output` 等），以缩小镜像体积并保护隐私。

---

## 4. 辅助开发配置

### `mkdocs.yml`
- **作用**：文档中心配置文件。
- **用途**：定义项目在线文档的结构、导航菜单、主题样式（Material theme）以及使用的 Markdown 插件。

### `requirements-docs.txt`
- **作用**：专门用于构建 MkDocs 文档的 Python 依赖列表。

### `.devcontainer/devcontainer.json`
- **作用**：VS Code 开发容器配置。
- **用途**：允许开发者在一致的 Docker 容器中打开项目，自动配置好 Python 环境、VS Code 扩展和环境变量，实现“开箱即用”的开发体验。

### `.gitignore`
- **作用**：Git 忽略规则。
- **用途**：防止临时文件、环境变量密钥 (`config.yaml`, `.env`)、生成产物 (`output/`) 以及 Python 虚拟环境被提交到版本库。

---

## 5. 打包与分发

### `packaging/windows/requirements.txt`
- **作用**：专门针对 Windows 平台打包工具（如封装成 .exe）所需的依赖列表。

---

## 修改建议
- **初次运行**：请务必先配置 `config.yaml`。
- **增加功能**：如需添加新库，请修改 `pyproject.toml` 的 `dependencies` 部分。
- **修改样式**：如需更改文档外观，请修改 `mkdocs.yml`。
