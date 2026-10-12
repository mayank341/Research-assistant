import streamlit as st

from components.progress import execute_job
from components.report_view import render_report
from components.documents import render_uploader
from services import documents as D
from services.research_service import CONNECTED
from utils import state as S
from utils.styles import badge, esc, fmt_dt, label

DEPTHS = ["Quick", "Standard", "Deep Research"]
SOURCES = ["Web", "Academic", "Documents", "All Sources"]
FORMATS = ["Summary", "Detailed Report", "Comparison"]

SUGGESTIONS = [
    ("Compare competing AI frameworks", "Strengths, trade-offs and research behind popular approaches.",
     "Compare retrieval-augmented generation with fine-tuning for adapting language models to new domains"),
    ("Analyze recent machine learning research", "What is new, what is proven and what is still open.",
     "What are the most important recent advances in efficient transformer inference?"),
    ("Research a business or market opportunity", "Evidence on adoption, risks and technical feasibility.",
     "What does research say about the feasibility of AI assistants for clinical documentation?"),
    ("Summarize an academic topic", "A clear, cited overview you can build on.",
     "Summarize the current state of research on diffusion models for image generation"),
]


def render_header() -> None:
    ss = st.session_state
    if ss.running:
        status = badge("Researching…", "run")
    elif ss.last_error:
        status = badge("Failed", "err")
    elif S.current_report():
        status = badge("Completed", "ok")
    else:
        status = badge("Ready")
    if ss.settings.get("demo_mode"):
        status += badge("Demo mode", "warn")
    left, right = st.columns([5, 1.2], vertical_alignment="center")
    left.markdown(
        '<h1 class="rs-title">Your AI Research Workspace</h1>'
        '<p class="rs-sub">Turn complex questions into clear, evidence-backed insights.</p>'
        f'<div>{status}</div>', unsafe_allow_html=True)
    right.button("Preferences", icon=":material/tune:", on_click=S.goto, args=("settings",), width="stretch")


def render_input(disabled: bool) -> None:
    ss = st.session_state
    with st.container(border=True):
        st.text_area("Research question", key="question_input", height=110, disabled=disabled,
                     placeholder="What would you like to research today?", label_visibility="collapsed")
        c1, c2, c3, c4 = st.columns([2.2, 1.3, 1.3, 1.2], vertical_alignment="bottom")
        c1.radio("Research depth", DEPTHS, key="in_depth", horizontal=True, disabled=disabled,
                 help="Quick: fewer sources, faster. Standard: balanced. Deep Research: more sources and sections, slower.")
        c2.selectbox("Sources", SOURCES, key="in_sources", disabled=disabled,
                     help="Where to look. Only connected sources are searched; others are skipped and reported.")
        c3.selectbox("Output format", FORMATS, key="in_format", disabled=disabled,
                     help="Summary is short, Detailed Report is thorough, Comparison adds a comparison table.")
        start = c4.button("Start Research", type="primary", icon=":material/search:", width="stretch", disabled=disabled)
        connected = ", ".join(CONNECTED) or "none"
        demo = ss.settings.get("demo_mode")
        st.caption("Demo mode is on: results are sample data." if demo else
                   f"Connected sources: {connected}. Documents in your library: {len(D.list_documents())}.")
        with st.expander("Attach documents"):
            render_uploader("ws")
    if start:
        q = ss.question_input.strip()
        if len(q) < 8:
            st.warning("Please enter a research question (at least a few words).")
            return
        job = {"question": q, "depth": ss.in_depth, "sources": ss.in_sources, "output_format": ss.in_format}
        ss.job, ss.last_job, ss.running, ss.last_error = job, job, True, None
        st.rerun()


def render_error() -> None:
    ss = st.session_state
    err = ss.last_error
    st.markdown(f'<div class="rs-card" style="border-left:3px solid #ef4444"><div class="rs-label">Research failed</div>'
                f'<p>{esc(err["message"])}</p></div>', unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 4])
    c1.button("Retry", icon=":material/refresh:", type="primary", on_click=S.retry, width="stretch")
    c2.button("Dismiss", on_click=lambda: ss.update(last_error=None), width="stretch")
    if err.get("detail"):
        with st.expander("Technical details"):
            st.code(err["detail"], language=None)
    if ss.last_activity:
        with st.expander("What happened before the failure"):
            for e in ss.last_activity:
                st.markdown(f"- `{e['time']}` {e['message']}")


def render_suggestions() -> None:
    label("Try a research idea")
    cols = st.columns(2)
    for i, (title, desc, prompt) in enumerate(SUGGESTIONS):
        with cols[i % 2].container(border=True):
            st.markdown(f"**{title}**")
            st.caption(desc)
            st.button("Use this idea", key=f"sug_{i}", icon=":material/arrow_outward:",
                      on_click=S.prefill, args=(prompt,))


def render_recent() -> None:
    recent = st.session_state.reports[:3]
    if not recent:
        return
    st.write("")
    label("Recent research")
    for r in recent:
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"**{r['title']}**  \n<span class='rs-meta'>{esc(fmt_dt(r['created_at']))}</span>", unsafe_allow_html=True)
        c2.button("Open", key=f"rec_{r['id']}", on_click=S.open_report, args=(r["id"],), width="stretch")


def render_workspace() -> None:
    ss = st.session_state
    if ss.get("toast"):
        st.toast(ss.pop("toast"))
    render_header()
    render_input(disabled=ss.running)
    if ss.running:
        execute_job(ss.job)  # reruns when finished
        return
    if ss.last_error:
        render_error()
        return
    report = S.current_report()
    if report:
        render_report(report)
    else:
        st.write("")
        render_suggestions()
        render_recent()
