"""Research pipeline (built to be cheap): 2 model calls per run, local evidence prep, free sources.

Sources (all free):  arXiv (papers) | Web (DuckDuckGo + Google News RSS, optional Tavily) | your uploaded Documents
Model calls:         1) scope + plan + queries   2) write the cited report.   Nothing else touches the paid API.
Not done (and the UI says so): full-text reading of web pages/papers, independent fact verification.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Optional
from urllib.parse import urlparse

import requests

from services import documents
from services.llm import DEFAULT_MODEL, get_llm

STAGES = [
    "Understanding the research question",
    "Creating a research plan",
    "Searching relevant sources",
    "Preparing evidence from sources",
    "Synthesizing findings",
    "Generating the final report",
]

DEPTH_PROFILES = {
    "Quick": {"per_query": 3, "max_sources": 5, "sections": 2, "queries": 2, "words": 350},
    "Standard": {"per_query": 5, "max_sources": 10, "sections": 4, "queries": 3, "words": 700},
    "Deep Research": {"per_query": 8, "max_sources": 18, "sections": 6, "queries": 4, "words": 1200},
}
FORMAT_GUIDE = {
    "Summary": "Keep it tight: 1-2 short sections and no comparison table.",
    "Detailed Report": "Write clear sections with headings. Add a comparison table only if it clearly helps.",
    "Comparison": "Include a comparison_table that compares the main items across 3-6 criteria; keep sections brief.",
}
DESCRIBE = {"Academic": "arXiv academic papers", "Web": "the live web and news", "Documents": "the user's uploaded documents"}
SNIPPET_CHARS = 700  # per source sent to the model: keeps token cost low
PRICES = {"gpt-4o-mini": (0.15, 0.60)}  # approx USD per 1M tokens (input, output)
UA = {"User-Agent": "ResearchAI/1.0"}
ARXIV_URL = "https://export.arxiv.org/api/query"
ProgressFn = Callable[[int, str, str], None]


class ResearchError(Exception):
    """A problem we can explain to the user in plain language."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


# ================================================================ providers
def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


_last_arxiv = [0.0]


def search_arxiv(query: str, max_results: int) -> list[dict]:
    wait = 3 - (time.time() - _last_arxiv[0])  # arXiv asks clients to wait ~3s between requests
    if wait > 0:
        time.sleep(wait)
    _last_arxiv[0] = time.time()
    words = re.findall(r"[A-Za-z0-9\-]+", query)[:6]
    if not words:
        return []
    params = {"search_query": " AND ".join(f"all:{w}" for w in words), "start": 0,
              "max_results": max_results, "sortBy": "relevance"}
    try:
        resp = requests.get(ARXIV_URL, params=params, timeout=15, headers=UA)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except requests.RequestException as e:
        raise ResearchError("Could not reach the arXiv search service. Check your connection and retry.", str(e)) from e
    except ET.ParseError as e:
        raise ResearchError("arXiv returned a response that could not be read. Please retry.", str(e)) from e
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        url = _clean(e.findtext("a:id", default="", namespaces=ns))
        if url:
            out.append({
                "title": _clean(e.findtext("a:title", default="Untitled", namespaces=ns)), "url": url,
                "domain": urlparse(url).netloc or "arxiv.org",
                "published": _clean(e.findtext("a:published", default="", namespaces=ns))[:10],
                "authors": [_clean(a.findtext("a:name", default="", namespaces=ns)) for a in e.findall("a:author", ns)][:6],
                "abstract": _clean(e.findtext("a:summary", default="", namespaces=ns)), "kind": "Academic (arXiv)"})
    return out


# ---- Web: Google News RSS (free, no key, real-time) + DuckDuckGo (free, no key); Tavily if TAVILY_API_KEY is set
_NEWSY = re.compile(r"today|latest|live|score|news|yesterday|tonight|match|result|\bvs\b|breaking|update|price|weather", re.I)


def _web_item(title, url, snippet, date) -> Optional[dict]:
    if not url:
        return None
    return {"title": _clean(title or url), "url": url, "domain": urlparse(url).netloc, "published": str(date or "")[:10],
            "authors": [], "abstract": _clean(snippet), "kind": "Web"}


def _google_news(query: str, n: int) -> list[dict]:
    try:
        resp = requests.get("https://news.google.com/rss/search", timeout=15, headers=UA,
                            params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError) as e:
        raise ResearchError("Google News could not be reached. Check your connection and retry.", str(e)) from e
    out = []
    for it in root.findall("./channel/item")[:n]:
        title, link, src = _clean(it.findtext("title")), _clean(it.findtext("link")), it.find("source")
        try:
            date = parsedate_to_datetime(it.findtext("pubDate")).date().isoformat()
        except (TypeError, ValueError):
            date = ""
        name = _clean(src.text) if src is not None else "Google News"
        item = _web_item(title, link, f"News headline from {name}, published {date or 'unknown date'}: {title}", date)
        if item:
            if src is not None and src.get("url"):
                item["domain"] = urlparse(src.get("url")).netloc
            out.append(item)
    return out


