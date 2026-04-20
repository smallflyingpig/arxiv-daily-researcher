#!/usr/bin/env python3
"""
ArXiv Daily Researcher - Report Viewer

独立报告阅读页面 - Space-Age Science Magazine 美学
修复: (1)侧边栏文字颜色可见 (2)分筛选器 (3)HTML嵌入页面Tab

Usage:
    streamlit run src/webui/report_viewer.py --server.port 8502
"""

import sys
import re
from pathlib import Path

# Add src to path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "src"))

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# ==================== Page Config ====================
st.set_page_config(
    page_title="ArXiv Research Reader",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== CSS Styles ====================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=Libre+Baskerville:wght@400;700&family=DM+Sans:wght@400;500;600;700&family=Crimson+Pro:wght@400;600&display=swap');

:root {
    --ink-deep: #1a1f3c;
    --ink-medium: #2d3555;
    --paper-cream: #f5f0e6;
    --paper-warm: #ebe4d4;
    --paper-vellum: #faf8f3;
    --coral-fire: #e85d75;
    --coral-soft: #f28b9d;
    --gold-glint: #d4a574;
    --gold-bright: #e8c49a;
    --cyan-glow: #4ecdc4;
    --navy-shadow: #0d1321;
    --display-font: 'Playfair Display', serif;
    --body-font: 'Libre Baskerville', Georgia, serif;
    --ui-font: 'DM Sans', sans-serif;
    --reading-font: 'Crimson Pro', serif;
}

.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, var(--paper-vellum) 0%, var(--paper-cream) 15%, var(--paper-warm) 85%, var(--paper-cream) 100%);
}

.block-container {
    max-width: 900px;
    margin: 0 auto;
    padding: 64px 48px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(135deg, var(--navy-shadow) 0%, var(--ink-deep) 40%, var(--ink-medium) 100%);
    border-right: 4px solid var(--gold-glint);
    min-width: 300px;
    max-width: 350px;
}

[data-testid="stSidebar"] * {
    font-family: var(--ui-font);
}

[data-testid="stSidebar"] h3 {
    font-family: var(--display-font);
    color: var(--gold-bright) !important;
    font-size: 1.3rem;
}

/* Sidebar info panel - high contrast */
.sidebar-info-panel {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--gold-glint);
    border-radius: 6px;
    padding: 1rem;
    margin: 1rem 0;
}

.sidebar-info-panel p {
    font-family: var(--ui-font);
    font-size: 0.85rem;
    color: var(--paper-cream) !important;
    margin: 0.3rem 0;
    line-height: 1.6;
}

.sidebar-info-panel strong {
    color: var(--gold-bright) !important;
}

.sidebar-info-label {
    color: var(--paper-cream) !important;
    opacity: 0.85;
}

/* Selectboxes in sidebar */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(245, 240, 230, 0.12);
    border: 1px solid rgba(212, 165, 116, 0.4);
}

[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
    border-color: var(--coral-fire);
}

[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: var(--paper-cream) !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] button {
    font-family: var(--ui-font);
    background: transparent;
    border: 1px solid rgba(212, 165, 116, 0.6);
    color: var(--gold-bright) !important;
    border-radius: 4px;
}

[data-testid="stSidebar"] button:hover {
    background: rgba(232, 93, 117, 0.25);
    border-color: var(--coral-fire);
    color: var(--paper-vellum) !important;
}

[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(135deg, var(--coral-fire) 0%, var(--coral-soft) 100%);
    border: none;
    color: var(--paper-vellum) !important;
}

/* Main content typography */
.stMarkdown h1 {
    font-family: var(--display-font);
    font-size: 2.8rem;
    font-weight: 700;
    color: var(--ink-deep);
    line-height: 1.2;
    margin-bottom: 1rem;
}

.stMarkdown h2 {
    font-family: var(--display-font);
    font-size: 1.6rem;
    font-weight: 600;
    color: var(--ink-medium);
    margin-top: 2rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--coral-fire);
    padding-bottom: 0.5rem;
}

.stMarkdown h3 {
    font-family: var(--ui-font);
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--ink-deep);
    margin-top: 1.5rem;
}

.stMarkdown p, .stMarkdown li {
    font-family: var(--reading-font);
    font-size: 1.05rem;
    color: var(--ink-deep);
    line-height: 1.75;
}

