"""ResearchAI - a Streamlit research workspace.  Run:  streamlit run app.py"""
from dotenv import load_dotenv

load_dotenv()

import streamlit as st  # noqa: E402

st.set_page_config(page_title="ResearchAI", page_icon=":material/travel_explore:", layout="wide",
                   initial_sidebar_state="expanded")

from components.documents import render_documents  # noqa: E402
from components.history import render_history, render_saved  # noqa: E402
from components.research_input import render_workspace  # noqa: E402
from components.settings import render_settings  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402
from components.source_cards import render_sources_library  # noqa: E402
from components.summarizer import render_summarizer  # noqa: E402
from utils import state as S  # noqa: E402
from utils.styles import inject_css  # noqa: E402

S.init_state()
S.persist_widget_state()
inject_css()
render_sidebar()

PAGES = {
    "workspace": render_workspace,
    "history": render_history,
    "saved": render_saved,
    "documents": render_documents,
    "sources": render_sources_library,
    "summarizer": render_summarizer,
    "settings": render_settings,
}
PAGES.get(st.session_state.page, render_workspace)()
