import json
import re

import streamlit as st

from components.source_cards import render_source_card
from services.research_service import report_to_markdown
from utils import state as S
from utils.styles import badge, esc, fmt_dt, label


def link_citations(text: str, by_id: dict) -> str:
    """Turn [n] into a clickable link to the source."""
    def repl(m):
        s = by_id.get(int(m.group(1)))
        return f"[[{m.group(1)}]]({s['url']})" if s and str(s.get("url", "")).startswith("http") else m.group(0)
    return re.sub(r"\[(\d+)\](?!\()", repl, text or "")


def _md_table(t: dict, by_id: dict) -> str:
    head = "| " + " | ".join(t["columns"]) + " |\n|" + "---|" * len(t["columns"]) + "\n"
    return head + "\n".join("| " + " | ".join(link_citations(c, by_id).replace("|", "/") for c in row) + " |" for row in t["rows"])


def render_report(r: dict) -> None:
    by_id = {s["id"]: s for s in r["sources"]}
    lk = lambda t: link_citations(t, by_id)  # noqa: E731
    st.divider()

    # ---- header
    left, a1, a2, a3 = st.columns([4, 1, 1, 1], vertical_alignment="center")
    with left:
        st.markdown(f'<h2 class="rs-title" style="font-size:1.55rem">{esc(r["title"])}</h2>', unsafe_allow_html=True)
        b = badge(r["status"], "ok") + badge(r["depth"]) + badge(r["output_format"])
        if r.get("demo"):
            b += badge("Demo: sample data", "warn")
        st.markdown(f'{b}<span class="rs-meta">Generated {esc(fmt_dt(r["created_at"]))}</span>', unsafe_allow_html=True)
    a1.download_button("Markdown", report_to_markdown(r), file_name=f"report-{r['id']}.md", mime="text/markdown",
                       icon=":material/download:", width="stretch", on_click="ignore", key=f"dl_md_{r['id']}")
    a2.download_button("JSON", json.dumps(r, indent=2, ensure_ascii=False), file_name=f"report-{r['id']}.json",
                       mime="application/json", icon=":material/data_object:", width="stretch", on_click="ignore",
                       key=f"dl_js_{r['id']}")
    a3.button("Saved" if r.get("saved") else "Save report", icon=":material/bookmark:" if r.get("saved") else ":material/bookmark_add:",
              type="secondary" if r.get("saved") else "primary", width="stretch", on_click=S.toggle_saved,
              args=(r["id"],), key=f"save_{r['id']}")

    if r.get("demo"):
        st.warning("This is a demo report with sample data. No real search was performed.", icon=":material/science:")

    tab_o, tab_d, tab_s, tab_a = st.tabs(["Overview", "Detailed Report", "Sources", "Research Activity"])

    # ---- overview
    with tab_o:
        with st.container(border=True):
            label("Executive summary")
            st.markdown(lk(r["executive_summary"]))
        label("Key takeaways")
        cols = st.columns(2)
        for i, t in enumerate(r["key_takeaways"]):
            with cols[i % 2].container(border=True):
                st.markdown(f"**{i + 1}.** {lk(t)}")
        if r.get("interpretation"):
            st.markdown('<div class="rs-card interp"><div class="rs-label">AI interpretation · not directly sourced</div>'
                        f'<p>{esc(r["interpretation"])}</p></div>', unsafe_allow_html=True)
        st.write("")
        label("Further exploration")
        for i, q in enumerate(r.get("follow_ups", [])):
            c1, c2 = st.columns([5, 1.3], vertical_alignment="center")
            c1.markdown(q)
            c2.button("Investigate", key=f"fu_{r['id']}_{i}", icon=":material/travel_explore:", width="stretch",
                      on_click=S.prefill, args=(q, "Deep Research", r["sources_mode"], r["output_format"]),
                      help="Loads this question into the research box. You choose when to start.")
        st.button("Refine and rerun this research", icon=":material/refresh:", key=f"rerun_{r['id']}",
                  on_click=S.prefill, args=(r["question"], r["depth"], r["sources_mode"], r["output_format"], True))

    # ---- detailed
    with tab_d:
        st.markdown('<div class="rs-card fact"><p class="rs-meta">Statements with a numbered citation such as '
                    '<b>[1]</b> come from a retrieved source (click to open it). "AI interpretation" is model reasoning '
                    'and is not a sourced fact.</p></div>', unsafe_allow_html=True)
        for s in r["sections"]:
            st.markdown(f"### {s['heading']}")
            st.markdown(lk(s["body"]))
        if r.get("table"):
            st.markdown("### Comparison")
            st.markdown(_md_table(r["table"], by_id))
        if r.get("interpretation"):
            st.markdown("### AI interpretation")
            st.caption("Not directly sourced.")
            st.markdown(r["interpretation"])
        if r.get("limitations"):
            st.markdown("### Limitations")
            st.markdown(r["limitations"])
        for n in r.get("notes", []):
            st.caption(n)

    # ---- sources
    with tab_s:
        cited = sum(1 for s in r["sources"] if s.get("cited"))
        st.caption(f"{len(r['sources'])} retrieved · {cited} cited in the report")
        for s in r["sources"]:
            render_source_card(s, f"{r['id']}_{s['id']}")

    # ---- activity
    with tab_a:
        st.caption("Exactly what the pipeline did, in order.")
        u = r.get("usage")
        if u:
            cost = f" · about ${u['approx_cost_usd']:.4f}" if u.get("approx_cost_usd") is not None else ""
            st.info(f"API usage: {u['input_tokens']} input / {u['output_tokens']} output tokens on {u['model']}{cost}", icon=":material/payments:")
        for e in r.get("activity", []):
            st.markdown(f"- `{e['time']}` **{e['stage']}** · {e['message']}")
