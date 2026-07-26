#!/usr/bin/env python3
"""
RUJ -- Jagiellonian University Repository (ruj.uj.edu.pl).
300,000+ records (articles, monographs, dissertations, chapters).
Runs DSpace 7, HAL+JSON. Anonymous read access for all public items.

IMPORTANT: GET /server/api/core/items (list all) is admin-only -- always use
the /discover/search/objects endpoint for search.

Subcommands (ported from ruj_search / ruj_get_item):
  search -- full-text + faceted discovery search.
  get    -- single item metadata by UUID.

Source: https://ruj.uj.edu.pl
"""

import argparse
import json

import _http

API_BASE = "https://ruj.uj.edu.pl/server/api"
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


def summarize_search(raw: str, minimize_pii: bool) -> dict:
    data = _http.parse_json_response(raw, API_BASE)
    sr = (data.get("_embedded") or {}).get("searchResult") or {}
    objects = (sr.get("_embedded") or {}).get("objects") or []
    page = sr.get("page") or {}

    items = []
    for obj in objects:
        it = (obj.get("_embedded") or {}).get("indexableObject") or {}
        m = it.get("metadata") or {}
        abstract = _http.dc_first(m, "dc.abstract.en") or _http.dc_first(m, "dc.abstract.pl")
        handle = it.get("handle") or ""
        items.append(
            {
                "uuid": it.get("uuid"),
                "handle": handle or None,
                "url": f"https://ruj.uj.edu.pl/xmlui/handle/{handle}" if handle else None,
                "title": _http.dc_first(m, "dc.title") or None,
                "titleAlt": _http.dc_first(m, "dc.title.alternative") or None,
                "authors": [] if minimize_pii else _http.dc_all(m, "dc.contributor.author"),
                "type": _http.dc_first(m, "dc.type") or None,
                "language": _http.dc_first(m, "dc.language") or None,
                "dateIssued": _http.dc_first(m, "dc.date.issued") or None,
                "dateSubmitted": _http.dc_first(m, "dc.date.submitted") or None,
                "affiliation": None if minimize_pii else (_http.dc_first(m, "dc.affiliation") or None),
                "subject": _http.dc_first(m, "dc.subject.en") or _http.dc_first(m, "dc.subject.pl") or None,
                "abstract": _http.truncate(abstract, 500) if abstract else None,
            }
        )

    result = {
        "totalElements": page.get("totalElements"),
        "page": {"number": page.get("number"), "size": page.get("size"), "totalPages": page.get("totalPages")},
        "items": items,
    }
    if minimize_pii:
        result = json.loads(_http.scrub_pii(json.dumps(result, ensure_ascii=False)))
    return result


def summarize_item(raw: str) -> dict:
    it = _http.parse_json_response(raw, API_BASE)
    m = it.get("metadata") or {}
    handle = it.get("handle") or ""
    return {
        "uuid": it.get("uuid"),
        "handle": handle or None,
        "url": f"https://ruj.uj.edu.pl/xmlui/handle/{handle}" if handle else None,
        "title": _http.dc_first(m, "dc.title") or None,
        "titleAlt": _http.dc_first(m, "dc.title.alternative") or None,
        "authors": _http.dc_all(m, "dc.contributor.author"),
        "advisors": _http.dc_all(m, "dc.contributor.advisor"),
        "reviewers": _http.dc_all(m, "dc.contributor.reviewer"),
        "type": _http.dc_first(m, "dc.type") or None,
        "language": _http.dc_first(m, "dc.language") or None,
        "dateIssued": _http.dc_first(m, "dc.date.issued") or None,
        "dateSubmitted": _http.dc_first(m, "dc.date.submitted") or None,
        "dateAccessioned": _http.dc_first(m, "dc.date.accessioned") or None,
        "affiliation": _http.dc_first(m, "dc.affiliation") or None,
        "fieldOfStudy": _http.dc_first(m, "dc.fieldofstudy") or None,
        "area": _http.dc_first(m, "dc.area") or None,
        "subjectEN": _http.dc_first(m, "dc.subject.en") or None,
        "subjectPL": _http.dc_first(m, "dc.subject.pl") or None,
        "doi": _http.dc_first(m, "dc.identifier.doi") or None,
        "identifierURI": _http.dc_first(m, "dc.identifier.uri") or None,
        "entityType": it.get("entityType"),
        "inArchive": it.get("inArchive"),
        "lastModified": it.get("lastModified"),
        "abstractEN": _http.dc_first(m, "dc.abstract.en") or None,
        "abstractPL": _http.dc_first(m, "dc.abstract.pl") or None,
    }


