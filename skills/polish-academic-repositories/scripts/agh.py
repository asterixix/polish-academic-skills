#!/usr/bin/env python3
"""
AGH University of Krakow Repository (repo.agh.edu.pl).
100,000+ records (theses, articles, technical reports, dissertations).
Runs DSpace 7, HAL+JSON. Anonymous read access for all public items.

Note: the JSON HAL API lives on api.repo.agh.edu.pl -- repo.agh.edu.pl/server/api
serves the Angular SPA (HTML), not REST.

IMPORTANT: GET /server/api/core/items (list all) is admin-only -- always use
the /discover/search/objects endpoint for search.

Subcommands (ported from agh_search / agh_get_item):
  search -- full-text + faceted discovery search. Retries once, dropping all
            filters, if the filtered query returns HTTP 400/404 (some AGH
            discovery filter combinations are known to error).
  get    -- single item metadata by UUID.

Source: https://repo.agh.edu.pl
"""

import argparse
import json

import _http

API_BASE = "https://api.repo.agh.edu.pl/server/api"
HANDLE_BASE = "https://repo.agh.edu.pl/handle"
JSON_HEADERS = {"Accept": "application/json"}

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
        handle = it.get("handle") or ""
        items.append(
            {
                "uuid": it.get("uuid"),
                "handle": handle or None,
                "url": f"{HANDLE_BASE}/{handle}" if handle else None,
                "title": _http.dc_first(m, "dc.title") or None,
                "titleAlt": _http.dc_first(m, "dc.title.alternative") or None,
                "authors": _http.dc_all(m, "dc.contributor.author"),
                "type": _http.dc_first(m, "dc.type") or None,
                "language": _http.dc_first(m, "dc.language.iso") or _http.dc_first(m, "dc.language") or None,
                "dateIssued": _http.dc_first(m, "dc.date.issued") or None,
                "dateSubmitted": _http.dc_first(m, "dc.date.submitted") or None,
                "publisher": _http.dc_first(m, "dc.publisher") or None,
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
    handle = it.get("handle") or ""
    return {
        "uuid": it.get("uuid"),
        "handle": handle or None,
        "url": f"{HANDLE_BASE}/{handle}" if handle else None,
        "title": _http.dc_first(m, "dc.title") or None,
        "titleAlt": _http.dc_first(m, "dc.title.alternative") or None,
        "authors": _http.dc_all(m, "dc.contributor.author"),
        "advisors": _http.dc_all(m, "dc.contributor.advisor"),
        "type": _http.dc_first(m, "dc.type") or None,
        "language": _http.dc_first(m, "dc.language.iso") or _http.dc_first(m, "dc.language") or None,
        "dateIssued": _http.dc_first(m, "dc.date.issued") or None,
        "dateSubmitted": _http.dc_first(m, "dc.date.submitted") or None,
        "dateAccessioned": _http.dc_first(m, "dc.date.accessioned") or None,
        "publisher": _http.dc_first(m, "dc.publisher") or None,
        "doi": _http.dc_first(m, "dc.identifier.doi") or None,
        "identifierURI": _http.dc_first(m, "dc.identifier.uri") or None,
        "subjects": _http.dc_all(m, "dc.subject"),
        "description": _http.dc_first(m, "dc.description") or None,
        "entityType": it.get("entityType"),
        "inArchive": it.get("inArchive"),
        "lastModified": it.get("lastModified"),
        "abstract": _http.dc_first(m, "dc.description.abstract") or None,
    }


def _build_params(args: argparse.Namespace, use_all_filters: bool) -> list:
    params = [("query", args.query), ("page", str(args.page)), ("size", str(args.size)), ("sort", args.sort)]
    if not use_all_filters:
        return params
    if args.author:
        _http.add_dspace_filter(params, "author", args.author, "contains")
    if args.subject:
        _http.add_dspace_filter(params, "subject", args.subject, "equals")
    if args.language:
        _http.add_dspace_filter(params, "language", args.language, "equals")
    if args.itemtype:
        _http.add_dspace_filter(params, "itemtype", args.itemtype, "equals")
    if args.date_issued:
        _http.add_dspace_filter(params, "dateIssued", args.date_issued, "equals")
    if args.date_accessioned:
        _http.add_dspace_filter(params, "dateAccessioned", args.date_accessioned, "equals")
    if args.has_full_text is not None:
        params.append(("f.has_content_in_original_bundle", f"{str(args.has_full_text).lower()},equals"))
    return params


def cmd_search(args: argparse.Namespace) -> dict:
    params = _build_params(args, True)
    url = f"{API_BASE}/discover/search/objects?{_http.build_query(params)}"
    try:
        raw = _http.fetch(url, headers=JSON_HEADERS)
        return summarize_search(raw)
    except _http.HttpError as e:
        if e.status in (400, 404):
            # Robustness fallback: some AGH discovery filter combos are known to error.
            # Retry with only core query/page/size/sort to keep the tool usable.
            fallback_params = _build_params(args, False)
            fallback_url = f"{API_BASE}/discover/search/objects?{_http.build_query(fallback_params)}"
            raw = _http.fetch(fallback_url, headers=JSON_HEADERS)
            return summarize_search(raw)
        raise


def cmd_get(args: argparse.Namespace) -> dict:
    url = f"{API_BASE}/core/items/{args.uuid}"
    raw = _http.fetch(url, headers=JSON_HEADERS)
    return summarize_item(raw)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AGH University of Krakow Repository discovery search.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Full-text + faceted discovery search.")
    s.add_argument("--query", required=True, help="Full-text search expression.")
    s.add_argument("--page", type=int, default=0, help="Zero-based page number. Default: 0.")
    s.add_argument("--size", type=int, default=10, help="Results per page (1-50). Default: 10.")
    s.add_argument("--sort", choices=SORT_CHOICES, default="score,desc")
    s.add_argument("--author", help="Author filter (default op: contains).")
    s.add_argument("--subject", help="Subject/keyword filter (default op: equals).")
    s.add_argument("--language", help="Language code filter (default op: equals), e.g. pl, en.")
    s.add_argument("--itemtype", help="Document type filter (default op: equals). E.g. Thesis, Article, Book, Technical Report.")
    s.add_argument("--date-issued", dest="date_issued", help="Publication date filter (default op: equals). For ranges use Solr query op, e.g. '[2020-01-01 TO 2023-12-31],query'.")
    s.add_argument("--date-accessioned", dest="date_accessioned", help="Deposit date filter (default op: equals).")
    s.add_argument(
        "--has-full-text",
        dest="has_full_text",
        type=_bool_flag,
        default=None,
        help="true/false -- restrict to items with files in the original bundle.",
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
    except _http.HttpError as e:
        _http.fail(f"{e} (status={e.status})")
    except Exception as e:  # noqa: BLE001
        _http.fail(str(e))


if __name__ == "__main__":
    main()
