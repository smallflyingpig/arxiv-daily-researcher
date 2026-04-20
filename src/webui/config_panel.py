#!/usr/bin/env python3
"""
ArXiv Daily Researcher - Streamlit Config Panel

Usage:
    streamlit run src/webui/config_panel.py

    Docker:
    docker compose -f docker/docker-compose.yml --profile webui up -d config-panel
"""

import sys
from pathlib import Path

# Add src to path for config_io imports (src/webui/ -> src/ -> project root)
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))

import streamlit as st

from utils.config_io import (
    read_env,
    write_env,
    read_config_json,
    write_config_json,
    flatten_config_dict,
    build_config_dict,
    DEFAULT_ENV_PATH,
    DEFAULT_CONFIG_PATH,
)

from webui.styles import CUSTOM_CSS
from webui.tabs import llm, search, keywords, scoring, notifications, advanced, reports
from webui.i18n import t


# ==================== Page Config ====================

st.set_page_config(
    page_title="ArXiv Researcher - Config",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize language (default: Chinese)
if "lang" not in st.session_state:
    st.session_state["lang"] = "zh"


# ==================== Data Loading ====================


@st.cache_data(ttl=5)
def load_env():
    return read_env()


@st.cache_data(ttl=5)
def load_config():
    raw = read_config_json()
    return flatten_config_dict(raw) if raw else {}


def do_save():
    """Save all configuration to disk."""
    env_values = load_env()
    config_values = load_config()

    # Collect from all tabs
    env_updates = {}
    config_updates = {}

    # LLM tab -> env only
    env_updates.update(llm.collect(env_values, config_values))

    # Search tab -> config only
    config_updates.update(search.collect(env_values, config_values))

    # Keywords tab -> config only
    config_updates.update(keywords.collect(env_values, config_values))

    # Scoring tab -> config only
    config_updates.update(scoring.collect(env_values, config_values))

    # Notifications tab -> both env and config
    notif_env, notif_cfg = notifications.collect(env_values, config_values)
    env_updates.update(notif_env)
    config_updates.update(notif_cfg)

    # Advanced tab -> config only
    config_updates.update(advanced.collect(env_values, config_values))

    # Merge and write env
    merged_env = {**env_values, **env_updates}
    write_env(merged_env)

    # Merge and write config
    merged_config = {**config_values, **config_updates}
    config_dict = build_config_dict(**merged_config)
    write_config_json(config_dict)

    # Clear cache to reload fresh data
    st.cache_data.clear()


# ==================== Sidebar ====================


with st.sidebar:
    st.markdown("### ArXiv Daily Researcher")
    st.caption(t("sidebar_caption"))
    st.divider()

    if st.button(t("save_btn"), type="primary", use_container_width=True, key="save_btn"):
        try:
            do_save()
            st.success(t("save_success"))
        except Exception as e:
            st.error(t("save_failed") + str(e))

    if st.button(t("reload_btn"), use_container_width=True, key="reload_btn"):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # File status
    env_exists = DEFAULT_ENV_PATH.exists()
    cfg_exists = DEFAULT_CONFIG_PATH.exists()
    found = t("file_found")
    not_found = t("file_not_found")
    st.markdown(f"`.env`: {found if env_exists else not_found}")
    st.markdown(f"`config.json`: {found if cfg_exists else not_found}")

    st.divider()

    # Language toggle
    lang_label = t("lang_toggle")
    if st.button(lang_label, use_container_width=True, key="lang_btn"):
        st.session_state["lang"] = "en" if st.session_state["lang"] == "zh" else "zh"
        st.rerun()

    st.caption("v3.0 | Powered by Streamlit")


# ==================== Main Content ====================


st.markdown('<p class="main-header">ArXiv Daily Researcher</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="sub-header">{t("sub_header")}</p>',
    unsafe_allow_html=True,
)

# Load data
env_values = load_env()
config_values = load_config()

# Render tabs
tab_labels = [
    t("tab_llm"),
    t("tab_search"),
    t("tab_keywords"),
    t("tab_scoring"),
    t("tab_notifications"),
    t("tab_advanced"),
    t("tab_reports"),
]
tabs = st.tabs(tab_labels)

with tabs[0]:
    llm.render(env_values, config_values)

with tabs[1]:
    search.render(env_values, config_values)

with tabs[2]:
    keywords.render(env_values, config_values)

with tabs[3]:
    scoring.render(env_values, config_values)

with tabs[4]:
    notifications.render(env_values, config_values)

with tabs[5]:
    advanced.render(env_values, config_values)

with tabs[6]:
    reports.render(env_values, config_values)

# ==================== Footer ====================
st.divider()
st.markdown("""
<div style="text-align: center; padding: 0.5rem; font-size: 0.8rem; color: #7a8599;">
    🔬 ArXiv Daily Researcher Config Panel •
    <a href="http://172.19.17.30:8502" style="color: #00ff9f;">📖 打开报告阅读器</a>
</div>
""", unsafe_allow_html=True)