def _tavily(query: str, n: int, key: str) -> list[dict]:
    try:
        resp = requests.post("https://api.tavily.com/search", headers={"Authorization": f"Bearer {key}"}, timeout=20,
                             json={"query": query, "max_results": n, "search_depth": "basic",
                                   "topic": "news" if _NEWSY.search(query) else "general"})
        resp.raise_for_status()
        data = resp.json().get("results", [])
    except (requests.RequestException, ValueError) as e:
        raise ResearchError("Web search (Tavily) failed. Check TAVILY_API_KEY and your connection.", str(e)) from e
    return [i for i in (_web_item(x.get("title"), x.get("url"), x.get("content"), x.get("published_date")) for x in data) if i]


def _ddgs(query: str, n: int) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError as e:
        raise ResearchError("Web search needs a small package. Run: pip install ddgs") from e
    try:
        with DDGS() as d:
            items = [_web_item(x.get("title"), x.get("href"), x.get("body"), None) for x in d.text(query, max_results=n)]
            if _NEWSY.search(query):
                items += [_web_item(x.get("title"), x.get("url"), x.get("body"), x.get("date")) for x in d.news(query, max_results=n)]
    except Exception as e:
        raise ResearchError("Web search was rate-limited or failed. Wait a moment and retry.", f"{type(e).__name__}: {e}") from e
    return [i for i in items if i]


def search_web(query: str, max_results: int) -> list[dict]:
    items: list[dict] = []
    errors: list[ResearchError] = []
    if _NEWSY.search(query):  # fresh news first
        try:
            items += _google_news(query, max_results)
        except ResearchError as e:
            errors.append(e)
    try:
        key = os.getenv("TAVILY_API_KEY")
        items += _tavily(query, max_results, key) if key else _ddgs(query, max_results)
    except ResearchError as e:
        errors.append(e)
    if not items and errors:
        raise errors[0]
    seen, out = set(), []
    for i in items:
        if i["url"] not in seen:
            seen.add(i["url"])
            out.append(i)
    return out


# Register more providers here: CONNECTED["Name"] = fn(query, max_results) -> list[dict]
CONNECTED: dict[str, Callable[[str, int], list[dict]]] = {
    "Web": search_web, "Academic": search_arxiv, "Documents": documents.search_documents}


def _select_providers(sources: str):
    wanted = ["Web", "Academic", "Documents"] if sources == "All Sources" else [sources]
    return [(n, CONNECTED[n]) for n in wanted if n in CONNECTED], [n for n in wanted if n not in CONNECTED]


# ================================================================ model helpers
def _ask(llm, prompt: str, usage: dict) -> dict:
    try:
        resp = llm.invoke(prompt)
    except Exception as e:
        raise ResearchError("The language model request failed. Check your API key, credit balance and network.",
                            f"{type(e).__name__}: {e}") from e
    meta = getattr(resp, "usage_metadata", None) or {}
    usage["input_tokens"] += int(meta.get("input_tokens", 0))
    usage["output_tokens"] += int(meta.get("output_tokens", 0))
    m = re.search(r"\{.*\}", resp.content, re.S)
    if not m:
        raise ResearchError("The model returned an unreadable response. Please retry.", resp.content[:500])
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ResearchError("The model returned malformed output. Please retry.", str(e)) from e


def _clean_citations(text: str, valid: set[int]) -> str:
    def repl(m):
        return "".join(f"[{i}]" for i in (int(x) for x in re.findall(r"\d+", m.group(1))) if i in valid)
    return re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", repl, text or "")


def _cited_ids(*texts: str) -> set[int]:
    return {int(n) for t in texts for n in re.findall(r"\[(\d+)\]", t or "")}


def _usage_summary(usage: dict) -> dict:
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    price = PRICES.get(model)
    cost = round((usage["input_tokens"] * price[0] + usage["output_tokens"] * price[1]) / 1e6, 5) if price else None
    return {**usage, "model": model, "approx_cost_usd": cost}