/* Details/Summary styling */
.stMarkdown details {
    background: var(--paper-vellum);
    border: 1px solid var(--gold-glint);
    border-radius: 4px;
    margin: 1rem 0;
    padding: 0.5rem 1rem;
}

.stMarkdown details summary {
    font-family: var(--ui-font);
    font-weight: 600;
    color: var(--ink-medium);
    cursor: pointer;
    padding: 0.5rem;
}

.stMarkdown details summary:hover {
    color: var(--coral-fire);
}

/* Tip blocks - use gold/coral instead of cyan */
.tip-block {
    background: linear-gradient(135deg, rgba(212, 165, 116, 0.12) 0%, rgba(212, 165, 116, 0.06) 100%);
    border: 1px solid var(--gold-glint);
    border-left: 4px solid var(--gold-glint);
    border-radius: 4px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
}

.tip-title {
    font-family: var(--ui-font);
    font-weight: 700;
    font-size: 0.9rem;
    color: var(--coral-fire);
    margin-bottom: 0.5rem;
}

.tip-title::before {
    content: '💡 ';
}

.tip-content {
    font-family: var(--reading-font);
    font-size: 1rem;
    color: var(--ink-deep);
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
}

/* Tables */
.stMarkdown table {
    font-family: var(--ui-font);
    border-collapse: collapse;
    border: 1px solid var(--gold-glint);
    width: 100%;
    margin: 1rem 0;
}

.stMarkdown th {
    background: var(--ink-deep);
    color: var(--gold-bright);
    font-weight: 600;
    padding: 0.75rem;
    border-bottom: 2px solid var(--coral-fire);
}

.stMarkdown td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--paper-warm);
    color: var(--ink-deep);
}

/* Info bar */
.info-bar {
    font-family: var(--ui-font);
    font-size: 0.85rem;
    color: var(--ink-medium);
    padding: 0.5rem 1rem;
    background: var(--paper-warm);
    border-radius: 4px;
    margin: 1rem 0;
    display: flex;
    gap: 1rem;
}

.source-badge {
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    padding: 4px 10px;
    background: var(--ink-deep);
    color: var(--gold-bright);
    border-radius: 3px;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    font-family: var(--ui-font);
    font-weight: 600;
    color: var(--ink-medium);
    background: var(--paper-warm);
    border-radius: 4px;
}

.stTabs [aria-selected="true"] {
    background: var(--ink-deep);
    color: var(--gold-bright) !important;
}

/* Divider */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, var(--coral-fire) 20%, var(--gold-glint) 80%, transparent 100%);
    margin: 2rem 0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--paper-warm); }
::-webkit-scrollbar-thumb { background: var(--coral-fire); border-radius: 5px; }

/* Sidebar toggle button - HIGH VISIBILITY */
[data-testid="collapsedControl"] {
    background-color: var(--gold-bright) !important;
    border: 2px solid var(--coral-fire) !important;
    border-radius: 0 12px 12px 0 !important;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.4) !important;
}

[data-testid="collapsedControl"] svg {
    color: var(--navy-shadow) !important;
    fill: var(--navy-shadow) !important;
}

[data-testid="collapsedControl"]:hover {
    background-color: var(--coral-fire) !important;
    box-shadow: 3px 3px 15px rgba(0,0,0,0.5) !important;
}

/* When sidebar is expanded, the collapse button */
button[kind="header"] {
    background: var(--gold-bright) !important;
    color: var(--navy-shadow) !important;
    border: 2px solid var(--coral-fire) !important;
    border-radius: 0 12px 12px 0;
    padding: 0.75rem 1rem;
    font-weight: 700;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.4);
}

button[kind="header"]:hover {
    background: var(--coral-fire) !important;
    color: var(--paper-vellum) !important;
}

/* Sidebar link */
.sidebar-link {
    display: block;
    text-align: center;
    font-family: var(--ui-font);
    font-size: 0.85rem;
    color: var(--coral-soft);
    padding: 0.5rem;
    margin-top: 1rem;
    border-top: 1px solid rgba(212, 165, 116, 0.3);
}

.sidebar-link a {
    color: var(--gold-bright);
    text-decoration: none;
    font-weight: 600;
}

.sidebar-link a:hover {
    color: var(--coral-soft);
}