def cmd_search(args: argparse.Namespace) -> dict:
    params = [("query", args.query), ("page", str(args.page)), ("size", str(args.size)), ("sort", args.sort)]

    if args.itemtype:
        _http.add_dspace_filter(params, "itemtype", args.itemtype, "equals")
    if args.author:
        _http.add_dspace_filter(params, "author", args.author, "contains")
    if args.subject:
        _http.add_dspace_filter(params, "subject", args.subject, "equals")
    if args.language:
        _http.add_dspace_filter(params, "language", args.language, "equals")
    if args.affiliation:
        _http.add_dspace_filter(params, "affiliation", args.affiliation, "contains")
    if args.affiliation_em:
        _http.add_dspace_filter(params, "affiliationEm", args.affiliation_em, "contains")
    if args.journal_title:
        _http.add_dspace_filter(params, "journalTitle", args.journal_title, "contains")
    if args.subtype:
        _http.add_dspace_filter(params, "subtype", args.subtype, "equals")
    if args.entity_type:
        _http.add_dspace_filter(params, "entityType", args.entity_type, "equals")
    if args.pbn_discipline:
        _http.add_dspace_filter(params, "pbndiscipline", args.pbn_discipline, "equals")
    if args.date_issued:
        _http.add_dspace_filter(params, "dateIssued", args.date_issued, "equals")
    if args.date_accessioned:
        _http.add_dspace_filter(params, "dateAccessioned", args.date_accessioned, "equals")
    if args.date_submitted:
        _http.add_dspace_filter(params, "dateSubmitted", args.date_submitted, "equals")
    if args.has_full_text is not None:
        params.append(("f.has_content_in_original_bundle", f"{str(args.has_full_text).lower()},equals"))

    url = f"{API_BASE}/discover/search/objects?{_http.build_query(params)}"
    raw = _http.fetch(url, headers=JSON_HEADERS)
    return summarize_search(raw, args.minimize_pii)


def cmd_get(args: argparse.Namespace) -> dict:
    url = f"{API_BASE}/core/items/{args.uuid}"
    raw = _http.fetch(url, headers=JSON_HEADERS)
    return summarize_item(raw)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="RUJ -- Jagiellonian University Repository discovery search.")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Full-text + faceted discovery search.")
    s.add_argument("--query", required=True, help="Full-text search expression.")
    s.add_argument("--page", type=int, default=0, help="Zero-based page number. Default: 0.")
    s.add_argument("--size", type=int, default=10, help="Results per page (1-50). Default: 10.")
    s.add_argument("--sort", choices=SORT_CHOICES, default="score,desc")
    s.add_argument("--itemtype", help="Document type filter (default op: equals). E.g. JournalArticle, Book.")
    s.add_argument("--author", help="Author filter (default op: contains).")
    s.add_argument("--subject", help="Subject/keyword filter (default op: equals).")
    s.add_argument("--language", help="Language code filter (default op: equals), e.g. pl, en.")
    s.add_argument("--affiliation", help="Author institutional affiliation filter (default op: contains).")
    s.add_argument("--affiliation-em", dest="affiliation_em", help="Corresponding-author affiliation filter (default op: contains).")
    s.add_argument("--journal-title", dest="journal_title", help="Journal title filter (default op: contains).")
    s.add_argument("--subtype", help="Publication subtype filter (default op: equals).")
    s.add_argument("--entity-type", dest="entity_type", help="DSpace entityType filter (default op: equals).")
    s.add_argument("--pbn-discipline", dest="pbn_discipline", help="PBN scientific discipline filter (default op: equals).")
    s.add_argument(
        "--has-full-text",
        dest="has_full_text",
        type=_bool_flag,
        default=None,
        help="true/false -- restrict to items with files in the original bundle.",
    )
    s.add_argument("--date-issued", dest="date_issued", help="Publication date filter (default op: equals). For ranges use Solr query op, e.g. '[2020-01-01 TO 2023-12-31],query'.")
    s.add_argument("--date-accessioned", dest="date_accessioned", help="Deposit date filter (default op: equals).")
    s.add_argument("--date-submitted", dest="date_submitted", help="Submission date filter (default op: equals).")
    s.add_argument(
        "--minimize-pii",
        action="store_true",
        help="Redact identifying fields (authors, affiliation) and scrub PII patterns from output.",
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
