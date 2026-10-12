"""Your own documents as a research source. Everything here is local and costs no API credit.

Files are parsed once, split into chunks and stored as JSON in data/docs/. Search is a small
keyword (BM25-style) ranking, so it needs no embeddings and no extra paid calls.
Only the few best-matching chunks are later sent to the language model.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from services import storage

DOC_DIR = storage.DATA_DIR / "docs"
MAX_BYTES = 10 * 1024 * 1024
CHUNK, OVERLAP = 900, 150
SUPPORTED = ["pdf", "txt", "md", "docx"]
STOP = set("the and for that with this from are was were have has had not but you your they their what when which "
           "will can how why who all any about into than then there been being its our out use using".split())


class DocumentError(Exception):
    pass


def _extract(name: str, data: bytes) -> list[tuple]:
    ext = Path(name).suffix.lower()
    if ext in (".txt", ".md"):
        return [(None, data.decode("utf-8", errors="ignore"))]
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise DocumentError("PDF support needs a package. Run: pip install pypdf") from e
        try:
            reader = PdfReader(io.BytesIO(data))
            return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
        except Exception as e:
            raise DocumentError("This PDF could not be read (it may be corrupted or password-protected).") from e
    if ext == ".docx":
        try:
            import docx
        except ImportError as e:
            raise DocumentError("Word support needs a package. Run: pip install python-docx") from e
        try:
            d = docx.Document(io.BytesIO(data))
            return [(None, "\n".join(p.text for p in d.paragraphs))]
        except Exception as e:
            raise DocumentError("This Word file could not be read.") from e
    raise DocumentError(f"Unsupported file type '{ext}'. Use: {', '.join(SUPPORTED)}.")


def _chunk(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    out, i = [], 0
    while i < len(text):
        j = min(len(text), i + CHUNK)
        if j < len(text):
            k = text.rfind(" ", i, j)
            j = k if k > i + CHUNK // 2 else j
        out.append(text[i:j])
        if j >= len(text):
            break
        i = max(j - OVERLAP, i + 1)
    return out


def add_document(name: str, data: bytes) -> dict:
    if len(data) > MAX_BYTES:
        raise DocumentError(f"{name} is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    doc_id = hashlib.sha1(data).hexdigest()[:12]
    path = DOC_DIR / f"{doc_id}.json"
    if path.exists():
        return {**json.loads(path.read_text(encoding="utf-8")), "duplicate": True}
    chunks = [{"page": pg, "text": c} for pg, txt in _extract(name, data) for c in _chunk(txt)]
    if not chunks:
        raise DocumentError(f"No readable text found in {name}. Scanned (image-only) PDFs are not supported.")
    doc = {"id": doc_id, "name": name, "size": len(data), "chunks": chunks,
           "added_at": datetime.now(timezone.utc).isoformat()}
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return doc


def _load_all() -> list[dict]:
    docs = []
    for p in DOC_DIR.glob("*.json") if DOC_DIR.exists() else []:
        try:
            docs.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return docs


def list_documents() -> list[dict]:
    return sorted(({k: d[k] for k in ("id", "name", "size", "added_at")} | {"chunks": len(d["chunks"])}
                   for d in _load_all()), key=lambda d: d["added_at"], reverse=True)


def has_documents() -> bool:
    return bool(DOC_DIR.exists() and any(DOC_DIR.glob("*.json")))


def delete_document(doc_id: str) -> None:
    (DOC_DIR / f"{doc_id}.json").unlink(missing_ok=True)


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]{3,}", text.lower()) if w not in STOP]


def search_documents(query: str, max_results: int) -> list[dict]:
    q_terms = set(_tokens(query))
    if not q_terms:
        return []
    rows = [(d, i, c) for d in _load_all() for i, c in enumerate(d["chunks"])]
    if not rows:
        return []
    toks = [Counter(_tokens(c["text"])) for _, _, c in rows]
    n = len(rows)
    df = {t: sum(1 for tk in toks if t in tk) for t in q_terms}
    scored = []
    for (d, i, c), tk in zip(rows, toks):
        s = sum((tk[t] * 2.2 / (tk[t] + 1.2)) * math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in q_terms if tk[t])
        if s > 0:
            scored.append((s, d, i, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for _, d, i, c in scored[:max_results]:
        where = f"page {c['page']}" if c.get("page") else f"part {i + 1}"
        out.append({"title": f"{d['name']} ({where})", "url": f"doc://{d['id']}#{i}", "domain": d["name"],
                    "published": d["added_at"][:10], "authors": [], "abstract": c["text"], "kind": "Document"})
    return out
