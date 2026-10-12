"""Live research execution UI. Progress = real completed backend stages, nothing simulated."""
import streamlit as st

from services import storage
from services.demo_data import run_demo
from services.research_service import STAGES, ResearchError, run_research
from utils import state as S
from utils.styles import esc, label


def _stages_html(states: list[str]) -> str:
    return "".join(f'<div class="rs-stage {s}"><span class="rs-dot"></span><span>{esc(n)}</span></div>'
                   for n, s in zip(STAGES, states))


def execute_job(job: dict) -> None:
    ss = st.session_state
    fresh = ss.pop("force_fresh", False)
    if ss.settings.get("reuse_recent", True) and not fresh and not ss.settings.get("demo_mode"):
        hit = S.find_recent(job)
        if hit:
            ss.current_id, ss.running = hit["id"], False
            ss.toast = "Reused a recent result for the same question (no API cost). Use “Refine and rerun” for a fresh run."
            st.rerun()
    n = len(STAGES)
    states = ["pending"] * n
    log: list[dict] = []

    with st.container(border=True):
        label("Research progress")
        bar = st.progress(0.0, text="Starting research")
        stage_ph = st.empty()
        st.caption("The bar advances only when a backend stage actually finishes. Long steps may take a minute.")
    log_ph = st.expander("Activity log").empty()

    def render() -> None:
        stage_ph.markdown(_stages_html(states), unsafe_allow_html=True)
        done = states.count("done")
        bar.progress(done / n, text=f"{done} of {n} stages complete")
        log_ph.markdown("\n".join(f"- `{e['time']}` {e['message']}" for e in log) or "Waiting…")

    def on_progress(stage: int, state: str, msg: str) -> None:
        from datetime import datetime
        if state == "start":
            states[stage] = "active"
        elif state == "done":
            states[stage] = "done"
        elif state == "error":
            states[stage] = "error"
        log.append({"time": datetime.now().strftime("%H:%M:%S"), "message": msg})
        render()

    render()
    runner = run_demo if ss.settings.get("demo_mode") else run_research
    try:
        report = runner(**job, on_progress=on_progress)
    except ResearchError as e:
        ss.last_error = {"message": str(e), "detail": e.detail}
    except Exception as e:  # never show a raw traceback
        ss.last_error = {"message": "Something unexpected went wrong while running the research. You can retry.",
                         "detail": f"{type(e).__name__}: {e}"}
    else:
        storage.upsert_report(report)
        S.refresh_reports()
        ss.current_id = report["id"]
    ss.running, ss.last_activity = False, log
    st.rerun()
