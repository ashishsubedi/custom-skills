#!/usr/bin/env python3
"""zotero-bridge — read-only access to a local Zotero library.

Two backends, one identical JSON shape:

  * Local HTTP API (Zotero running) — http://localhost:23119/api/users/0/...
  * SQLite snapshot (Zotero closed, offline, or --sqlite-only) — copies
    zotero.sqlite{, -wal, -shm} into a TemporaryDirectory and opens it mode=ro.

Nothing here writes to Zotero files. Standard library only.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Zotero top-level "paper" items; children never appear in search/recent.
CHILD_TYPES = {"attachment", "annotation", "note"}

# Zotero.Annotations constants (chrome/content/zotero/xpcom/annotations.js).
ANNOTATION_TYPES = {
    0: "highlight",  # legacy pre-Zotero-7 convention
    1: "highlight",
    2: "note",
    3: "image",
    4: "ink",
    5: "underline",
    6: "text",
}

STOPWORDS = {
    "a", "all", "an", "and", "are", "as", "at", "be", "been", "based", "by",
    "can", "do", "for", "from", "has", "have", "how", "in", "into", "is", "it",
    "its", "need", "new", "no", "not",
    "of", "on", "onto", "or", "our", "over", "study", "that", "the", "their",
    "this", "those", "these", "through", "to", "toward", "towards", "under",
    "understand", "understanding", "using", "used", "via", "was", "we", "were",
    "what", "when", "where", "which", "why", "with", "you", "your",
}


# --------------------------------------------------------------------------- #
# Slugging & normalization helpers
# --------------------------------------------------------------------------- #

def _ascii_fold(value: object) -> str:
    """Lowercase ASCII-only fold (unicode accents degrade, never crash)."""
    text = unicodedata.normalize("NFKD", "" if value is None else str(value))
    return text.encode("ascii", "ignore").decode("ascii").lower()


def _clean_slug(value: object) -> str:
    text = _ascii_fold(value)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text)


def _title_words(title: object) -> list[str]:
    words = re.findall(r"[a-z0-9]+", _ascii_fold(title))
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def _first_author_last(authors: object) -> str:
    if not authors:
        return ""
    first = authors[0]
    if isinstance(first, dict):
        name = first.get("lastName") or first.get("name") or first.get("firstName") or ""
    else:
        name = str(first)
    name = name.split(",", 1)[0]  # "Last, First" -> "Last"
    tokens = re.findall(r"[a-z0-9]+", _ascii_fold(name))
    return tokens[-1] if tokens else ""


def make_paper_slug(authors, year, title, item_key) -> str:
    """Citekey-independent, Logseq-safe slug.

    <firstAuthorLastName>-<year>-<first-two-or-three-title-words>, or
    <title-slug>-<itemKey> when author/year is unavailable.
    """
    key = _clean_slug(item_key)
    words = _title_words(title)[:3]
    author = _first_author_last(authors)
    digits = re.sub(r"[^0-9]", "", "" if year is None else str(year))[:4]

    if author and len(digits) == 4:
        slug = "-".join([author, digits] + words)
    else:
        slug = "-".join(words + ([key] if key else [])) or "paper"

    slug = _clean_slug(slug)
    if len(slug) > 50:
        slug = slug[:50].rstrip("-")
        if "-" in slug:
            slug = slug.rsplit("-", 1)[0]
    return slug or (key or "paper")[:50]


def extract_year(value: object) -> str:
    match = re.search(r"(?:1[5-9]|20|21)\d{2}", "" if value is None else str(value))
    return match.group(0) if match else ""


def _sort_tokens(value: object) -> list[int]:
    """Numeric-ish sort key for Zotero's TEXT sortIndex and page labels."""
    tokens = [int(n) for n in re.findall(r"\d+", "" if value is None else str(value))]
    return tokens or [0]


def _annotation_sort(ann: dict) -> tuple:
    return (
        _sort_tokens(ann.get("sortIndex")),
        _sort_tokens(ann.get("pageLabel")),
        str(ann.get("annotationKey") or ""),
    )


def _pdf_uri(attachment_key: object, page: object = None) -> str:
    if not attachment_key:
        return ""
    uri = f"zotero://open-pdf/library/items/{attachment_key}"
    if page is not None and str(page) != "":
        uri += "?page=" + urllib.parse.quote(str(page), safe="")
    return uri


