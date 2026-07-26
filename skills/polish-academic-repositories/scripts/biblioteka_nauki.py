#!/usr/bin/env python3
"""
Biblioteka Nauki -- Poland's largest open-access publication database.
Public API, no authentication required.

Subcommands (ported from the polish-academic-mcp tools of the same name):
  search-publications  -- bn_search_publications: POST /api/search (JSON) full-text keyword search.
  search-articles      -- bn_search_articles: OAI-PMH ListRecords, harvest by date/set. NOT keyword search.
  get-article          -- bn_get_article: OAI-PMH GetRecord by numeric article ID.

Source: https://bibliotekanauki.pl
"""

import argparse
import json
import sys
from urllib.parse import quote

import _http

OAI_BASE = "https://bibliotekanauki.pl/api/oai/articles"
SEARCH_API = "https://bibliotekanauki.pl/api/search"

PUBLICATION_TYPES = ["ARTICLE", "SIMPLE_BOOK", "COLLECTIVE_WORK", "CHAPTER"]


def cmd_search_publications(args: argparse.Namespace) -> dict:
    search_criteria: dict = {"generalSearchString": args.query}
    if args.publication_types:
        search_criteria["publicationTypes"] = args.publication_types
    if args.published_date_from:
        search_criteria["publishedDateFrom"] = args.published_date_from
    if args.published_date_to:
        search_criteria["publishedDateTo"] = args.published_date_to
    if args.open_resources:
        search_criteria["openResources"] = True

    body = {
        "searchCriteria": search_criteria,
        "paginationCriteria": {
            "pageNumber": args.page,
            "pageSize": args.page_size,
            "sortingCriteria": {
                "fieldName": args.sort_field,
                "direction": args.sort_direction,
            },
        },
    }

    raw = _http.fetch(
        SEARCH_API,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        data=body,
    )
    return _http.parse_json_response(raw, SEARCH_API)


def _oai_list_records(from_date, until_date, set_spec, metadata_format, resumption_token) -> str:
    if resumption_token:
        url = f"{OAI_BASE}?verb=ListRecords&resumptionToken={quote(resumption_token, safe='')}"
    else:
        params = [("verb", "ListRecords"), ("metadataPrefix", metadata_format)]
        if from_date:
            params.append(("from", from_date))
        if until_date:
            params.append(("until", until_date))
        if set_spec:
            params.append(("set", set_spec))
        url = f"{OAI_BASE}?{_http.build_query(params)}"
    return _http.fetch(url), url


def cmd_search_articles(args: argparse.Namespace) -> dict:
    xml, url = _oai_list_records(
        args.from_date, args.until_date, args.set, args.metadata_format, args.resumption_token
    )

    # Robustness fallback: if a restrictive set yields no records, retry once without set.
    if not args.resumption_token and args.set and _http.has_no_records_match(xml):
        params = [("verb", "ListRecords"), ("metadataPrefix", args.metadata_format)]
        if args.from_date:
            params.append(("from", args.from_date))
        if args.until_date:
            params.append(("until", args.until_date))
        fallback_url = f"{OAI_BASE}?{_http.build_query(params)}"
        xml = _http.fetch(fallback_url)
        url = fallback_url

    if args.minimize_pii:
        xml = _http.scrub_pii(xml)

    result = _http.parse_oai_pmh(xml, url)
    if args.minimize_pii:
        # Also scrub any residual PII that survived structured extraction.
        result = json.loads(_http.scrub_pii(json.dumps(result, ensure_ascii=False)))
    return result


def cmd_get_article(args: argparse.Namespace) -> dict:
    identifier = f"oai:bibliotekanauki.pl:{args.article_id}"
    params = [("verb", "GetRecord"), ("metadataPrefix", args.metadata_format), ("identifier", identifier)]
    url = f"{OAI_BASE}?{_http.build_query(params)}"
    xml = _http.fetch(url)
    return _http.parse_oai_pmh(xml, url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Biblioteka Nauki -- Polish open-access publication database (bibliotekanauki.pl)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser(
        "search-publications",
        help="Full-text keyword search (JSON search API). Preferred tool for keyword/author/title queries.",
    )
    sp.add_argument("--query", required=True, help="Search phrase (Polish or English).")
    sp.add_argument("--page", type=int, default=1, help="Page number, 1-based. Default: 1.")
    sp.add_argument("--page-size", type=int, default=10, help="Results per page, max 50. Default: 10.")
    sp.add_argument("--sort-field", choices=["score", "publishedDate"], default="score")
    sp.add_argument("--sort-direction", choices=["ASC", "DESC"], default="DESC")
    sp.add_argument(
        "--publication-types",
        nargs="+",
        choices=PUBLICATION_TYPES,
        help="Restrict to publication types (ARTICLE, SIMPLE_BOOK, COLLECTIVE_WORK, CHAPTER).",
    )
    sp.add_argument("--published-date-from", help="Lower bound YYYY-MM-DD (inclusive).")
    sp.add_argument("--published-date-to", help="Upper bound YYYY-MM-DD (inclusive).")
    sp.add_argument("--open-resources", action="store_true", help="Prefer open/diamond open access resources.")
    sp.set_defaults(func=cmd_search_publications)

    sa = sub.add_parser(
        "search-articles",
        help="OAI-PMH ListRecords harvest by date range and/or OAI set. NOT a keyword search -- use "
        "search-publications for that.",
    )
    sa.add_argument("--from-date", dest="from_date", help="Earliest datestamp, YYYY-MM-DD.")
    sa.add_argument("--until-date", dest="until_date", help="Latest datestamp, YYYY-MM-DD.")
    sa.add_argument("--set", help="OAI setSpec identifier to restrict to a journal/discipline.")
    sa.add_argument("--metadata-format", choices=["oai_dc", "jats"], default="oai_dc")
    sa.add_argument("--resumption-token", help="Token from a previous response to fetch the next page.")
    sa.add_argument(
        "--minimize-pii",
        action="store_true",
        help="Redact ORCID/email/phone/PESEL-like patterns from the output.",
    )
    sa.set_defaults(func=cmd_search_articles)

    ga = sub.add_parser("get-article", help="OAI-PMH GetRecord for one article by numeric ID.")
    ga.add_argument("--article-id", required=True, help="Numeric article ID, e.g. 1968869.")
    ga.add_argument("--metadata-format", choices=["jats", "oai_dc"], default="jats")
    ga.set_defaults(func=cmd_get_article)

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
