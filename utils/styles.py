"""Design system: tokens, reusable HTML helpers and a small, selector-light stylesheet.

Cards use translucent surfaces and inherited text colour, so they work in both dark and light themes.
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

CSS = """
<style>
:root{
  --rs-accent:#6366f1; --rs-accent-soft:rgba(99,102,241,.14);
  --rs-border:rgba(128,128,128,.28); --rs-surface:rgba(128,128,128,.07); --rs-radius:12px;
}
.stApp, .rs-root{ font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif; }
.rs-title{ font-size:1.9rem; font-weight:700; letter-spacing:-.02em; line-height:1.2; margin:0; }
.rs-sub{ opacity:.72; margin:.3rem 0 .6rem; font-size:1rem; }
.rs-label{ font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; opacity:.62; font-weight:600; margin:0 0 .45rem; }
.rs-brand{ display:flex; align-items:center; gap:.6rem; font-weight:700; font-size:1.2rem; padding:.2rem 0 .9rem; }
.rs-brand svg{ width:28px; height:28px; }
.rs-card{ border:1px solid var(--rs-border); background:var(--rs-surface); border-radius:var(--rs-radius);
  padding:1rem 1.15rem; box-shadow:0 1px 2px rgba(0,0,0,.12); animation:rs-fade .25s ease; }
.rs-card p{ margin:0; line-height:1.6; }
.rs-card.fact{ border-left:3px solid var(--rs-accent); }
.rs-card.interp{ border-left:3px solid #f59e0b; }
.rs-badge{ display:inline-flex; align-items:center; gap:.35rem; padding:.12rem .62rem; border-radius:999px;
  font-size:.78rem; font-weight:500; border:1px solid var(--rs-border); background:var(--rs-surface); margin-right:.35rem; }
.rs-badge.ok{ color:#22c55e; border-color:rgba(34,197,94,.45); background:rgba(34,197,94,.1); }
.rs-badge.run{ color:#818cf8; border-color:rgba(129,140,248,.5); background:var(--rs-accent-soft); }
.rs-badge.err{ color:#ef4444; border-color:rgba(239,68,68,.45); background:rgba(239,68,68,.1); }
.rs-badge.warn{ color:#f59e0b; border-color:rgba(245,158,11,.45); background:rgba(245,158,11,.1); }
.rs-stage{ display:flex; align-items:center; gap:.7rem; padding:.38rem 0; font-size:.95rem; }
.rs-stage.pending{ opacity:.5; }
.rs-dot{ width:18px; height:18px; border-radius:50%; border:2px solid var(--rs-border); flex:none; box-sizing:border-box; }
.rs-stage.done .rs-dot{ background:#22c55e; border-color:#22c55e; position:relative; }
.rs-stage.done .rs-dot::after{ content:""; position:absolute; left:4px; top:0; width:4px; height:8px;
  border:solid #fff; border-width:0 2px 2px 0; transform:rotate(45deg); }
.rs-stage.active .rs-dot{ border-color:var(--rs-accent); border-top-color:transparent; animation:rs-spin .8s linear infinite; }
.rs-stage.error .rs-dot{ background:#ef4444; border-color:#ef4444; }
.rs-meta{ opacity:.7; font-size:.85rem; }
.rs-empty{ text-align:center; padding:2.2rem 1rem; }
@keyframes rs-spin{ to{ transform:rotate(360deg); } }
@keyframes rs-fade{ from{ opacity:0; transform:translateY(4px); } to{ opacity:1; transform:none; } }
@media (prefers-reduced-motion: reduce){ .rs-card, .rs-stage.active .rs-dot{ animation:none; } }
</style>
"""

DARK = {"base": "dark", "primaryColor": "#6366f1", "backgroundColor": "#0b0d12",
        "secondaryBackgroundColor": "#12151c", "textColor": "#e6e8ee", "borderColor": "#232838"}
LIGHT = {"base": "light", "primaryColor": "#4f46e5", "backgroundColor": "#ffffff",
         "secondaryBackgroundColor": "#f4f5f9", "textColor": "#14161c", "borderColor": "#dcdfe8"}


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def apply_theme(name: str) -> bool:
    """Update Streamlit's theme config. Takes effect for new page loads (refresh the browser)."""
    try:
        for k, v in (DARK if name == "Dark" else LIGHT).items():
            st._config.set_option(f"theme.{k}", v)
        return True
    except Exception:
        return False


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def badge(text: str, kind: str = "") -> str:
    return f'<span class="rs-badge {kind}">{esc(text)}</span>'


def label(text: str) -> None:
    st.markdown(f'<div class="rs-label">{esc(text)}</div>', unsafe_allow_html=True)


def fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%b %d, %Y · %H:%M")
    except (ValueError, TypeError):
        return iso or ""


def logo_svg() -> str:
    p = ROOT / "assets" / "logo.svg"
    return p.read_text() if p.exists() else ""


def empty_state(title: str, body: str) -> None:
    st.markdown(f'<div class="rs-card rs-empty"><h4>{esc(title)}</h4><p class="rs-meta">{esc(body)}</p></div>',
                unsafe_allow_html=True)