# Canonical payloads — both backends funnel through these functions so that
# Local API and SQLite output is byte-for-byte the same shape.

def item_payload(raw: dict, backend: str) -> dict:
    key = raw.get("itemKey") or ""
    authors = raw.get("authors") or []
    return {
        "backend": backend,
        "itemKey": key,
        "slug": make_paper_slug(authors, raw.get("year"), raw.get("title"), key),
        "title": raw.get("title") or "",
        "authors": authors,
        "year": raw.get("year") or "",
        "itemType": raw.get("itemType") or "",
        "abstract": raw.get("abstract") or "",
        "tags": raw.get("tags") or [],
        "collections": [c.get("name", "") if isinstance(c, dict) else str(c)
                        for c in (raw.get("collections") or [])],
        "attachmentKey": raw.get("attachmentKey") or "",
        "pdfPath": raw.get("pdfPath") or "",
        "zoteroSelectUri": f"zotero://select/library/items/{key}" if key else "",
        "zoteroPdfUri": _pdf_uri(raw.get("attachmentKey")),
    }


def annotation_payload(item_key: str, annotations: list[dict], backend: str) -> dict:
    ordered = sorted(annotations, key=_annotation_sort)
    return {
        "backend": backend,
        "itemKey": item_key,
        "annotations": [
            {
                "annotationKey": a.get("annotationKey") or "",
                "attachmentKey": a.get("attachmentKey") or "",
                "type": a.get("type") or "",
                "color": a.get("color") or "",
                "pageLabel": str(a.get("pageLabel") or ""),
                "sortIndex": str(a.get("sortIndex") or ""),
                "text": a.get("text") or "",
                "comment": a.get("comment") or "",
                "zoteroPdfUri": _pdf_uri(a.get("attachmentKey"), a.get("pageLabel")),
            }
            for a in ordered
        ],
    }


def collection_payload(collections: list[dict], backend: str) -> dict:
    return {
        "backend": backend,
        "collections": [
            {
                "key": c.get("key") or "",
                "name": c.get("name") or "",
                "parentKey": c.get("parentKey") or "",
                "itemCount": int(c.get("itemCount") or 0),
            }
            for c in sorted(collections, key=lambda c: (c.get("name") or "").lower())
        ],
    }


def bibtex_key(bibtex: str) -> str:
    match = re.search(r"@[A-Za-z]+\s*\{\s*([^,\s}]+)", bibtex or "")
    return match.group(1) if match else ""


