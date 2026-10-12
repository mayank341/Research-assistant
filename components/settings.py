import os

import streamlit as st

from components.research_input import DEPTHS, FORMATS, SOURCES
from services import storage
from utils.styles import apply_theme, badge


def render_settings() -> None:
    ss = st.session_state
    s = ss.settings
    st.markdown('<h2 class="rs-title" style="font-size:1.5rem">Settings</h2>'
                '<p class="rs-sub">Defaults for new research. Stored locally in the data folder.</p>', unsafe_allow_html=True)
    with st.form("settings_form"):
        st.markdown("**Appearance**")
        theme = st.radio("Theme", ["Dark", "Light"], index=["Dark", "Light"].index(s["theme"]), horizontal=True,
                         help="Applies after you refresh the page.")
        st.markdown("**Research defaults**")
        c1, c2, c3 = st.columns(3)
        depth = c1.selectbox("Default research depth", DEPTHS, index=DEPTHS.index(s["default_depth"]))
        sources = c2.selectbox("Preferred source type", SOURCES, index=SOURCES.index(s["default_sources"]))
        fmt = c3.selectbox("Report output format", FORMATS, index=FORMATS.index(s["default_format"]))
        st.markdown("**Demo mode**")
        demo = st.toggle("Use labelled sample data instead of the real research agent", value=s["demo_mode"],
                         help="For previewing the interface without an API key. Demo reports are clearly marked.")
        reuse = st.toggle("Reuse a recent result for the same question (saves API credit)", value=s.get("reuse_recent", True),
                          help="Web results are reused for 15 minutes, other results for 24 hours.")
        saved = st.form_submit_button("Save settings", type="primary", icon=":material/save:")
    if saved:
        theme_changed = theme != ss.settings.get("theme")
        ss.settings = {"theme": theme, "default_depth": depth, "default_sources": sources,
                       "default_format": fmt, "demo_mode": demo, "reuse_recent": reuse}
        storage.save_settings(ss.settings)
        ss.in_depth, ss.in_sources, ss.in_format = depth, sources, fmt
        ok = apply_theme(theme) if theme_changed else True
        msg = "Settings saved."
        if theme_changed and ok:
            msg += " Refresh the page to apply the theme."
        st.success(msg)
        if not ok:
            st.info("To change the theme, use the ⋮ menu → Settings → Theme.")

    st.markdown("**Model and agent**")
    with st.container(border=True):
        key_ok = bool(os.getenv("OPENAI_API_KEY"))
        st.markdown(f"API key: {badge('Configured' if key_ok else 'Missing', 'ok' if key_ok else 'err')}", unsafe_allow_html=True)
        st.markdown(f"Model: `{os.getenv('OPENAI_MODEL') or 'gpt-4o-mini (default, set OPENAI_MODEL to change)'}`")
        st.caption("Keys are read from environment variables (.env) and are never shown here.")
