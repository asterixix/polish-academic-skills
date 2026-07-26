#!/usr/bin/env python3
"""
UAFM -- University of Applied Sciences in Nowy Sacz Repository (repozytorium eRIKA,
repozytorium.uafm.edu.pl). Runs DSpace 8, HAL+JSON. Anonymous read access for all
public items.

Available discovery filters (from /server/api/discover/search):
  title, author, subject, dateIssued, itemtype, keyword, dateAccessioned, license,
  has_content_in_original_bundle

KNOWN OUTAGE (as documented in the source TS as of 2026-07-20): repozytorium.uafm.edu.pl
returns HTTP 404 for /server/api/* and HTTP 500 for the Angular UI -- the DSpace/Tomcat
backend appears unmounted or broken. These tools are kept in the skill; they currently
always surface an HTTP error with a clear note. If/when the service returns, the public
API contract is unchanged and these commands should work without modification.

Subcommands (ported from uafm_search / uafm_get_item):
  search -- full-text + faceted discovery search.
  get    -- single item metadata by UUID.

Source: https://repozytorium.uafm.edu.pl
"""

from __future__ import annotations

import argparse
import json

import _http

API_BASE = "https://repozytorium.uafm.edu.pl/server/api"
BASE_URL = "https://repozytorium.uafm.edu.pl"
JSON_HEADERS = {"Accept": "application/json"}

OUTAGE_NOTE = (
    "Repozytorium eRIKA (repozytorium.uafm.edu.pl) is currently unavailable: the DSpace "
    "backend returns HTTP 404 for /server/api/*. When the service returns, this tool "
    "should work again without any code changes."
)

SORT_CHOICES = [
    "score,desc",
    "dc.title,asc",
    "dc.title,desc",
    "dc.date.issued,asc",
    "dc.date.issued,desc",
    "dc.date.accessioned,asc",
    "dc.date.accessioned,desc",
]


def _bool_flag(value: str) -> bool:
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError("expected true/false")


def _item_url(it: dict) -> str | None:
    handle = it.get("handle") or ""
    if handle:
        return f"{BASE_URL}/handle/{handle}"
    uuid = it.get("uuid")
    if uuid:
        return f"{BASE_URL}/items/{uuid}"
    return None


def summarize_search(raw: str) -> dict:
    data = _http.parse_json_response(raw, API_BASE)
    sr = (data.get("_embedded") or {}).get("searchResult") or {}
    objects = (sr.get("_embedded") or {}).get("objects") or []
    page = sr.get("page") or {}

    items = []
    for obj in objects:
        it = (obj.get("_embedded") or {}).get("indexableObject") or {}
        m = it.get("metadata") or {}
        abstract = _http.dc_first(m, "dc.description.abstract")
        items.append(
            {
                "uuid": it.get("uuid"),
                "handle": it.get("handle") or None,
                "url": _item_url(it),
                "title": _http.dc_first(m, "dc.title") or None,
                "authors": _http.dc_all(m, "dc.contributor.author"),
                "type": _http.dc_first(m, "dc.type") or None,
                "language": _http.dc_first(m, "dc.language.iso") or None,
                "dateIssued": _http.dc_first(m, "dc.date.issued") or None,
                "subject": _http.dc_first(m, "dc.subject") or None,
                "abstract": _http.truncate(abstract, 500) if abstract else None,
            }
        )

    return {
        "totalElements": page.get("totalElements"),
        "page": {"number": page.get("number"), "size": page.get("size"), "totalPages": page.get("totalPages")},
        "items": items,
    }


def summarize_item(raw: str) -> dict:
    it = _http.parse_json_response(raw, API_BASE)
    m = it.get("metadata") or {}
    return {
        "uuid": it.get("uuid"),
        "handle": it.get("handle") or None,
        "url": _item_url(it),
        "title": _http.dc_first(m, "dc.title") or None,
        "authors": _http.dc_all(m, "dc.contributor.author"),
        "type": _http.dc_first(m, "dc.type") or None,
        "language": _http.dc_first(m, "dc.language.iso") or None,
        "dateIssued": _http.dc_first(m, "dc.date.issued") or None,
        "dateAccessioned": _http.dc_first(m, "dc.date.accessioned") or None,
        "subject": _http.dc_all(m, "dc.subject"),
        "doi": _http.dc_first(m, "dc.identifier.doi") or None,
        "uri": _http.dc_first(m, "dc.identifier.uri") or None,
        "publisher": _http.dc_first(m, "dc.publisher") or None,
        "license": _http.dc_first(m, "dc.rights") or None,
        "lastModified": it.get("lastModified"),
        "abstract": _http.dc_first(m, "dc.description.abstract") or None,
    }


