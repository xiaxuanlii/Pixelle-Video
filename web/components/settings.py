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
System settings component for web UI

Web UI 高级系统底层设置交互面板（抽屉组件）。
封装了连接大厂 API 和本地 ComfyUI 配置的编辑、测试连接和全局生效功能。
"""

import streamlit as st

from web.i18n import tr, get_language
from web.utils.streamlit_helpers import safe_rerun
from pixelle_video.config import config_manager


def render_advanced_settings():
    """
    负责在顶部展示包含两栏（左侧 LLM，右侧画图生音大模型引擎）的设置折叠区。
    系统会嗅探全局配置的合法性：如果检测出必填的配置（如 LLM api_key）处于残缺或空白态，则会强制默认向用户展开面板。
    """
    is_configured = config_manager.validate()
    
    with st.expander(tr("settings.title"), expanded=not is_configured):
        # 2-column layout: LLM | ComfyUI, followed by direct media API providers.
        llm_col, comfyui_col = st.columns(2)
        
        # ====================================================================
        # Column 1: LLM Settings / 左列：大语言模型鉴权通道
        # ====================================================================
        with llm_col:
            with st.container(border=True):
                st.markdown(f"**{tr('settings.llm.title')}**")
                
                # 集成从系统中提取到的大模型接入预设 (Presets) 自动补全逻辑
                from pixelle_video.llm_presets import get_preset_names, get_preset, find_preset_by_base_url_and_model
                
                preset_names = get_preset_names() + ["Custom"]
                current_llm = config_manager.get_llm_config()
                
                # 回推目前用户的 Base URL 指向的厂商作为默认选择项目
                current_preset = find_preset_by_base_url_and_model(
                    current_llm["base_url"], 
                    current_llm["model"]
                )
                
                if current_preset:
                    default_index = preset_names.index(current_preset)
                else:
                    default_index = len(preset_names) - 1
                
                selected_preset = st.selectbox(
                    tr("settings.llm.quick_select"),
                    options=preset_names,
                    index=default_index,
                    help=tr("settings.llm.quick_select_help"),
                    key="llm_preset_select"
                )
                
                if selected_preset != "Custom":
                    preset_config = get_preset(selected_preset)
                    
                    if selected_preset == current_preset:
                        default_api_key = current_llm["api_key"]
                    else:
                        default_api_key = preset_config.get("default_api_key", "")
                    
                    default_base_url = preset_config.get("base_url", "")
                    default_model = preset_config.get("model", "")
                    
                    if preset_config.get("api_key_url"):
                        st.markdown(f"🔑 [{tr('settings.llm.get_api_key')}]({preset_config['api_key_url']})")
                else:
                    default_api_key = current_llm["api_key"]
                    default_base_url = current_llm["base_url"]
                    default_model = current_llm["model"]
                
                st.markdown("---")
                
                llm_api_key = st.text_input(
                    f"{tr('settings.llm.api_key')} *",
                    value=default_api_key,
                    type="password",
                    help=tr("settings.llm.api_key_help"),
                    key=f"llm_api_key_input_{selected_preset}"
                )
                
                llm_base_url = st.text_input(
                    f"{tr('settings.llm.base_url')} *",
                    value=default_base_url,
                    help=tr("settings.llm.base_url_help"),
                    key=f"llm_base_url_input_{selected_preset}"
                )
                
                # =============================== 模型探针探测与拉取 ===============================
                
                if "llm_loaded_models" not in st.session_state:
                    st.session_state.llm_loaded_models = []
                
                CUSTOM_MODEL_OPTION = f"✏️ {tr('settings.llm.custom_model')}"
                model_options = [CUSTOM_MODEL_OPTION] + st.session_state.llm_loaded_models
                
                if default_model in st.session_state.llm_loaded_models:
                    default_model_index = model_options.index(default_model)
                else:
                    default_model_index = 0
                
                model_col, load_col, test_col = st.columns([3, 1, 1])
                
                with model_col:
                    selected_model_option = st.selectbox(
                        f"{tr('settings.llm.model')} *",
                        options=model_options,
                        index=default_model_index,
                        help=tr("settings.llm.model_help"),
                        key=f"llm_model_select_{selected_preset}"
                    )
                
                with load_col:
                    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
                    load_clicked = st.button(
                        f"🔄 {tr('settings.llm.load_models')}",
                        help=tr("settings.llm.load_models_help"),
                        key="load_models_btn",
                        width="stretch"
                    )
                
                with test_col:
                    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
                    test_clicked = st.button(
                        f"🔌 {tr('settings.llm.test_connection')}",
                        help=tr("settings.llm.test_connection_help"),
                        key="test_llm_connection_btn",
                        width="stretch"
                    )
                
                if load_clicked:
                    if llm_api_key and llm_base_url:
                        try:
                            from pixelle_video.utils.llm_util import fetch_available_models
                            with st.spinner(tr("settings.llm.loading_models")):
                                models = fetch_available_models(llm_api_key, llm_base_url)
                                st.session_state.llm_loaded_models = models
                                st.success(tr("settings.llm.models_loaded").replace("{count}", str(len(models))))
                                safe_rerun()
                        except Exception as e:
                            st.error(tr("settings.llm.models_load_failed").replace("{error}", str(e)))
                    else:
                        st.warning(tr("status.llm_config_incomplete"))
                
                if test_clicked:
                    if llm_api_key and llm_base_url:
                        try:
                            from pixelle_video.utils.llm_util import test_llm_connection
                            with st.spinner(tr("settings.llm.loading_models")):
                                success, message, model_count = test_llm_connection(llm_api_key, llm_base_url)
                                if success:
                                    st.success(tr("settings.llm.connection_success").replace("{count}", str(model_count)))
                                else:
                                    st.error(tr("settings.llm.connection_failed").replace("{error}", message))
                        except Exception as e:
                            st.error(tr("settings.llm.connection_failed").replace("{error}", str(e)))
                    else:
                        st.warning(tr("status.llm_config_incomplete"))
                
                if selected_model_option == CUSTOM_MODEL_OPTION:
                    llm_model = st.text_input(
                        tr("settings.llm.custom_model_input"),
                        value=default_model,
                        help=tr("settings.llm.model_help"),
                        key=f"llm_custom_model_input_{selected_preset}"
                    )
                else:
                    llm_model = selected_model_option
        
        # ====================================================================
        # Column 2: ComfyUI Settings / 右列：并发引擎参数控制与配置
        # ====================================================================
        with comfyui_col:
            with st.container(border=True):
                st.markdown(f"**{tr('settings.comfyui.title')}**")
                
                comfyui_config = config_manager.get_comfyui_config()
                
                # 支持自备显卡及开源社群使用本地局域网内起的节点控制板
                st.markdown(f"**{tr('settings.comfyui.local_title')}**")
                url_col, key_col = st.columns(2)
                with url_col:
                    comfyui_url = st.text_input(
                        tr("settings.comfyui.comfyui_url"),
                        value=comfyui_config.get("comfyui_url", "http://127.0.0.1:8188"),
                        help=tr("settings.comfyui.comfyui_url_help"),
                        key="comfyui_url_input"
                    )
                with key_col:
                    comfyui_api_key = st.text_input(
                        tr("settings.comfyui.comfyui_api_key"),
                        value=comfyui_config.get("comfyui_api_key", ""),
                        type="password",
                        help=tr("settings.comfyui.comfyui_api_key_help"),
                        key="comfyui_api_key_input"
                    )
                
                if st.button(tr("btn.test_connection"), key="test_comfyui", width="stretch"):
                    try:
                        import requests
                        response = requests.get(f"{comfyui_url}/system_stats", timeout=5)
                        if response.status_code == 200:
                            st.success(tr("status.connection_success"))
                        else:
                            st.error(tr("status.connection_failed"))
                    except Exception as e:
                        st.error(f"{tr('status.connection_failed')}: {str(e)}")
                
                st.markdown("---")
                
                # 云算力使用策略与平台令牌配置
                st.markdown(f"**{tr('settings.comfyui.cloud_title')}**")
                runninghub_api_key = st.text_input(
                    tr("settings.comfyui.runninghub_api_key"),
                    value=comfyui_config.get("runninghub_api_key", ""),
                    type="password",
                    help=tr("settings.comfyui.runninghub_api_key_help"),
                    key="runninghub_api_key_input"
                )
                st.caption(
                    f"{tr('settings.comfyui.runninghub_hint')} "
                    f"[{tr('settings.comfyui.runninghub_get_api_key')}]"
                    f"(https://www.runninghub{'.cn' if get_language() == 'zh_CN' else '.ai'}/?inviteCode=bozpdlbj)"
                )
                
                limit_col, instance_col = st.columns(2)
                with limit_col:
                    runninghub_concurrent_limit = st.number_input(
                        tr("settings.comfyui.runninghub_concurrent_limit"),
                        min_value=1,
                        max_value=10,
                        value=comfyui_config.get("runninghub_concurrent_limit", 1),
                        help=tr("settings.comfyui.runninghub_concurrent_limit_help"),
                        key="runninghub_concurrent_limit_input"
                    )
                with instance_col:
                    # 设定请求云端高级服务器运算型号的标记开关逻辑
                    current_instance_type = comfyui_config.get("runninghub_instance_type") or ""
                    is_plus_enabled = current_instance_type == "plus"
                    instance_options = [
                        tr("settings.comfyui.runninghub_instance_24g"),
                        tr("settings.comfyui.runninghub_instance_48g"),
                    ]
                    runninghub_instance_type_display = st.selectbox(
                        tr("settings.comfyui.runninghub_instance_type"),
                        options=instance_options,
                        index=1 if is_plus_enabled else 0,
                        help=tr("settings.comfyui.runninghub_instance_type_help"),
                        key="runninghub_instance_type_input"
                    )
                    runninghub_48g_enabled = runninghub_instance_type_display == tr("settings.comfyui.runninghub_instance_48g")

        # ====================================================================
        # Direct API media providers
        # ====================================================================
        zh = get_language() == "zh_CN"
        api_cfg = config_manager.get_api_providers_config()
        common_cfg = api_cfg.get("common", {})
        openai_cfg = api_cfg.get("openai", {})
        dashscope_cfg = api_cfg.get("dashscope", {})
        ark_cfg = api_cfg.get("ark", {})
        kling_cfg = api_cfg.get("kling", {})
        default_api_base_urls = {
            "openai": "https://api.openai.com/v1",
            "dashscope": "https://dashscope.aliyuncs.com/api/v1",
            "ark": "https://ark.cn-beijing.volces.com/api/v3",
            "kling": "https://api-beijing.klingai.com",
        }

        with st.container(border=True):
            st.markdown("**🧩 API 媒体模型**" if zh else "**🧩 API Media Models**")
            st.caption(
                "用于直连图像/视频模型，不影响上方 LLM 与 ComfyUI/RunningHub 配置。"
                if zh
                else "Used for direct image/video model calls. This does not affect the LLM or ComfyUI/RunningHub settings above."
            )

            common_col, proxy_col = st.columns(2)
            with common_col:
                api_print_model_input = st.checkbox(
                    "打印模型请求参数" if zh else "Print model request parameters",
                    value=bool(common_cfg.get("print_model_input", False)),
                    help=(
                        "调试用。开启后会在终端打印发送给图像/视频模型的 prompt、模型名和输入文件路径。"
                        if zh
                        else "For debugging. Prints prompts, model names and input file paths sent to image/video models."
                    ),
                    key="api_media_print_model_input",
                )
            with proxy_col:
                api_local_proxy = st.text_input(
                    "本地代理（可选）" if zh else "Local proxy (optional)",
                    value=common_cfg.get("local_proxy", ""),
                    placeholder="http://127.0.0.1:9090",
                    help=(
                        "仅部分提供商会使用，例如 OpenAI 图像模型。留空表示不使用代理。"
                        if zh
                        else "Only used by some providers, such as OpenAI image models. Leave blank to disable."
                    ),
                    key="api_media_local_proxy",
                )

            st.markdown("---")

            provider_col1, provider_col2 = st.columns(2)
            with provider_col1:
                st.markdown("**OpenAI / GPT Image**")
                api_openai_use_proxy = st.checkbox(
                    "OpenAI 启用代理" if zh else "Use proxy for OpenAI",
                    value=bool(openai_cfg.get("use_proxy", False)),
                    key="api_media_openai_use_proxy",
                )
                api_openai_key = st.text_input(
                    "OpenAI API Key",
                    value=openai_cfg.get("api_key", ""),
                    type="password",
                    key="api_media_openai_key",
                )
                api_openai_base_url = st.text_input(
                    "OpenAI Base URL",
                    value=openai_cfg.get("base_url") or default_api_base_urls["openai"],
                    placeholder="https://api.openai.com/v1",
                    key="api_media_openai_base_url",
                )

                st.markdown("**DashScope / Wan / HappyHorse**")
                api_dashscope_use_proxy = st.checkbox(
                    "DashScope 启用代理" if zh else "Use proxy for DashScope",
                    value=bool(dashscope_cfg.get("use_proxy", False)),
                    key="api_media_dashscope_use_proxy",
                )
                api_dashscope_key = st.text_input(
                    "DashScope API Key",
                    value=dashscope_cfg.get("api_key", ""),
                    type="password",
                    key="api_media_dashscope_key",
                )
                api_dashscope_base_url = st.text_input(
                    "DashScope Base URL",
                    value=dashscope_cfg.get("base_url") or default_api_base_urls["dashscope"],
                    placeholder="https://dashscope.aliyuncs.com/api/v1",
                    key="api_media_dashscope_base_url",
                )

            with provider_col2:
                st.markdown("**Volcengine ARK / Seedream / Seedance**")
                api_ark_use_proxy = st.checkbox(
                    "ARK 启用代理" if zh else "Use proxy for ARK",
                    value=bool(ark_cfg.get("use_proxy", False)),
                    key="api_media_ark_use_proxy",
                )
                api_ark_key = st.text_input(
                    "ARK API Key",
                    value=ark_cfg.get("api_key", ""),
                    type="password",
                    key="api_media_ark_key",
                )
                api_ark_base_url = st.text_input(
                    "ARK Base URL",
                    value=ark_cfg.get("base_url") or default_api_base_urls["ark"],
                    placeholder="https://ark.cn-beijing.volces.com/api/v3",
                    key="api_media_ark_base_url",
                )

                st.markdown("**Kling AI / 可灵**")
                api_kling_use_proxy = st.checkbox(
                    "Kling 启用代理" if zh else "Use proxy for Kling",
                    value=bool(kling_cfg.get("use_proxy", False)),
                    key="api_media_kling_use_proxy",
                )
                api_kling_base_url = st.text_input(
                    "Kling Base URL",
                    value=kling_cfg.get("base_url") or default_api_base_urls["kling"],
                    placeholder="https://api-beijing.klingai.com",
                    key="api_media_kling_base_url",
                )
                api_kling_access_key = st.text_input(
                    "Kling Access Key",
                    value=kling_cfg.get("access_key", ""),
                    type="password",
                    key="api_media_kling_access_key",
                )
                api_kling_secret_key = st.text_input(
                    "Kling Secret Key",
                    value=kling_cfg.get("secret_key", ""),
                    type="password",
                    key="api_media_kling_secret_key",
                )
        
        # ====================================================================
        # Action Buttons / 全局确认保存并落地重置区域
        # ====================================================================
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(tr("btn.save_config"), width="stretch", key="save_config_btn"):
                try:
                    if not (llm_api_key and llm_base_url and llm_model):
                        st.error(tr("status.llm_config_incomplete"))
                    else:
                        config_manager.set_llm_config(llm_api_key, llm_base_url, llm_model)
                    
                    instance_type = "plus" if runninghub_48g_enabled else ""
                    config_manager.set_comfyui_config(
                        comfyui_url=comfyui_url if comfyui_url else None,
                        comfyui_api_key=comfyui_api_key if comfyui_api_key else None,
                        runninghub_api_key=runninghub_api_key if runninghub_api_key else None,
                        runninghub_concurrent_limit=int(runninghub_concurrent_limit),
                        runninghub_instance_type=instance_type
                    )

                    # Save direct image/video API provider configuration.
                    config_manager.set_api_provider_config("common", {
                        "print_model_input": bool(api_print_model_input),
                        "local_proxy": api_local_proxy or "",
                    })
                    config_manager.set_api_provider_config("openai", {
                        "api_key": api_openai_key or "",
                        "base_url": api_openai_base_url or "",
                        "use_proxy": bool(api_openai_use_proxy),
                    })
                    config_manager.set_api_provider_config("dashscope", {
                        "api_key": api_dashscope_key or "",
                        "base_url": api_dashscope_base_url or "",
                        "use_proxy": bool(api_dashscope_use_proxy),
                    })
                    config_manager.set_api_provider_config("ark", {
                        "api_key": api_ark_key or "",
                        "base_url": api_ark_base_url or "",
                        "use_proxy": bool(api_ark_use_proxy),
                    })
                    config_manager.set_api_provider_config("kling", {
                        "base_url": api_kling_base_url or "",
                        "access_key": api_kling_access_key or "",
                        "secret_key": api_kling_secret_key or "",
                        "use_proxy": bool(api_kling_use_proxy),
                    })
                    
                    if llm_api_key and llm_base_url and llm_model:
                        # 只有在主心骨未破损时真正覆写 JSON YAML 等结构落盘文件
                        config_manager.save()
                        st.success(tr("status.config_saved"))
                        safe_rerun()
                except Exception as e:
                    st.error(f"{tr('status.save_failed')}: {str(e)}")
        
        with col2:
            if st.button(tr("btn.reset_config"), width="stretch", key="reset_config_btn"):
                from pixelle_video.config.schema import PixelleVideoConfig
                config_manager.config = PixelleVideoConfig()
                config_manager.save()
                st.success(tr("status.config_reset"))
                safe_rerun()
