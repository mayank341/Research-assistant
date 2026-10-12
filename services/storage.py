"""Tiny JSON-file persistence for reports and settings (no database needed)."""
from __future__ import annotations

import json
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("RESEARCH_AI_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
STORE = DATA_DIR / "store.json"

DEFAULT_SETTINGS = {
    "theme": "Dark",
    "default_depth": "Standard",
    "default_sources": "Academic",
    "default_format": "Detailed Report",
    "demo_mode": False,
    "reuse_recent": True,
}


def _read() -> dict:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        STORE.replace(STORE.with_suffix(".corrupt.json"))  # keep the bad file, start fresh
        return {}


def _write(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STORE)


def load_reports() -> list[dict]:
    reports = _read().get("reports", [])
    return sorted(reports, key=lambda r: r.get("created_at", ""), reverse=True)


def upsert_report(report: dict) -> None:
    data = _read()
    reports = [r for r in data.get("reports", []) if r["id"] != report["id"]]
    reports.append(report)
    data["reports"] = reports
    _write(data)


def delete_report(report_id: str) -> None:
    data = _read()
    data["reports"] = [r for r in data.get("reports", []) if r["id"] != report_id]
    _write(data)


def load_settings() -> dict:
    return {**DEFAULT_SETTINGS, **_read().get("settings", {})}


def save_settings(settings: dict) -> None:
    data = _read()
    data["settings"] = settings
    _write(data)