/* End mark - centered */
.end-mark {
    text-align: center;
    font-family: var(--display-font);
    font-size: 1.1rem;
    color: var(--ink-medium);
    margin-top: 3rem;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ==================== Header ====================
st.markdown("""
<h1 style="margin-top: 0;">◈ ArXiv Research Reader</h1>
<p style="font-family: var(--ui-font); font-size: 0.8rem; letter-spacing: 0.1em; color: var(--ink-medium);">
    SPACE-AGE SCIENCE MAGAZINE • 探索知识前沿
</p>
""", unsafe_allow_html=True)

# ==================== Report Discovery ====================
REPORTS_DIR = _project_root / "data" / "reports"

def find_reports():
    """Find all available reports."""
    reports = []

    # Daily research HTML
    daily_html = REPORTS_DIR / "daily_research" / "html"
    if daily_html.exists():
        for src_dir in daily_html.iterdir():
            if src_dir.is_dir():
                source = src_dir.name.upper()
                for f in sorted(src_dir.glob("*.html"), reverse=True):
                    name = f.stem
                    m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})$", name)
                    if m:
                        date = m.group(1)
                        time = m.group(2).replace("-", ":")
                    else:
                        date = "未知日期"
                        time = ""
                    reports.append({
                        "path": f,
                        "type": "HTML",
                        "source": source,
                        "date": date,
                        "time": time,
                        "category": "日报",
                        "sort_date": date if date != "未知日期" else "0000-00-00",
                    })

    # Daily research Markdown
    daily_md = REPORTS_DIR / "daily_research" / "markdown"
    if daily_md.exists():
        for src_dir in daily_md.iterdir():
            if src_dir.is_dir():
                source = src_dir.name.upper()
                for f in sorted(src_dir.glob("*.md"), reverse=True):
                    name = f.stem
                    m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})$", name)
                    if m:
                        date = m.group(1)
                        time = m.group(2).replace("-", ":")
                    else:
                        date = "未知日期"
                        time = ""
                    reports.append({
                        "path": f,
                        "type": "MD",
                        "source": source,
                        "date": date,
                        "time": time,
                        "category": "日报",
                        "sort_date": date if date != "未知日期" else "0000-00-00",
                    })

    # Trend research
    trend_html = REPORTS_DIR / "trend_research" / "html"
    if trend_html.exists():
        for kw_dir in trend_html.iterdir():
            if kw_dir.is_dir():
                slug = kw_dir.name
                for f in sorted(kw_dir.glob("*.html"), reverse=True):
                    name = f.stem
                    m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})$", name)
                    if m:
                        date_range = f"{m.group(1)} → {m.group(2)}"
                    else:
                        date_range = name
                    reports.append({
                        "path": f,
                        "type": "HTML",
                        "source": slug,
                        "date": date_range,
                        "time": "",
                        "category": "趋势",
                        "sort_date": m.group(1) if m else "0000-00-00",
                    })

    # Keyword trend
    kw_html = REPORTS_DIR / "keyword_trend" / "html"
    if kw_html.exists():
        for f in sorted(kw_html.glob("*.html"), reverse=True):
            name = f.stem
            m = re.search(r"(\d{4}-\d{2}-\d{2})$", name)
            date = m.group(1) if m else "未知"
            reports.append({
                "path": f,
                "type": "HTML",
                "source": "关键词",
                "date": date,
                "time": "",
                "category": "趋势",
                "sort_date": date if m else "0000-00-00",
            })

    reports.sort(key=lambda x: (x["sort_date"], x["category"]), reverse=True)
    return reports

# ==================== Markdown Processing ====================
def process_markdown(content: str) -> str:
    """Process markdown for proper rendering."""

    # !!! tip TL;DR blocks
    tip_pattern = r'!!!\s+tip\s+.*?TL;DR\s*\n((?:\s{4,}.*?\n)+)'

    def replace_tip(match):
        tip_content = match.group(1)
        lines = [line.strip() for line in tip_content.strip().split('\n')]
        content_text = ' '.join(lines) if len(lines) == 1 else '\n'.join(lines)
        return f'''<div class="tip-block">
<div class="tip-title">TL;DR 摘要</div>
<div class="tip-content">{content_text}</div>
</div>'''

    content = re.sub(tip_pattern, replace_tip, content)

    # Alternative tip format
    content = re.sub(
        r'!!!\s+tip\s+(.*?)\n\n',
        r'<div class="tip-block"><div class="tip-title">💡 \1</div></div>\n\n',
        content
    )

    return content

