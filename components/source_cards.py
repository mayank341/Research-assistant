import streamlit as st

from utils.styles import badge, empty_state, esc, label


def render_source_card(src: dict, key: str, extra: str = "") -> None:
    with st.container(border=True):
        top, act = st.columns([5, 1], vertical_alignment="center")
        with top:
            st.markdown(f"**[{src.get('id', '·')}] {src['title']}**")
            meta = " · ".join(x for x in [src.get("domain"), src.get("published"), ", ".join(src.get("authors", [])[:3])] if x)
            badges = ""
            if "cited" in src:
                badges += badge("Cited in report", "ok") if src["cited"] else badge("Retrieved, not cited")
            if src.get("relevance"):
                badges += badge(f"Relevance: {src['relevance']}")
            st.markdown(f'<span class="rs-meta">{esc(meta)}</span><br>{badges}{extra}', unsafe_allow_html=True)
        with act:
            if str(src["url"]).startswith("http"):
                st.link_button("Open source", src["url"], icon=":material/open_in_new:", width="stretch")
            else:
                st.caption("Uploaded document")
        with st.expander("Source details"):
            st.markdown(f"**Abstract / snippet (as retrieved):** {src.get('abstract') or 'Not available.'}")
            if src.get("claims"):
                st.markdown("**Claims extracted by the AI from this abstract:**")
                for c in src["claims"]:
                    st.markdown(f"- {c}")
            st.caption(f"Type: {src.get('kind', 'n/a')} · Retrieved: {src.get('retrieved_at', 'n/a')[:19]}")


def render_sources_library() -> None:
    reports = st.session_state.reports
    merged: dict[str, dict] = {}
    for r in reports:
        for s in r.get("sources", []):
            e = merged.setdefault(s["url"], {**s, "_reports": []})
            e["_reports"].append(r["title"])
    st.markdown('<h2 class="rs-title" style="font-size:1.5rem">Sources Library</h2>', unsafe_allow_html=True)
    st.markdown('<p class="rs-sub">Every source collected across your research.</p>', unsafe_allow_html=True)
    if not merged:
        empty_state("No sources yet", "Sources appear here after you run research.")
        return
    c1, c2 = st.columns([3, 1])
    q = c1.text_input("Search sources", placeholder="Search by title, author or domain", key="lib_q")
    only_cited = c2.checkbox("Cited only", key="lib_cited")
    items = [
        s for s in merged.values()
        if (not q or q.lower() in (s["title"] + s.get("domain", "") + " ".join(s.get("authors", []))).lower())
        and (not only_cited or s.get("cited"))
    ]
    st.caption(f"{len(items)} source(s)")
    if not items:
        empty_state("No matches", "Try a different search or clear the filter.")
    for i, s in enumerate(items):
        render_source_card({**s, "id": "·"}, f"lib_{i}", extra=f'<br><span class="rs-meta">Used in: {esc("; ".join(s["_reports"][:2]))}</span>')