def cmd_search(args: argparse.Namespace) -> dict:
    params = [("query", args.query), ("page", str(args.page)), ("size", str(args.size)), ("sort", args.sort)]
    if args.author:
        _http.add_dspace_filter(params, "author", args.author, "contains")
    if args.title:
        _http.add_dspace_filter(params, "title", args.title, "contains")
    if args.subject:
        _http.add_dspace_filter(params, "subject", args.subject, "equals")
    if args.keyword:
        _http.add_dspace_filter(params, "keyword", args.keyword, "equals")
    if args.itemtype:
        _http.add_dspace_filter(params, "itemtype", args.itemtype, "equals")
    if args.date_issued:
        _http.add_dspace_filter(params, "dateIssued", args.date_issued, "equals")
    if args.date_accessioned:
        _http.add_dspace_filter(params, "dateAccessioned", args.date_accessioned, "equals")
    if args.license:
        _http.add_dspace_filter(params, "license", args.license, "contains")
    if args.has_full_text is not None:
        params.append(("f.has_content_in_original_bundle", f"{str(args.has_full_text).lower()},equals"))

    url = f"{API_BASE}/discover/search/objects?{_http.build_query(params)}"
    try:
        raw = _http.fetch(url, headers=JSON_HEADERS)
    except Exception as e:  # noqa: BLE001 -- append the known-outage note, mirroring the TS tool
        raise RuntimeError(f"{e}\n{OUTAGE_NOTE}") from e
    return summarize_search(raw)


def cmd_get(args: argparse.Namespace) -> dict:
    url = f"{API_BASE}/core/items/{args.uuid}"
    try:
        raw = _http.fetch(url, headers=JSON_HEADERS)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"{e}\n{OUTAGE_NOTE}") from e
    return summarize_item(raw)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="UAFM -- Repozytorium eRIKA discovery search. NOTE: backend is currently down (HTTP 404)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Full-text + faceted discovery search.")
    s.add_argument("--query", required=True, help="Full-text search expression.")
    s.add_argument("--page", type=int, default=0, help="Zero-based page number. Default: 0.")
    s.add_argument("--size", type=int, default=10, help="Results per page (1-50). Default: 10.")
    s.add_argument("--sort", choices=SORT_CHOICES, default="score,desc")
    s.add_argument("--author", help="Author filter (default op: contains).")
    s.add_argument("--title", help="Title filter (default op: contains).")
    s.add_argument("--subject", help="Subject filter (default op: equals).")
    s.add_argument("--keyword", help="Keyword filter (default op: equals).")
    s.add_argument("--itemtype", help="Document type filter (default op: equals), e.g. 'article', 'book'.")
    s.add_argument("--date-issued", dest="date_issued", help="Publication date filter (default op: equals). For ranges use Solr notation, e.g. '[2020-01-01 TO 2023-12-31],query'.")
    s.add_argument("--date-accessioned", dest="date_accessioned", help="Deposit date filter (default op: equals).")
    s.add_argument("--license", help="License filter (default op: contains), e.g. 'CC BY'.")
    s.add_argument(
        "--has-full-text",
        dest="has_full_text",
        type=_bool_flag,
        default=None,
        help="true/false -- restrict to items with full text in the original bundle.",
    )
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="Full item metadata by UUID.")
    g.add_argument("--uuid", required=True, help="Item UUID, from the 'uuid' field of search results.")
    g.set_defaults(func=cmd_get)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:  # noqa: BLE001 -- cmd_search/cmd_get already append the outage note
        _http.fail(str(e))


if __name__ == "__main__":
    main()
