import streamlit as st

from services import documents as D
from utils.styles import empty_state, fmt_dt


def render_uploader(key: str) -> None:
    with st.form(f"upload_{key}", clear_on_submit=True):
        files = st.file_uploader("Add documents", type=D.SUPPORTED, accept_multiple_files=True,
                                 help="PDF, Word (.docx), text or Markdown. Max 10 MB each. Text is read on this computer; "
                                      "only the best-matching passages are sent to the AI when you research.")
        go = st.form_submit_button("Add to library", icon=":material/upload_file:")
    if go:
        if not files:
            st.warning("Choose at least one file first.")
        for f in files or []:
            try:
                with st.spinner(f"Reading {f.name}…"):
                    doc = D.add_document(f.name, f.getvalue())
                st.success(f"{f.name}: already in your library." if doc.get("duplicate")
                           else f"{f.name}: added ({len(doc['chunks'])} passages).")
            except D.DocumentError as e:
                st.error(f"{f.name}: {e}")
            except Exception as e:
                st.error(f"{f.name}: could not be processed.")
                with st.expander("Technical details"):
                    st.code(f"{type(e).__name__}: {e}", language=None)


def render_documents() -> None:
    st.markdown('<h2 class="rs-title" style="font-size:1.5rem">Documents</h2>'
                '<p class="rs-sub">Upload your own files, then choose “Documents” or “All Sources” when researching.</p>',
                unsafe_allow_html=True)
    with st.container(border=True):
        render_uploader("page")
    docs = D.list_documents()
    if not docs:
        empty_state("No documents yet", "Add a PDF, Word, text or Markdown file above.")
        return
    st.caption(f"{len(docs)} document(s) in your library")
    for d in docs:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
            c1.markdown(f"**{d['name']}**")
            c1.caption(f"{d['size'] / 1024:.0f} KB · {d['chunks']} passages · added {fmt_dt(d['added_at'])}")
            if c2.button("Remove", key=f"rmdoc_{d['id']}", icon=":material/delete:", width="stretch"):
                D.delete_document(d["id"])
                st.rerun()
