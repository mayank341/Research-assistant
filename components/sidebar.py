import streamlit as st

from utils import state as S
from utils.styles import badge, esc, logo_svg

# Change these two lines to update the profile card at the bottom of the sidebar
CREATOR = "Mayank"
TAGLINE = "ResearchAI · Local workspace"

NAV = [
    ("workspace", "Dashboard", ":material/dashboard:"),
    ("history", "Research History", ":material/history:"),
    ("saved", "Saved Reports", ":material/bookmark:"),
    ("documents", "Documents", ":material/folder_open:"),
    ("sources", "Sources Library", ":material/library_books:"),
    ("summarizer", "Paper Summarizer", ":material/description:"),
    ("settings", "Settings", ":material/settings:"),
]


def render_sidebar() -> None:
    ss = st.session_state
    with st.sidebar:
        st.markdown(f'<div class="rs-brand">{logo_svg()}<span>ResearchAI</span></div>', unsafe_allow_html=True)
        st.button("New Research", icon=":material/add:", type="primary", width="stretch",
                  on_click=S.new_research, key="nav_new")
        st.write("")
        for key, text, icon in NAV:
            st.button(text, icon=icon, key=f"nav_{key}", width="stretch",
                      type="secondary" if ss.page == key else "tertiary",
                      on_click=S.goto, args=(key,))
        st.divider()
        if ss.settings.get("demo_mode"):
            st.markdown(badge("Demo mode: sample data", "warn"), unsafe_allow_html=True)
        st.markdown(
            f'<div class="rs-card" style="display:flex;gap:.7rem;align-items:center;padding:.6rem .8rem">'
            f'<div style="width:34px;height:34px;border-radius:50%;background:var(--rs-accent);color:#fff;'
            f'display:flex;align-items:center;justify-content:center;font-weight:600">{esc(CREATOR[:1].upper())}</div>'
            f'<div><div style="font-weight:600">Made by {esc(CREATOR)}</div>'
            f'<div class="rs-meta">{esc(TAGLINE)}</div></div></div>',
            unsafe_allow_html=True,
        )
