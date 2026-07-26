#!/usr/bin/env python3
"""SAOS -- System Analizy Orzeczen Sadowych (Polish court judgments, public
JSON API, no key required).

Two distinct APIs live under the same base URL:
  - Search & detail (typical single-judgment lookups):
      search-judgments (saos_search_judgments) -- GET /api/search/judgments
      get-judgment     (saos_get_judgment)     -- GET /api/judgments/{id}
  - Bulk "dump" API (wholesale data sync -- NOT a search replacement):
      dump-services      (saos_dump_services)      -- GET /api/dump
      dump-common-courts (saos_dump_common_courts) -- GET /api/dump/commonCourts
      dump-sc-chambers   (saos_dump_sc_chambers)   -- GET /api/dump/scChambers
      dump-judgments     (saos_dump_judgments)     -- GET /api/dump/judgments
      dump-enrichments   (saos_dump_enrichments)   -- GET /api/dump/enrichments

WARNING: dump-judgments returns full judgment records per row and responses
can be VERY LARGE. Prefer a narrow judgment_start_date/judgment_end_date
window and a small --page-size (10-20). It exists for mirroring/syncing the
whole database, not as a substitute for search-judgments.

SAOS periodically goes into a "Przerwa techniczna" (maintenance) mode where
search-judgments may hang or error out; if that happens, dump-judgments
with a narrow date range is the documented fallback.

Standard library only. See _http.py for the shared HTTP/retry helper.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from _http import build_query, fetch_json

SAOS_BASE = "https://www.saos.org.pl/api"

JUDGMENT_TYPES = ["DECISION", "RESOLUTION", "SENTENCE", "REGULATION", "REASONS"]
COURT_TYPES = ["APPEAL", "REGIONAL", "DISTRICT"]


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _add_page_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--page-size", type=int, default=20, dest="page_size",
        help="Results per request; API accepts 10-100. Default 20.",
    )
    p.add_argument(
        "--page-number", type=int, default=0, dest="page_number",
        help="Zero-based page index. Default 0.",
    )


def cmd_search_judgments(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "pageSize": args.page_size,
        "pageNumber": args.page_number,
    }
    if args.sorting_field:
        params["sortingField"] = args.sorting_field
    if args.sorting_direction:
        params["sortingDirection"] = args.sorting_direction
    if args.all:
        params["all"] = args.all
    if args.legal_base:
        params["legalBase"] = args.legal_base
    if args.referenced_regulation:
        params["referencedRegulation"] = args.referenced_regulation
    if args.law_journal_entry_code:
        params["lawJournalEntryCode"] = args.law_journal_entry_code
    if args.judge_name:
        params["judgeName"] = args.judge_name
    if args.case_number:
        params["caseNumber"] = args.case_number
    if args.court_type:
        params["courtType"] = args.court_type
    if args.cc_court_id is not None:
        params["ccCourtId"] = args.cc_court_id
    if args.cc_court_code:
        params["ccCourtCode"] = args.cc_court_code
    if args.cc_court_name:
        params["ccCourtName"] = args.cc_court_name
    if args.cc_division_id is not None:
        params["ccDivisionId"] = args.cc_division_id
    if args.cc_division_code:
        params["ccDivisionCode"] = args.cc_division_code
    if args.cc_division_name:
        params["ccDivisionName"] = args.cc_division_name
    if args.cc_include_dependent_court_judgments is not None:
        params["ccIncludeDependentCourtJudgments"] = (
            "true" if args.cc_include_dependent_court_judgments else "false"
        )
    if args.sc_personnel_type:
        params["scPersonnelType"] = args.sc_personnel_type
    if args.sc_judgment_form:
        params["scJudgmentForm"] = args.sc_judgment_form
    if args.sc_chamber_id is not None:
        params["scChamberId"] = args.sc_chamber_id
    if args.sc_chamber_name:
        params["scChamberName"] = args.sc_chamber_name
    if args.sc_division_id is not None:
        params["scDivisionId"] = args.sc_division_id
    if args.sc_division_name:
        params["scDivisionName"] = args.sc_division_name
    if args.judgment_date_from:
        params["judgmentDateFrom"] = args.judgment_date_from
    if args.judgment_date_to:
        params["judgmentDateTo"] = args.judgment_date_to

    judgment_types = _split_csv(args.judgment_types)
    if judgment_types:
        params["judgmentTypes"] = judgment_types
    keywords = _split_csv(args.keywords)
    if keywords:
        params["keywords"] = keywords

    url = f"{SAOS_BASE}/search/judgments?{build_query(params)}"
    try:
        return fetch_json(url)
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc}\n"
            "SAOS may be in \"Przerwa techniczna\" (maintenance) mode. Try "
            "dump-judgments with a narrow date range, or check "
            "https://www.saos.org.pl/search"
        ) from exc


def cmd_get_judgment(args: argparse.Namespace) -> Any:
    url = f"{SAOS_BASE}/judgments/{args.judgment_id}"
    return fetch_json(url)


def cmd_dump_services(_args: argparse.Namespace) -> Any:
    return fetch_json(f"{SAOS_BASE}/dump")


def cmd_dump_common_courts(args: argparse.Namespace) -> Any:
    params = {"pageSize": args.page_size, "pageNumber": args.page_number}
    url = f"{SAOS_BASE}/dump/commonCourts?{build_query(params)}"
    return fetch_json(url)


def cmd_dump_sc_chambers(args: argparse.Namespace) -> Any:
    params = {"pageSize": args.page_size, "pageNumber": args.page_number}
    url = f"{SAOS_BASE}/dump/scChambers?{build_query(params)}"
    return fetch_json(url)


def cmd_dump_judgments(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "pageSize": args.page_size,
        "pageNumber": args.page_number,
        "withGenerated": "true" if args.with_generated else "false",
    }
    if args.judgment_start_date:
        params["judgmentStartDate"] = args.judgment_start_date
    if args.judgment_end_date:
        params["judgmentEndDate"] = args.judgment_end_date
    if args.since_modification_date:
        params["sinceModificationDate"] = args.since_modification_date
    url = f"{SAOS_BASE}/dump/judgments?{build_query(params)}"
    return fetch_json(url)


def cmd_dump_enrichments(args: argparse.Namespace) -> Any:
    params = {"pageSize": args.page_size, "pageNumber": args.page_number}
    url = f"{SAOS_BASE}/dump/enrichments?{build_query(params)}"
    return fetch_json(url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="saos.py",
        description="Search and fetch Polish court judgments from SAOS (saos.org.pl).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser(
        "search-judgments",
        help="Search judgments (saos_search_judgments). See SAOS query language docs.",
    )
    p_search.add_argument("--all", default=None, help="Full-text/metadata phrase (SAOS query language).")
    p_search.add_argument("--page-size", type=int, default=20, dest="page_size", help="10-100. Default 20.")
    p_search.add_argument("--page-number", type=int, default=0, dest="page_number", help="Zero-based. Default 0.")
    p_search.add_argument("--sorting-field", default=None, dest="sorting_field",
                           help="e.g. DATABASE_ID, JUDGMENT_DATE.")
    p_search.add_argument("--sorting-direction", default=None, dest="sorting_direction", choices=["ASC", "DESC"])
    p_search.add_argument("--legal-base", default=None, dest="legal_base", help="Full-text search in legal basis field.")
    p_search.add_argument("--referenced-regulation", default=None, dest="referenced_regulation")
    p_search.add_argument("--law-journal-entry-code", default=None, dest="law_journal_entry_code",
                           help="Dziennik Ustaw position, format year/number, e.g. 2024/123.")
    p_search.add_argument("--judge-name", default=None, dest="judge_name")
    p_search.add_argument("--case-number", default=None, dest="case_number", help="Exact full case signature.")
    p_search.add_argument("--court-type", default=None, dest="court_type", choices=COURT_TYPES,
                           help="Common court level (only when filtering common courts).")
    p_search.add_argument("--cc-court-id", type=int, default=None, dest="cc_court_id")
    p_search.add_argument("--cc-court-code", default=None, dest="cc_court_code",
                           help="Source court code digits, e.g. 15500000 for SA Wroclaw.")
    p_search.add_argument("--cc-court-name", default=None, dest="cc_court_name")
    p_search.add_argument("--cc-division-id", type=int, default=None, dest="cc_division_id")
    p_search.add_argument("--cc-division-code", default=None, dest="cc_division_code")
    p_search.add_argument("--cc-division-name", default=None, dest="cc_division_name")
    p_search.add_argument(
        "--cc-include-dependent-court-judgments", dest="cc_include_dependent_court_judgments",
        action="store_true", default=None,
        help="When cc_court_id is an appeal court: include lower-instance judgments from that district.",
    )
    p_search.add_argument("--sc-personnel-type", default=None, dest="sc_personnel_type",
                           help="ONE_PERSON, THREE_PERSON, FIVE_PERSON, SEVEN_PERSON, ALL_COURT, ALL_CHAMBER, JOINED_CHAMBERS.")
    p_search.add_argument("--sc-judgment-form", default=None, dest="sc_judgment_form")
    p_search.add_argument("--sc-chamber-id", type=int, default=None, dest="sc_chamber_id")
    p_search.add_argument("--sc-chamber-name", default=None, dest="sc_chamber_name")
    p_search.add_argument("--sc-division-id", type=int, default=None, dest="sc_division_id")
    p_search.add_argument("--sc-division-name", default=None, dest="sc_division_name")
    p_search.add_argument(
        "--judgment-types", default=None, dest="judgment_types",
        help=f"Comma-separated, any of: {', '.join(JUDGMENT_TYPES)} (OR match).",
    )
    p_search.add_argument(
        "--keywords", default=None,
        help="Comma-separated thematic keywords (common courts); all must match (AND). Exact spelling.",
    )
    p_search.add_argument("--judgment-date-from", default=None, dest="judgment_date_from", help="yyyy-MM-dd.")
    p_search.add_argument("--judgment-date-to", default=None, dest="judgment_date_to", help="yyyy-MM-dd.")
    p_search.set_defaults(func=cmd_search_judgments)

    p_get = subparsers.add_parser("get-judgment", help="Fetch one judgment by numeric id (saos_get_judgment).")
    p_get.add_argument("--id", type=int, required=True, dest="judgment_id",
                        help="Numeric SAOS judgment id from search results items[].id.")
    p_get.set_defaults(func=cmd_get_judgment)

    p_dump_services = subparsers.add_parser(
        "dump-services",
        help="List dump sub-service hypermedia links (saos_dump_services).",
    )
    p_dump_services.set_defaults(func=cmd_dump_services)

    p_dump_cc = subparsers.add_parser(
        "dump-common-courts", help="Paginated dump of common courts (saos_dump_common_courts)."
    )
    _add_page_args(p_dump_cc)
    p_dump_cc.set_defaults(func=cmd_dump_common_courts)

    p_dump_sc = subparsers.add_parser(
        "dump-sc-chambers", help="Paginated dump of Supreme Court chambers (saos_dump_sc_chambers)."
    )
    _add_page_args(p_dump_sc)
    p_dump_sc.set_defaults(func=cmd_dump_sc_chambers)

    p_dump_j = subparsers.add_parser(
        "dump-judgments",
        help="Bulk judgment dump -- CAN RETURN VERY LARGE RESPONSES (saos_dump_judgments).",
    )
    _add_page_args(p_dump_j)
    p_dump_j.add_argument("--judgment-start-date", default=None, dest="judgment_start_date", help="yyyy-MM-dd.")
    p_dump_j.add_argument("--judgment-end-date", default=None, dest="judgment_end_date", help="yyyy-MM-dd.")
    p_dump_j.add_argument(
        "--since-modification-date", default=None, dest="since_modification_date",
        help="Incremental sync cutoff, yyyy-MM-dd'T'HH:mm:ss.SSS.",
    )
    p_dump_j.add_argument(
        "--no-generated", action="store_false", dest="with_generated", default=True,
        help="Exclude SAOS enrichment-module fields (default: included).",
    )
    p_dump_j.set_defaults(func=cmd_dump_judgments)

    p_dump_e = subparsers.add_parser(
        "dump-enrichments", help="Paginated dump of enrichment tags (saos_dump_enrichments)."
    )
    _add_page_args(p_dump_e)
    p_dump_e.set_defaults(func=cmd_dump_enrichments)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
