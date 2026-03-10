"""Reports Viewer tab for the Streamlit config panel."""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import NamedTuple

import streamlit as st
import streamlit.components.v1 as components

from webui.i18n import t

# project root: tabs/ -> webui/ -> src/ -> project_root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_REPORTS_DIR = _PROJECT_ROOT / "data" / "reports"

_SEL_KEY = "rsel"  # prefix for all selectbox session-state keys
_PREVIEW_KEY = "preview_report"


# ─── data structures ──────────────────────────────────────────────────────────


class ReportFile(NamedTuple):
    path: Path
    display: str  # human-friendly label shown in UI
    source: str  # uppercase source name / keyword slug / "keyword_trend"
    report_type: str  # "daily" | "trend" | "keyword_trend"


# ─── label formatting ─────────────────────────────────────────────────────────


def _fmt_daily(stem: str) -> str:
    """ARXIV_Report_2026-03-10_12-27-47  →  2026-03-10  12:27:47"""
    m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})$", stem)
    if m:
        return f"{m.group(1)}  {m.group(2).replace('-', ':')}"
    return stem


def _fmt_trend(stem: str) -> str:
    """2025-03-10_2026-03-10  →  2025-03-10 → 2026-03-10"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})$", stem)
    if m:
        return f"{m.group(1)} → {m.group(2)}"
    return stem


def _fmt_kw(stem: str) -> str:
    """keyword_trends_2026-03-09  →  2026-03-09"""
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", stem)
    return m.group(1) if m else stem


# ─── discovery ────────────────────────────────────────────────────────────────


def _discover_reports() -> dict[str, list[ReportFile]]:
    """Scan data/reports/ and return three lists, each newest-first."""
    result: dict[str, list[ReportFile]] = {
        "daily": [],
        "trend": [],
        "keyword_trend": [],
    }

    # daily_research/html/{source}/*.html
    daily_html = _REPORTS_DIR / "daily_research" / "html"
    if daily_html.exists():
        for src_dir in daily_html.iterdir():
            if src_dir.is_dir():
                src = src_dir.name.upper()
                for f in src_dir.glob("*.html"):
                    result["daily"].append(ReportFile(f, _fmt_daily(f.stem), src, "daily"))
        result["daily"].sort(key=lambda r: r.path.stat().st_mtime, reverse=True)

    # trend_research/html/{keyword-slug}/*.html
    trend_html = _REPORTS_DIR / "trend_research" / "html"
    if trend_html.exists():
        for kw_dir in trend_html.iterdir():
            if kw_dir.is_dir():
                slug = kw_dir.name
                for f in kw_dir.glob("*.html"):
                    result["trend"].append(ReportFile(f, _fmt_trend(f.stem), slug, "trend"))
        result["trend"].sort(key=lambda r: r.path.stat().st_mtime, reverse=True)

    # keyword_trend/html/*.html
    kw_html = _REPORTS_DIR / "keyword_trend" / "html"
    if kw_html.exists():
        for f in sorted(kw_html.glob("*.html"), reverse=True):
            result["keyword_trend"].append(
                ReportFile(f, _fmt_kw(f.stem), "keyword_trend", "keyword_trend")
            )

    return result


def _load_trend_metadata(html_path: Path) -> dict | None:
    md_dir = html_path.parent.parent.parent / "markdown" / html_path.parent.name
    meta_path = md_dir / f"{html_path.stem}_metadata.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ─── file browser helpers ─────────────────────────────────────────────────────


def _sel_key(rtype: str, group: str) -> str:
    return f"{_SEL_KEY}_{rtype}_{group}"


def _make_on_change(key: str, by_display: dict[str, ReportFile]):
    """Return an on_change callback that updates preview_report."""

    def _cb():
        chosen = st.session_state.get(key)
        if chosen in by_display:
            st.session_state[_PREVIEW_KEY] = by_display[chosen]

    return _cb


def _render_group_selectbox(rtype: str, group: str, reports: list[ReportFile]) -> None:
    """Render one selectbox for a source/slug group; updates preview on change."""
    by_display = {r.display: r for r in reports}
    labels = [r.display for r in reports]
    key = _sel_key(rtype, group)

    # Auto-set preview if nothing selected yet
    if _PREVIEW_KEY not in st.session_state and reports:
        st.session_state[_PREVIEW_KEY] = reports[0]

    st.selectbox(
        f"**{group}** ({len(labels)})",
        labels,
        key=key,
        on_change=_make_on_change(key, by_display),
    )
    # Button to explicitly load this selectbox's current selection into preview
    if st.button(t("reports_preview_btn"), key=f"btn_{key}", use_container_width=True):
        chosen = st.session_state.get(key)
        if chosen in by_display:
            st.session_state[_PREVIEW_KEY] = by_display[chosen]
            st.rerun()


def _render_category_col(rtype: str, reports: list[ReportFile], header: str) -> None:
    """Render one category column (daily / trend / keyword_trend)."""
    count = len(reports)
    st.markdown(
        f"**{header}**<br>"
        f"<span style='color:#888;font-size:0.82em'>{count} {t('reports_count_unit')}</span>",
        unsafe_allow_html=True,
    )

    if not reports:
        st.caption(t("reports_empty_type"))
        return

    if rtype == "keyword_trend":
        _render_group_selectbox(rtype, "keyword_trend", reports)
    else:
        # Group by source / keyword slug
        groups = sorted({r.source for r in reports})
        for grp in groups:
            grp_reports = [r for r in reports if r.source == grp]
            _render_group_selectbox(rtype, grp, grp_reports)


# ─── preview ──────────────────────────────────────────────────────────────────


def _render_preview(report: ReportFile) -> None:
    """Render file info bar, optional metadata, height control, and HTML preview."""

    # File info bar
    stat = report.path.stat()
    size_kb = stat.st_size / 1024
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    type_cn = {
        "daily": t("rtype_daily"),
        "trend": t("rtype_trend"),
        "keyword_trend": t("rtype_keyword_trend"),
    }.get(report.report_type, report.report_type)

    st.caption(
        f"**{type_cn}** · `{report.source}` · `{report.path.name}` · "
        f"{size_kb:.1f} KB · {t('reports_mtime')}: {mtime}"
    )

    # Trend metadata
    if report.report_type == "trend":
        meta = _load_trend_metadata(report.path)
        if meta:
            with st.expander(t("reports_meta_expander"), expanded=False):
                cols = st.columns(3)
                if "keyword" in meta:
                    cols[0].metric(t("meta_keyword"), meta["keyword"])
                if "date_from" in meta and "date_to" in meta:
                    cols[1].metric(t("meta_date_range"), f"{meta['date_from']} → {meta['date_to']}")
                if "total_papers" in meta:
                    cols[2].metric(t("meta_papers"), meta["total_papers"])

    # Height control
    col_h, _ = st.columns([1, 4])
    with col_h:
        valid_heights = [600, 800, 1000, 1200, 1500, 2000]
        if st.session_state.get("preview_height") not in valid_heights:
            st.session_state["preview_height"] = 1000
        height = st.select_slider(
            t("reports_height"),
            options=valid_heights,
            key="preview_height",
        )

    # Render HTML
    try:
        html_content = report.path.read_text(encoding="utf-8")
        components.html(html_content, height=height, scrolling=True)
    except Exception as e:
        st.error(f"{t('reports_load_error')}: {e}")


# ─── main render ──────────────────────────────────────────────────────────────


def render(_env_values: dict, _config_values: dict) -> None:
    """Render the Reports Viewer tab."""

    st.markdown(
        f'<p class="section-title">{t("reports_title")}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="hint-text">{t("reports_hint")}</p>',
        unsafe_allow_html=True,
    )

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button(t("reports_refresh"), use_container_width=True):
            for k in list(st.session_state.keys()):
                if k.startswith(_SEL_KEY) or k in (_PREVIEW_KEY, "preview_height"):
                    del st.session_state[k]
            st.rerun()

    st.divider()

    all_reports = _discover_reports()
    total = sum(len(v) for v in all_reports.values())

    if total == 0:
        st.info(t("reports_empty"))
        st.caption(f"📂 {t('reports_dir_label')}: `{_REPORTS_DIR}`")
        return

    # ── Three-column file browser ──────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        _render_category_col(
            "daily",
            all_reports["daily"],
            f"📅 {t('rtype_daily')}",
        )

    with c2:
        _render_category_col(
            "trend",
            all_reports["trend"],
            f"🔬 {t('rtype_trend')}",
        )

    with c3:
        _render_category_col(
            "keyword_trend",
            all_reports["keyword_trend"],
            f"📈 {t('rtype_keyword_trend')}",
        )

    # ── Preview ────────────────────────────────────────────────────────────
    report: ReportFile | None = st.session_state.get(_PREVIEW_KEY)
    if report is None:
        return

    st.divider()
    _render_preview(report)