# ================================================================ pipeline
def run_research(question: str, depth: str = "Standard", sources: str = "Academic",
                 output_format: str = "Detailed Report", on_progress: Optional[ProgressFn] = None) -> dict:
    prof = DEPTH_PROFILES.get(depth, DEPTH_PROFILES["Standard"])
    log: list[dict] = []
    t0 = time.time()
    usage = {"input_tokens": 0, "output_tokens": 0}

    def emit(stage: int, state: str, msg: str):
        if state == "done":
            msg = f"{msg} ({time.time() - t0:.0f}s elapsed)"
        log.append({"time": datetime.now().strftime("%H:%M:%S"), "stage": STAGES[stage], "state": state, "message": msg})
        if on_progress:
            on_progress(stage, state, msg)

    if not os.getenv("OPENAI_API_KEY"):
        raise ResearchError("OPENAI_API_KEY is not set. Add it to your .env file and restart the app.")
    providers, missing = _select_providers(sources)
    if any(n == "Documents" for n, _ in providers) and not documents.has_documents():
        providers = [p for p in providers if p[0] != "Documents"]
        missing.append("Documents (no files uploaded yet)")
        if not providers:
            raise ResearchError("You chose Documents, but no files are uploaded yet. Open the Documents page and add some first.")
    if not providers:
        raise ResearchError(f"'{sources}' sources are not available. Choose another source type.")
    llm = get_llm()

    # ---- 0+1: scope and plan in ONE model call
    emit(0, "start", "Reading and scoping the question")
    u = _ask(llm,
             "You are a research assistant. Restate this research question precisely, define its scope, and plan the research.\n"
             f"Question: {question}\nToday's date is {datetime.now().strftime('%A, %d %B %Y')}; interpret 'today' and 'latest' "
             f"relative to it and put the date or year in queries when it matters.\nDepth: {depth}. Searchable sources: "
             f"{', '.join(DESCRIBE[n] for n, _ in providers)}. Write {prof['queries']} short search queries "
             "(2-6 words each, no operators) suited to them.\nReturn ONLY JSON: "
             + json.dumps({"restated_question": "str", "scope": "str", "plan": ["step"], "search_queries": ["keywords"]}), usage)
    restated = u.get("restated_question") or question
    emit(0, "done", f"Scope: {u.get('scope', 'n/a')}")
    emit(1, "start", "Drafting a research plan and search queries")
    queries = [q for q in u.get("search_queries", []) if isinstance(q, str)][: prof["queries"]] or [restated]
    emit(1, "done", "Plan: " + "; ".join(str(x) for x in u.get("plan", [])[:5]))

    # ---- 2: search (free sources)
    emit(2, "start", f"Searching: {', '.join(n for n, _ in providers)}")
    for name in missing:
        emit(2, "warn", f"{name} was skipped.")
    found: dict[str, dict] = {}
    errors: list[ResearchError] = []
    for pname, fn in providers:
        for q in queries + ([question] if pname == "Documents" else []):
            try:
                hits = fn(q, prof["per_query"])
            except ResearchError as e:
                errors.append(e)
                emit(2, "warn", f"{pname} search failed: {e}")
                break
            emit(2, "info", f"{pname}: '{q}' returned {len(hits)} result(s)")
            for h in hits:
                found.setdefault(h["url"], h)
    srcs = list(found.values())[: prof["max_sources"]]
    if not srcs and errors:
        raise errors[0]
    if not srcs:
        raise ResearchError("No sources were found for this question. Try broader wording or a different source type.")
    for i, s in enumerate(srcs, 1):
        s["id"], s["retrieved_at"] = i, datetime.now(timezone.utc).isoformat()
    emit(2, "done", f"Collected {len(srcs)} unique source(s)")

    # ---- 3: local evidence prep (no model call = no cost)
    emit(3, "start", "Trimming evidence to the most useful text (no model call, to save cost)")
    evidence = "\n\n".join(
        f"[{s['id']}] {s['title']} | {s['domain']} | published: {s['published'] or 'unknown'}\n{s['abstract'][:SNIPPET_CHARS]}"
        for s in srcs)
    emit(3, "done", f"{len(srcs)} sources ready. Only titles, abstracts, snippets or passages are used; full text is not read.")

    # ---- 4: write the report with ONE model call
    emit(4, "start", "Writing the cited report")
    schema = {"title": "str", "executive_summary": "str", "key_takeaways": ["str"],
              "sections": [{"heading": "str", "body": "markdown str"}],
              "comparison_table": {"columns": ["str"], "rows": [["str"]]},
              "interpretation": "str", "limitations": "str", "follow_ups": ["str"]}
    r = _ask(llm,
             f"Write a research report answering: {restated}\nToday's date: {datetime.now().strftime('%d %B %Y')}.\n\n"
             "Use ONLY the sources below. Rules:\n"
             "- Every factual statement must end with a citation like [2] or [1][3], using only the listed ids.\n"
             "- Ignore sources that are irrelevant. If the sources do not answer the question, say so plainly instead of guessing.\n"
             "- If sources conflict or look outdated compared with today's date, say that clearly.\n"
             "- Put your own reasoning ONLY in 'interpretation', separate from sourced facts. Mention gaps in 'limitations'.\n"
             f"- Keep the whole report under {prof['words']} words, about {prof['sections']} sections. "
             f"{FORMAT_GUIDE.get(output_format, '')}\n- comparison_table may be null. Give 3 follow_ups.\n\n"
             f"SOURCES:\n{evidence}\n\nReturn ONLY JSON: " + json.dumps(schema), usage)
    emit(4, "done", "Draft written")

    # ---- 5: validate + assemble
    emit(5, "start", "Validating citations and assembling the report")
    valid = {s["id"] for s in srcs}
    cl = lambda t: _clean_citations(str(t or ""), valid)  # noqa: E731
    sections = [{"heading": str(x.get("heading", "")).strip(), "body": cl(x.get("body", ""))}
                for x in r.get("sections", []) if isinstance(x, dict)]
    table, t = None, r.get("comparison_table")
    if isinstance(t, dict) and t.get("columns") and t.get("rows"):
        n = len(t["columns"])
        table = {"columns": [str(c) for c in t["columns"]],
                 "rows": [[cl(c) for c in (list(row) + [""] * n)[:n]] for row in t["rows"] if isinstance(row, list)]}
    summary = cl(r.get("executive_summary", ""))
    takeaways = [cl(x) for x in r.get("key_takeaways", [])]
    cited = _cited_ids(summary, *takeaways, *(s["body"] for s in sections),
                       *(c for row in (table or {}).get("rows", []) for c in row))
    used = _usage_summary(usage)
    cost = f", about ${used['approx_cost_usd']:.4f}" if used["approx_cost_usd"] is not None else ""
    names = ", ".join(n for n, _ in providers)
    report = {
        "id": uuid.uuid4().hex[:12], "question": question, "depth": depth, "sources_mode": sources,
        "output_format": output_format, "status": "Completed", "created_at": datetime.now(timezone.utc).isoformat(),
        "demo": False, "saved": False, "title": str(r.get("title") or restated)[:160],
        "executive_summary": summary, "key_takeaways": takeaways, "sections": sections, "table": table,
        "interpretation": str(r.get("interpretation", "")), "limitations": str(r.get("limitations", "")),
        "follow_ups": [str(x) for x in r.get("follow_ups", [])][:5],
        "sources": [{**s, "cited": s["id"] in cited} for s in srcs],
        "notes": [f"Sources were retrieved live from: {names}. Claims come from titles, abstracts, headlines, snippets or "
                  "document passages only, not full text.",
                  "Statements have not been independently fact-checked. Open the cited source to confirm details."]
        + ([f"Skipped: {', '.join(missing)}."] if missing else []),
        "usage": used, "activity": log,
    }
    emit(5, "done", f"Report ready with {len(cited)} cited source(s). Tokens: {used['input_tokens']} in / "
                    f"{used['output_tokens']} out{cost} on {used['model']}")
    report["activity"] = log
    return report