# ==================== Sidebar with Separate Filters ====================
with st.sidebar:
    st.markdown("<h3>◆ 报告目录</h3>", unsafe_allow_html=True)

    reports = find_reports()

    if not reports:
        st.info("暂无报告")
        st.stop()

    # Extract unique values for each filter
    dates = sorted(set(r["date"] for r in reports), reverse=True)
    sources = sorted(set(r["source"] for r in reports))
    types = sorted(set(r["type"] for r in reports))
    categories = sorted(set(r["category"] for r in reports))

    st.markdown("<p style='font-size: 0.75rem; color: var(--paper-cream); opacity: 0.85; margin-bottom: 1rem;'>筛选条件</p>", unsafe_allow_html=True)

    # Three separate filters
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.selectbox("日期", dates, key="filter_date")
    with col2:
        selected_source = st.selectbox("来源", sources, key="filter_source")

    selected_type = st.selectbox("格式", types, key="filter_type")

    st.divider()

    # Filter reports
    filtered = [r for r in reports
                if r["date"] == selected_date
                and r["source"] == selected_source
                and r["type"] == selected_type]

    if not filtered:
        st.warning("无匹配报告，请调整筛选条件")
        selected = reports[0]  # fallback to first
    else:
        # If multiple matches, let user pick
        if len(filtered) > 1:
            time_options = [r["time"] if r["time"] else "无时间" for r in filtered]
            selected_time_idx = st.selectbox(
                "时间版本",
                range(len(filtered)),
                format_func=lambda i: time_options[i],
                key="filter_time"
            )
            selected = filtered[selected_time_idx]
        else:
            selected = filtered[0]

    # Report info panel with visible colors
    st.markdown(f"""
    <div class="sidebar-info-panel">
        <p><span class="sidebar-info-label">报告类型:</span> <strong>{selected['category']}</strong></p>
        <p><span class="sidebar-info-label">数据来源:</span> <strong>{selected['source']}</strong></p>
        <p><span class="sidebar-info-label">生成日期:</span> <strong>{selected['date']}</strong></p>
        <p><span class="sidebar-info-label">文件格式:</span> <strong>{selected['type']}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Download
    file_content = selected['path'].read_text(encoding='utf-8')
    st.download_button(
        "📥 下载报告",
        data=file_content,
        file_name=selected['path'].name,
        mime="text/markdown" if selected['type'] == "MD" else "text/html",
        use_container_width=True,
    )

    st.divider()

    # Navigation link
    st.markdown("""
    <div class="sidebar-link">
        🔬 <a href="http://172.19.17.30:8501">返回配置面板</a>
    </div>
    """, unsafe_allow_html=True)

# ==================== Report Display with Tabs ====================
st.markdown(f"""
<div class="info-bar">
    <span class="source-badge">{selected['source']}</span>
    <span>◆</span>
    <span>{selected['category']}报告</span>
    <span>◆</span>
    <span>{selected['date']}</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# Use tabs for HTML/MD display
if selected['type'] == 'HTML':
    tab1, tab2 = st.tabs(["📄 内容预览", "🌐 全屏HTML"])

    with tab1:
        # Read HTML content
        html_content = selected['path'].read_text(encoding='utf-8')

        # Show in embedded iframe with adjustable height
        height = st.slider("显示高度", 400, 1500, 800, step=100)
        components.html(html_content, height=height, scrolling=True)

    with tab2:
        st.markdown("""
        <p style="font-family: var(--ui-font); color: var(--ink-medium); margin-bottom: 1rem;">
            全屏模式下，HTML报告将完整渲染。适合详细阅读和交互。
        </p>
        """, unsafe_allow_html=True)

        # Full height display
        html_content = selected['path'].read_text(encoding='utf-8')
        components.html(html_content, height=1200, scrolling=True)

elif selected['type'] == 'MD':
    raw_content = selected['path'].read_text(encoding='utf-8')
    processed = process_markdown(raw_content)
    st.markdown(processed, unsafe_allow_html=True)

# ==================== Footer ====================
st.divider()
st.markdown("""
<div class="end-mark">
    ◆ ◈ ◆ — 报告结束 — ◆ ◈ ◆
</div>
""", unsafe_allow_html=True)