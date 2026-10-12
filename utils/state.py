"""Session-state helpers. All cross-page state lives in st.session_state."""
from __future__ import annotations

import streamlit as st

from services import storage

PAGES = ["workspace", "history", "saved", "documents", "sources", "summarizer", "settings"]
WIDGET_KEYS = ("question_input", "in_depth", "in_sources", "in_format")


def init_state() -> None:
    ss = st.session_state
    if "initialised" in ss:
        return
    s = storage.load_settings()
    ss.update(
        settings=s, reports=storage.load_reports(), page="workspace", current_id=None,
        running=False, job=None, last_job=None, last_error=None, last_activity=[],
        question_input="", in_depth=s["default_depth"], in_sources=s["default_sources"],
        in_format=s["default_format"], initialised=True,
    )


def persist_widget_state() -> None:
    """Re-assign widget keys so inputs survive navigating to other pages."""
    for k in WIDGET_KEYS:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]


def refresh_reports() -> None:
    st.session_state.reports = storage.load_reports()


def goto(page: str) -> None:
    st.session_state.page = page


def new_research() -> None:
    ss = st.session_state
    ss.page, ss.current_id, ss.last_error, ss.question_input = "workspace", None, None, ""


def open_report(report_id: str) -> None:
    st.session_state.current_id = report_id
    st.session_state.page = "workspace"
    st.session_state.last_error = None


def current_report():
    rid = st.session_state.current_id
    return next((r for r in st.session_state.reports if r["id"] == rid), None)


def prefill(question: str, depth: str | None = None, sources: str | None = None, fmt: str | None = None,
            fresh: bool = False) -> None:
    ss = st.session_state
    ss.page, ss.current_id, ss.last_error, ss.question_input = "workspace", None, None, question
    ss.force_fresh = fresh
    if depth:
        ss.in_depth = depth
    if sources:
        ss.in_sources = sources
    if fmt:
        ss.in_format = fmt


def retry() -> None:
    ss = st.session_state
    ss.job, ss.running, ss.last_error = ss.last_job, True, None


def toggle_saved(report_id: str) -> None:
    r = next((x for x in st.session_state.reports if x["id"] == report_id), None)
    if r:
        r["saved"] = not r.get("saved", False)
        storage.upsert_report(r)
        refresh_reports()


def find_recent(job: dict):
    """Return a saved report for the identical question if it is still fresh (saves API credit)."""
    from datetime import datetime, timedelta, timezone
    if job["sources"] in ("Documents", "All Sources"):  # your library can change, so always run fresh
        return None
    ttl = timedelta(minutes=15) if job["sources"] == "Web" else timedelta(hours=24)
    now = datetime.now(timezone.utc)
    for r in st.session_state.reports:
        if r.get("demo") or (r["question"].strip().lower(), r["depth"], r["sources_mode"], r["output_format"]) != (
                job["question"].strip().lower(), job["depth"], job["sources"], job["output_format"]):
            continue
        try:
            if now - datetime.fromisoformat(r["created_at"]) <= ttl:
                return r
        except ValueError:
            continue
    return None