def extract_pdf_text(
    pdf_path: str | Path,
    first_page: int | None = None,
    last_page: int | None = None,
) -> tuple[str, str]:
    """Extract reading-order text from a PDF (safe for 2-column academic papers).

    Uses ``pdftotext`` without ``-layout`` first so multi-column PDFs stay in
    reading order, falling back to ``pypdf`` or ``fitz`` (PyMuPDF) if available.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        cmd = [pdftotext]
        if first_page is not None:
            cmd.extend(["-f", str(first_page)])
        if last_page is not None:
            cmd.extend(["-l", str(last_page)])
        cmd.extend([str(path), "-"])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return "pdftotext", proc.stdout
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"pdftotext failed ({proc.returncode}): {stderr}")

    try:
        pypdf = importlib.import_module("pypdf")
        reader = pypdf.PdfReader(str(path))
        start = max(0, (first_page - 1) if first_page else 0)
        end = min(len(reader.pages), last_page if last_page else len(reader.pages))
        pages = [(reader.pages[i].extract_text() or "") for i in range(start, end)]
        return "pypdf", "\f".join(pages)
    except ImportError:
        pass

    try:
        fitz = importlib.import_module("fitz")
        with fitz.open(str(path)) as doc:
            start = max(0, (first_page - 1) if first_page else 0)
            end = min(len(doc), last_page if last_page else len(doc))
            pages = [doc[i].get_text("text") for i in range(start, end)]
        return "pymupdf", "\f".join(pages)
    except ImportError:
        pass

    raise RuntimeError(
        "No PDF text extractor found (install poppler `pdftotext`, `pypdf`, or `pymupdf`)."
    )


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #

class APIBackend:
    """Primary read-only backend: Zotero's local HTTP API."""

    name = "local-api"

    def __init__(self, api_url: str, zotero_dir: Path):
        self.api_url = api_url.rstrip("/")
        self.zotero_dir = zotero_dir
        self._raw: list[dict] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def _get(self, path: str, raw: bool = False):
        url = self.api_url + path
        request = urllib.request.Request(url, headers={"User-Agent": "zotero-bridge/1.0"})
        with urllib.request.urlopen(request, timeout=2) as response:
            body = response.read().decode("utf-8", "replace")
        return body if raw else json.loads(body)

    def raw_items(self) -> list[dict]:
        if self._raw is None:
            items: list[dict] = []
            start = 0
            while True:
                page = self._get(f"/items?limit=1000&start={start}")
                items.extend(page)
                if len(page) < 1000:
                    break
                start += 1000
            self._raw = items
        return self._raw

    def children_of(self, key: str) -> list[dict]:
        return [i for i in self.raw_items()
                if (i.get("data") or {}).get("parentItem") == key]

    def items(self) -> list[dict]:
        result = []
        for api_item in self.raw_items():
            data = api_item.get("data") or {}
            if data.get("itemType") in CHILD_TYPES or data.get("deleted"):
                continue
            result.append(self._canonical(api_item))
        return result

    def _canonical(self, api_item: dict) -> dict:
        data = api_item.get("data") or {}
        meta = api_item.get("meta") or {}
        key = api_item.get("key") or data.get("key") or ""
        creators = data.get("creators") or []
        authors = []
        for creator in creators:
            if creator.get("creatorType", "author") in ("author", "bookAuthor", ""):
                name = " ".join(p for p in (creator.get("firstName"), creator.get("lastName")) if p)
                authors.append(name.strip() or creator.get("lastName", ""))
        if not authors:
            authors = [" ".join(p for p in (c.get("firstName"), c.get("lastName")) if p).strip()
                       for c in creators]

        attachments = [c for c in self.children_of(key)
                       if (c.get("data") or {}).get("itemType") == "attachment"]
        pdf = next((c for c in attachments
                    if (c.get("data") or {}).get("contentType") == "application/pdf"), None)
        pdf = pdf or (attachments[0] if attachments else None)
        pdf_data = (pdf.get("data") or {}) if pdf else {}
        pdf_key = pdf.get("key", "") if pdf else ""
        filename = pdf_data.get("filename") or ""
        pdf_path = str(self.zotero_dir / "storage" / pdf_key / filename) if (pdf_key and filename) else ""

        return {
            "itemKey": key,
            "title": data.get("title") or "",
            "authors": [a for a in authors if a],
            "year": extract_year(data.get("date") or meta.get("parsedDate")),
            "itemType": data.get("itemType") or "",
            "abstract": data.get("abstractNote") or "",
            "tags": [t.get("tag", "") for t in (data.get("tags") or [])],
            "collections": list(data.get("collections") or []),
            "dateAdded": data.get("dateAdded") or "",
            "attachmentKey": pdf_key,
            "pdfPath": pdf_path,
            "_collectionKeys": list(data.get("collections") or []),
        }

    def item(self, key: str) -> dict | None:
        for raw in self.items():
            if raw["itemKey"] == key:
                return raw
        try:
            api_item = self._get(f"/items/{urllib.parse.quote(key)}")
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
            return None
        data = api_item.get("data") or {}
        if data.get("itemType") in CHILD_TYPES:
            return None
        self._raw.append(api_item)
        return self._canonical(api_item)

    def annotations(self, item_key: str) -> list[dict]:
        attachment_keys = {c.get("key") for c in self.children_of(item_key)
                           if (c.get("data") or {}).get("itemType") == "attachment"}
        result = []
        for api_item in self.raw_items():
            data = api_item.get("data") or {}
            if data.get("itemType") != "annotation" or data.get("parentItem") not in attachment_keys:
                continue
            ann_type = data.get("annotationType") or ""
            result.append({
                "annotationKey": api_item.get("key") or "",
                "attachmentKey": data.get("parentItem") or "",
                "type": ANNOTATION_TYPES.get(ann_type, ann_type) if isinstance(ann_type, int) else ann_type,
                "color": data.get("annotationColor") or "",
                "pageLabel": data.get("annotationPageLabel") or "",
                "sortIndex": data.get("annotationSortIndex") or "",
                "text": data.get("annotationText") or "",
                "comment": data.get("annotationComment") or "",
            })
        return result

    def collections(self) -> list[dict]:
        result = []
        start = 0
        while True:
            page = self._get(f"/collections?limit=1000&start={start}")
            for api_col in page:
                data = api_col.get("data") or {}
                meta = api_col.get("meta") or {}
                parent = data.get("parentCollection")
                result.append({
                    "key": api_col.get("key") or "",
                    "name": data.get("name") or "",
                    "parentKey": parent if isinstance(parent, str) else "",
                    "itemCount": meta.get("numItems") or 0,
                })
            if len(page) < 1000:
                break
            start += 1000
        return result

    def bibtex(self, key: str) -> str:
        text = self._get(f"/items/{urllib.parse.quote(key)}?format=bibtex", raw=True).strip()
        return text if text.startswith("@") else ""