# ================================================================ export
def report_to_markdown(r: dict) -> str:
    md = [f"# {r['title']}", "", f"*Generated {r['created_at'][:19].replace('T', ' ')} UTC · {r['depth']} · {r['output_format']}*"]
    if r.get("demo"):
        md.append("\n> **Demo report - sample data, not the result of a real search.**")
    md += ["", "## Executive summary", r["executive_summary"], "", "## Key takeaways"] + [f"- {t}" for t in r["key_takeaways"]]
    for s in r["sections"]:
        md += ["", f"## {s['heading']}", s["body"]]
    if r.get("table"):
        t = r["table"]
        md += ["", "| " + " | ".join(t["columns"]) + " |", "|" + "---|" * len(t["columns"])]
        md += ["| " + " | ".join(c.replace("|", "/") for c in row) + " |" for row in t["rows"]]
    if r.get("interpretation"):
        md += ["", "## AI interpretation (not directly sourced)", r["interpretation"]]
    if r.get("limitations"):
        md += ["", "## Limitations", r["limitations"]]
    md += ["", "## Sources"]
    for s in r["sources"]:
        ref = f"[{s['title']}]({s['url']})" if str(s["url"]).startswith("http") else f"{s['title']} (uploaded document)"
        md.append(f"{s['id']}. {ref} - {s['domain']}" + (f", {s['published']}" if s.get("published") else ""))
    return "\n".join(md + ["", "## Notes"] + [f"- {n}" for n in r.get("notes", [])])
