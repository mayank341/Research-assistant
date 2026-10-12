import streamlit as st

from services.paper_summarizer import LENGTHS, PAPERS, STYLES, summarize_paper


def render_summarizer() -> None:
    st.markdown('<h2 class="rs-title" style="font-size:1.5rem">Paper Summarizer</h2>'
                '<p class="rs-sub">Your original summarizer: pick a classic paper, a style and a length.</p>',
                unsafe_allow_html=True)
    with st.form("summarizer_form"):
        paper = st.selectbox("Select Research Paper Name", PAPERS)
        c1, c2 = st.columns(2)
        style = c1.selectbox("Select Explanation Style", STYLES)
        length = c2.selectbox("Select Explanation Length", LENGTHS)
        go = st.form_submit_button("Summarize", type="primary", icon=":material/auto_awesome:")
    if go:
        try:
            with st.spinner("Summarizing…"):
                st.session_state.summary = (paper, style, length, summarize_paper(paper, style, length))
        except FileNotFoundError as e:
            st.error(str(e))
        except Exception as e:
            st.error("The summary could not be generated. Check your API key and network, then try again.")
            with st.expander("Technical details"):
                st.code(f"{type(e).__name__}: {e}", language=None)
    if st.session_state.get("summary"):
        p, s, l, text = st.session_state.summary
        with st.container(border=True):
            st.caption(f"{p} · {s} · {l}")
            st.markdown(text)
