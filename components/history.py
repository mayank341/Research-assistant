import streamlit as st

from services import storage
from utils import state as S
from utils.styles import badge, empty_state, esc, fmt_dt


@st.dialog("Delete this report?")
def _confirm_delete(report_id: str, title: str) -> None:
    st.write(f"“{title}” will be permanently removed from this device.")
    c1, c2 = st.columns(2)
    if c1.button("Delete", type="primary", width="stretch", icon=":material/delete:"):
        storage.delete_report(report_id)
        if st.session_state.current_id == report_id:
            st.session_state.current_id = None
        S.refresh_reports()
        st.rerun()
    if c2.button("Cancel", width="stretch"):
        st.rerun()


def _status_badge(r: dict) -> str:
    return badge(r["status"], "ok") + (badge("Demo", "warn") if r.get("demo") else "")


def _heading(title: str, sub: str) -> None:
    st.markdown(f'<h2 class="rs-title" style="font-size:1.5rem">{title}</h2><p class="rs-sub">{sub}</p>', unsafe_allow_html=True)


def render_history() -> None:
    _heading("Research History", "Everything you have researched, newest first.")
    reports = st.session_state.reports
    if not reports:
        empty_state("No research yet", "Your completed research will appear here.")
        st.button("Start your first research", on_click=S.new_research, type="primary")
        return
    c1, c2 = st.columns([3, 1])
    q = c1.text_input("Search history", placeholder="Search by title or question", key="hist_q")
    status = c2.selectbox("Type", ["All", "Summary", "Detailed Report", "Comparison"], key="hist_t")
    rows = [r for r in reports if (not q or q.lower() in (r["title"] + r["question"]).lower())
            and (status == "All" or r["output_format"] == status)]
    if not rows:
        empty_state("No matches", "Try a different search or filter.")
    for r in rows:
        with st.container(border=True):
            c = st.columns([4, 1.6, 1.6, 1.2, 1.1, 1.1], vertical_alignment="center")
            c[0].markdown(f"**{r['title']}**")
            c[0].caption(r["question"][:110])
            c[1].caption(fmt_dt(r["created_at"]))
            c[2].caption(f"{r['depth']} · {r['output_format']}")
            c[3].markdown(_status_badge(r), unsafe_allow_html=True)
            c[4].button("Open", key=f"h_open_{r['id']}", on_click=S.open_report, args=(r["id"],), width="stretch")
            if c[5].button("Delete", key=f"h_del_{r['id']}", icon=":material/delete:", width="stretch"):
                _confirm_delete(r["id"], r["title"])


def render_saved() -> None:
    _heading("Saved Reports", "Reports you bookmarked for later.")
    saved = [r for r in st.session_state.reports if r.get("saved")]
    if not saved:
        empty_state("Nothing saved yet", "Use “Save report” on any report to keep it here.")
        return
    q = st.text_input("Search saved reports", placeholder="Search saved reports", key="saved_q")
    for r in [r for r in saved if not q or q.lower() in (r["title"] + r["executive_summary"]).lower()]:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            c1.markdown(f"**{r['title']}** {_status_badge(r)}", unsafe_allow_html=True)
            c1.caption(f"{fmt_dt(r['created_at'])} · {r['depth']} · {len(r['sources'])} sources")
            c1.markdown(esc(r["executive_summary"][:280] + ("…" if len(r["executive_summary"]) > 280 else "")))
            c2.button("Open", key=f"s_open_{r['id']}", on_click=S.open_report, args=(r["id"],), width="stretch")
            c2.button("Remove", key=f"s_rm_{r['id']}", on_click=S.toggle_saved, args=(r["id"],), width="stretch")
