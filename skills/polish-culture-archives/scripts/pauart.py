#!/usr/bin/env python3
"""PAUart -- Polska Akademia Umiejetnosci (PAU) art-works catalogue
(Navigart / Collectio engine).

UI: http://www.pauart.pl/app  --  HTTP API: POST /api/search (JSON, no key).

Subcommands mirror the original MCP tools:
  search        -> POST /api/search with a multi_match query (Elasticsearch-style)
  get-artwork   -> POST /api/search with an ids query for a single record
"""

from __future__ import annotations

import argparse
import json
import sys

from _http import fail, print_result, request_json

API_BASE = "http://www.pauart.pl/api"
SEARCH_URL = f"{API_BASE}/search"
SITE_APP = "http://www.pauart.pl/app"
JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _tag_labels(art: dict) -> list[str]:
    tags = (art.get("description") or {}).get("tags")
    if not isinstance(tags, list):
        return []
    out = []
    for t in tags:
        if not isinstance(t, dict):
            continue
        labels = t.get("labels") or {}
        pl = labels.get("pl") or labels.get("en")
        if isinstance(pl, str) and pl:
            out.append(pl)
    return out


def _preview_path(art: dict):
    previews = art.get("previews") or []
    if not previews or not isinstance(previews[0], dict):
        return None
    ref = previews[0].get("ref") or {}
    thumbnails = ref.get("thumbnails") or {}
    path = (
        (thumbnails.get("medium") or {}).get("path")
        or (thumbnails.get("small") or {}).get("path")
        or ref.get("path")
    )
    return path if isinstance(path, str) else None


def _compact_artwork(art: dict) -> dict:
    object_types = art.get("objectTypes") or []
    ot = None
    if object_types and isinstance(object_types[0], dict):
        ot = (object_types[0].get("labels") or {}).get("pl")
    description = art.get("description") or {}
    return {
        "id": art.get("_id"),
        "title": description.get("title"),
        "inventoryNumber": art.get("inventoryNumber"),
        "copyright": art.get("copyright"),
        "objectType": ot if isinstance(ot, str) else None,
        "tags": _tag_labels(art),
        "dimensions": art.get("dimensions") if isinstance(art.get("dimensions"), str) else None,
        "previewPath": _preview_path(art),
        "ui": SITE_APP,
    }


def _summarize_search(data, artworks_only: bool) -> dict:
    content = data.get("content") if isinstance(data, dict) else None
    if not isinstance(content, list):
        content = []
    rows = content
    if artworks_only:
        rows = [x for x in content if isinstance(x, dict) and x.get("_type") == "artwork"]
    items = []
    for x in rows:
        if not isinstance(x, dict):
            continue
        if x.get("_type") == "artwork":
            items.append(_compact_artwork(x))
        else:
            labels = x.get("labels") or {}
            items.append({
                "_type": x.get("_type"),
                "id": x.get("_id"),
                "label": labels.get("pl") or labels.get("en"),
            })
    return {
        "totalElements": data.get("totalElements") if isinstance(data, dict) else None,
        "totalPages": data.get("totalPages") if isinstance(data, dict) else None,
        "page": data.get("number") if isinstance(data, dict) else None,
        "pageSize": data.get("size") if isinstance(data, dict) else None,
        "artworksOnly": artworks_only,
        "items": items,
    }


def _summarize_artwork(data) -> dict:
    content = data.get("content") if isinstance(data, dict) else None
    if not isinstance(content, list):
        content = []
    art = next((x for x in content if isinstance(x, dict) and x.get("_type") == "artwork"), None)
    if art is None:
        return {"error": "not_found", "raw": data}
    return _compact_artwork(art)


def _build_search_body(query: dict, page: int, size: int) -> bytes:
    body = {
        "query": query,
        "options": {"trash": "NOT_REMOVED"},
        "pageRequest": {"pageSize": size, "pageNumber": page},
    }
    return json.dumps(body).encode("utf-8")


def cmd_search(args: argparse.Namespace) -> None:
    body = _build_search_body({"multi_match": {"query": args.query, "fields": ["_all"]}}, args.page, args.size)
    try:
        data = request_json(SEARCH_URL, method="POST", headers=JSON_HEADERS, data=body)
    except RuntimeError as e:
        fail(f"Error calling pauart_search: {e}")
        return
    print_result(_summarize_search(data, args.artworks_only))


def cmd_get_artwork(args: argparse.Namespace) -> None:
    body = _build_search_body({"ids": {"values": [args.id]}}, 0, 1)
    try:
        data = request_json(SEARCH_URL, method="POST", headers=JSON_HEADERS, data=body)
    except RuntimeError as e:
        fail(f"Error calling pauart_get_artwork: {e}")
        return
    print_result(_summarize_artwork(data))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pauart.py",
        description="PAUart (pauart.pl) -- PAU fine-arts catalogue, Collectio/Elasticsearch search API.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("search", help="Search the PAUart collection catalogue.")
    ps.add_argument("--query", required=True, help="Search phrase (Polish or English).")
    ps.add_argument("--page", type=int, default=0, help="Page number, 0-based. Default 0.")
    ps.add_argument("--size", type=int, default=15, help="Results per page (1-50). Default 15.")
    ps.add_argument("--artworks-only", action=argparse.BooleanOptionalAction, default=True,
                     help="Drop non-artwork hits (dictionary entries, etc.) from this page. Default true.")
    ps.set_defaults(func=cmd_search)

    pg = sub.add_parser("get-artwork", help="Fetch one artwork record by catalogue id.")
    pg.add_argument("--id", required=True, help="Artwork _id from pauart_search results, e.g. AN_KIII_150_16476.")
    pg.set_defaults(func=cmd_get_artwork)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