def open_zotero_snapshot(zotero_dir: Path) -> tuple[sqlite3.Connection, tempfile.TemporaryDirectory]:
    """Copy Zotero DB (+ WAL/SHM) to a temp dir; open the copy read-only."""
    tmp = tempfile.TemporaryDirectory(prefix="zotero_ro_")
    try:
        for name in ("zotero.sqlite", "zotero.sqlite-wal", "zotero.sqlite-shm"):
            src = zotero_dir / name
            if src.exists():
                shutil.copy2(src, Path(tmp.name) / name)
        db_path = Path(tmp.name) / "zotero.sqlite"
        if not db_path.exists():
            raise FileNotFoundError(f"No zotero.sqlite in {zotero_dir}")
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        return con, tmp
    except Exception:
        tmp.cleanup()
        raise


class SQLiteBackend:
    """Offline fallback: WAL-safe read-only snapshot of zotero.sqlite."""

    name = "sqlite"

    def __init__(self, zotero_dir: Path):
        self.zotero_dir = zotero_dir
        self.con, self._tmp = open_zotero_snapshot(zotero_dir)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
        return False

    def close(self):
        self.con.close()
        self._tmp.cleanup()

    # Schema verified against Zotero 10.0.9's zotero.sqlite (read-only copy).
    def _field_map(self) -> dict[int, dict[str, str]]:
        out: dict[int, dict[str, str]] = {}
        sql = ("SELECT id.itemID AS item_id, f.fieldName AS field, v.value AS value "
               "FROM itemData id JOIN fields f ON f.fieldID = id.fieldID "
               "JOIN itemDataValues v ON v.valueID = id.valueID")
        for row in self.con.execute(sql):
            out.setdefault(row["item_id"], {})[row["field"]] = row["value"]
        return out

    def _creator_map(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        sql = ("SELECT ic.itemID AS item_id, c.firstName AS first, c.lastName AS last, "
               "ct.creatorType AS kind, ic.orderIndex AS ord "
               "FROM itemCreators ic JOIN creators c ON c.creatorID = ic.creatorID "
               "LEFT JOIN creatorTypes ct ON ct.creatorTypeID = ic.creatorTypeID "
               "ORDER BY ic.itemID, ic.orderIndex")
        for row in self.con.execute(sql):
            name = " ".join(p for p in (row["first"], row["last"]) if p).strip() or (row["last"] or "")
            if name:
                out.setdefault(row["item_id"], []).append(name)
        return out

    def _tag_map(self) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        sql = ("SELECT it.itemID AS item_id, t.name AS name FROM itemTags it "
               "JOIN tags t ON t.tagID = it.tagID ORDER BY it.itemID, t.name")
        for row in self.con.execute(sql):
            out.setdefault(row["item_id"], []).append(row["name"])
        return out

    def _collection_map(self) -> dict[int, list[dict]]:
        out: dict[int, list[dict]] = {}
        sql = ("SELECT ci.itemID AS item_id, c.key AS key, c.collectionName AS name "
               "FROM collectionItems ci JOIN collections c ON c.collectionID = ci.collectionID "
               "ORDER BY ci.itemID, c.collectionName")
        for row in self.con.execute(sql):
            out.setdefault(row["item_id"], []).append({"key": row["key"], "name": row["name"]})
        return out

    def _attachment_map(self) -> dict[int, list[sqlite3.Row]]:
        out: dict[int, list[sqlite3.Row]] = {}
        sql = ("SELECT att.itemID AS item_id, att.parentItemID AS parent_id, att.linkMode AS link_mode, "
               "att.contentType AS content_type, att.path AS path, i.key AS key "
               "FROM itemAttachments att JOIN items i ON i.itemID = att.itemID "
               "WHERE att.parentItemID IS NOT NULL ORDER BY att.itemID")
        for row in self.con.execute(sql):
            out.setdefault(row["parent_id"], []).append(row)
        return out

    def _canonical(self, row: sqlite3.Row, fields, creators, tags, collections, attachments) -> dict:
        item_id = row["item_id"]
        data = fields.get(item_id, {})
        key = row["key"]
        atts = attachments.get(item_id, [])
        pdf = next((a for a in atts if a["content_type"] == "application/pdf"), None)
        pdf = pdf or (atts[0] if atts else None)
        pdf_key = pdf["key"] if pdf else ""
        pdf_path = ""
        if pdf:
            path = pdf["path"] or ""
            if path.startswith("storage:"):
                pdf_path = str(self.zotero_dir / "storage" / pdf_key / path[len("storage:"):])
            elif path:
                pdf_path = str(Path(path) if os.path.isabs(path) else self.zotero_dir / path)
        return {
            "itemKey": key,
            "title": data.get("title") or "",
            "authors": creators.get(item_id, []),
            "year": extract_year(data.get("date")),
            "itemType": row["item_type"],
            "abstract": data.get("abstractNote") or "",
            "tags": tags.get(item_id, []),
            "collections": collections.get(item_id, []),
            "dateAdded": row["date_added"] or "",
            "attachmentKey": pdf_key,
            "pdfPath": pdf_path,
            "_collectionKeys": [c["key"] for c in collections.get(item_id, [])],
        }

    def items(self) -> list[dict]:
        fields = self._field_map()
        creators = self._creator_map()
        tags = self._tag_map()
        collections = self._collection_map()
        attachments = self._attachment_map()
        sql = ("SELECT i.itemID AS item_id, i.key AS key, it.typeName AS item_type, "
               "i.dateAdded AS date_added FROM items i "
               "JOIN itemTypes it ON it.itemTypeID = i.itemTypeID "
               "WHERE it.typeName NOT IN ('attachment', 'annotation', 'note') "
               "AND i.itemID NOT IN (SELECT itemID FROM deletedItems) "
               "ORDER BY i.dateAdded DESC, i.itemID DESC")
        return [self._canonical(r, fields, creators, tags, collections, attachments)
                for r in self.con.execute(sql)]

    def item(self, key: str) -> dict | None:
        return next((r for r in self.items() if r["itemKey"] == key), None)

    def annotations(self, item_key: str) -> list[dict]:
        sql = ("SELECT ia.itemID AS item_id, i.key AS annotation_key, att.key AS attachment_key, "
               "ia.type AS type, ia.color AS color, ia.pageLabel AS page_label, "
               "ia.sortIndex AS sort_index, ia.text AS text, ia.comment AS comment "
               "FROM itemAnnotations ia "
               "JOIN items i ON i.itemID = ia.itemID "
               "JOIN items att ON att.itemID = ia.parentItemID "
               "WHERE att.key IN (SELECT i2.key FROM itemAttachments a2 "
               "                  JOIN items i2 ON i2.itemID = a2.itemID "
               "                  WHERE a2.parentItemID = (SELECT itemID FROM items WHERE key = ?)) "
               "AND ia.itemID NOT IN (SELECT itemID FROM deletedItems)")
        result = []
        for row in self.con.execute(sql, (item_key,)):
            raw_type = row["type"]
            ann_type = ANNOTATION_TYPES.get(raw_type, raw_type) if isinstance(raw_type, int) else raw_type
            result.append({
                "annotationKey": row["annotation_key"],
                "attachmentKey": row["attachment_key"],
                "type": ann_type,
                "color": row["color"] or "",
                "pageLabel": row["page_label"] or "",
                "sortIndex": row["sort_index"] or "",
                "text": row["text"] or "",
                "comment": row["comment"] or "",
            })
        return result

    def collections(self) -> list[dict]:
        sql = ("SELECT c.key AS key, c.collectionName AS name, pc.key AS parent_key, "
               "COUNT(ci.itemID) AS item_count FROM collections c "
               "LEFT JOIN collections pc ON pc.collectionID = c.parentCollectionID "
               "LEFT JOIN collectionItems ci ON ci.collectionID = c.collectionID "
               "AND ci.itemID NOT IN (SELECT itemID FROM deletedItems) "
               "WHERE c.collectionID NOT IN (SELECT collectionID FROM deletedCollections) "
               "GROUP BY c.collectionID ORDER BY c.collectionName")
        return [{"key": r["key"], "name": r["name"], "parentKey": r["parent_key"] or "",
                 "itemCount": r["item_count"]} for r in self.con.execute(sql)]

    def bibtex(self, key: str) -> str:
        raw = self.item(key)
        if not raw:
            return ""
        authors = " and ".join(raw["authors"])
        bib_key = make_paper_slug(raw["authors"], raw["year"], raw["title"], key).replace("-", "")
        if not bib_key or bib_key[0].isdigit():
            bib_key = "paper" + bib_key
        lines = [f"@article{{{bib_key},", f"  title = {{{raw['title']}}},"]
        if authors:
            lines.append(f"  author = {{{authors}}},")
        if raw["year"]:
            lines.append(f"  year = {{{raw['year']}}},")
        if raw.get("abstract"):
            lines.append(f"  abstract = {{{raw['abstract']}}},")
        lines.append("}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Command dispatch
# --------------------------------------------------------------------------- #

def _matches(raw: dict, query: str) -> bool:
    haystack = " ".join([
        raw["title"], " ".join(raw["authors"]), " ".join(raw["tags"]),
        " ".join(c.get("name", "") if isinstance(c, dict) else str(c)
                 for c in raw["collections"]),
    ]).lower()
    return all(term in haystack for term in query.lower().split())


def run_command(backend, args) -> dict:
    if args.command == "search":
        items = backend.items()
        if args.collection:
            wanted = args.collection.lower()
            col_keys = {c["key"].lower() for c in backend.collections()
                        if wanted == c["key"].lower() or wanted == c["name"].lower()}
            items = [i for i in items
                     if {k.lower() for k in (i.get("_collectionKeys") or [])} & col_keys]
        results = [item_payload(i, backend.name) for i in items if _matches(i, args.query)]
        results = results[:args.limit]
        return {"backend": backend.name, "query": args.query, "limit": args.limit,
                "count": len(results), "results": results}

    if args.command == "recent":
        items = sorted(backend.items(), key=lambda i: i.get("dateAdded") or "", reverse=True)
        results = [item_payload(i, backend.name) for i in items[:args.limit]]
        return {"backend": backend.name, "limit": args.limit,
                "count": len(results), "results": results}

    if args.command == "item":
        raw = backend.item(args.item_key)
        if not raw:
            raise SystemExit(f"Item not found: {args.item_key}")
        return item_payload(raw, backend.name)

    if args.command == "annotations":
        return annotation_payload(args.item_key, backend.annotations(args.item_key), backend.name)

    if args.command == "collections":
        return collection_payload(backend.collections(), backend.name)

    if args.command == "bibtex":
        text = backend.bibtex(args.item_key)
        if not text:
            raise SystemExit(f"No BibTeX available for: {args.item_key}")
        return {"backend": backend.name, "itemKey": args.item_key,
                "bibtexKey": bibtex_key(text), "bibtex": text}

    if args.command == "text":
        raw = backend.item(args.item_key)
        if not raw:
            raise SystemExit(f"Item not found: {args.item_key}")
        pdf_path = raw.get("pdfPath") or ""
        if not pdf_path:
            raise SystemExit(f"No PDF attachment for: {args.item_key}")
        try:
            extractor, extracted = extract_pdf_text(
                pdf_path, first_page=args.first_page, last_page=args.last_page
            )
        except (FileNotFoundError, RuntimeError) as exc:
            raise SystemExit(str(exc)) from exc
        truncated = False
        if args.max_chars is not None and len(extracted) > args.max_chars:
            extracted = extracted[:args.max_chars]
            truncated = True
        return {
            "backend": backend.name,
            "itemKey": args.item_key,
            "attachmentKey": raw.get("attachmentKey") or "",
            "pdfPath": pdf_path,
            "extractor": extractor,
            "charCount": len(extracted),
            "truncated": truncated,
            "text": extracted,
        }

    raise SystemExit(f"Unknown command: {args.command}")


def pretty_print(payload: dict, command: str) -> None:
    backend = payload.get("backend", "")
    if command in ("search", "recent"):
        print(f"[{backend}] {command}: {payload.get('count', 0)} result(s)")
        for item in payload.get("results", []):
            print(f"  {item['itemKey']}  {item['slug']}  {item['title']} ({item['year']})")
    elif command == "item":
        print(f"[{backend}] {payload['title']} ({payload['year']}) — {payload['slug']}")
        print(f"  authors: {', '.join(payload['authors'])}")
        print(f"  PDF: {payload['pdfPath'] or '(none)'}")
        print(f"  Zotero: {payload['zoteroSelectUri']}")
    elif command == "annotations":
        print(f"[{backend}] {len(payload['annotations'])} annotation(s) on {payload['itemKey']}")
        for ann in payload["annotations"]:
            print(f"  p.{ann['pageLabel']} [{ann['type']}/{ann['color']}] {ann['text'][:80]}"
                  f" — {ann['comment']}")
    elif command == "collections":
        print(f"[{backend}] {len(payload['collections'])} collection(s)")
        for col in payload["collections"]:
            print(f"  {col['key']}  {col['name']}  ({col['itemCount']} items)")
    elif command == "bibtex":
        print(f"[{backend}] {payload['bibtexKey']}\n{payload['bibtex']}")
    elif command == "text":
        suffix = " (truncated)" if payload.get("truncated") else ""
        print(f"[{backend}/{payload.get('extractor', '')}] {payload['itemKey']} "
              f"({payload.get('charCount', 0)} chars{suffix})\n")
        print(payload.get("text", ""))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    # Subparser-level copy of global options using SUPPRESS defaults so flags work
    # both before and after the subcommand without clobbering root-level flags.
    sub_common = argparse.ArgumentParser(add_help=False)
    sub_common.add_argument("--zotero-dir", default=argparse.SUPPRESS,
                            help="Zotero data directory (default: $ZOTERO_DIR or ~/Zotero)")
    sub_common.add_argument("--api-url", default=argparse.SUPPRESS,
                            help="Zotero local API base URL")
    sub_common.add_argument("--sqlite-only", action="store_true", default=argparse.SUPPRESS,
                            help="Skip the local API; use SQLite snapshot only")
    sub_common.add_argument("--pretty", action="store_true", default=argparse.SUPPRESS,
                            help="Print a human-readable summary")

    parser = argparse.ArgumentParser(
        prog="zotero-bridge",
        description="Read-only Zotero access via local API with offline SQLite fallback.",
    )
    parser.add_argument("--zotero-dir", default=os.environ.get("ZOTERO_DIR") or str(Path.home() / "Zotero"),
                        help="Zotero data directory (default: $ZOTERO_DIR or ~/Zotero)")
    parser.add_argument("--api-url", default=os.environ.get("ZOTERO_API_URL") or "http://localhost:23119/api/users/0",
                        help="Zotero local API base URL")
    parser.add_argument("--sqlite-only", action="store_true", help="Skip the local API; use SQLite snapshot only")
    parser.add_argument("--pretty", action="store_true", help="Print a human-readable summary")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", parents=[sub_common], help="Search title, author, tag, or collection")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--collection", help="Collection name or key")

    recent = sub.add_parser("recent", parents=[sub_common], help="Most recently added top-level items")
    recent.add_argument("--limit", type=int, default=10)

    item = sub.add_parser("item", parents=[sub_common], help="Full metadata for one item")
    item.add_argument("item_key")

    annotations = sub.add_parser("annotations", parents=[sub_common], help="All highlights and margin notes for an item")
    annotations.add_argument("item_key")

    sub.add_parser("collections", parents=[sub_common], help="List collections with item counts")

    bibtex = sub.add_parser("bibtex", parents=[sub_common], help="Zotero BibTeX entry (API export with offline synthesis)")
    bibtex.add_argument("item_key")

    text = sub.add_parser("text", parents=[sub_common], help="Extract reading-order text from the item's PDF")
    text.add_argument("item_key")
    text.add_argument("--first-page", type=int, default=None, help="First 1-based page to extract")
    text.add_argument("--last-page", type=int, default=None, help="Last 1-based page to extract")
    text.add_argument("--max-chars", type=int, default=None, help="Truncate extracted text to at most N chars")
    return parser


def select_backend(args):
    zotero_dir = Path(args.zotero_dir).expanduser()
    if not args.sqlite_only:
        try:
            api = APIBackend(args.api_url, zotero_dir)
            api.items()  # fail fast on network/HTTP/JSON errors
            return api
        except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError):
            pass
    return SQLiteBackend(zotero_dir)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    backend = select_backend(args)
    try:
        payload = run_command(backend, args)
    finally:
        if isinstance(backend, SQLiteBackend):
            backend.close()
    if args.pretty:
        pretty_print(payload, args.command)
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
