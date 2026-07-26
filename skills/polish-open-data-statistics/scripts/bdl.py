#!/usr/bin/env python3
"""GUS Bank Danych Lokalnych (BDL) -- regional and national statistics.

BDL web UI: https://bdl.stat.gov.pl/BDL/start
REST API v1: https://bdl.stat.gov.pl/api/v1/
OpenAPI spec: https://bdl.stat.gov.pl/api/v1/swagger/doc/swagger.json

Anonymous access works. Optionally set the BDL_CLIENT_ID environment
variable to send it as the X-ClientId header for higher rate limits
(register a client id at https://api.stat.gov.pl/home/bdlapi). The skill
works fine without it -- it's purely a rate-limit optimization.

Subcommands (mirroring the original MCP tools):
  search-subjects       (bdl_search_subjects)      -- thematic tree search by name fragment.
  search-variables      (bdl_search_variables)     -- search statistical variables.
  search-units          (bdl_search_units)         -- search territorial units.
  get-variable          (bdl_get_variable)         -- metadata for one variable by numeric id.
  get-data-by-variable  (bdl_get_data_by_variable) -- values for one variable across units.
  get-data-by-unit      (bdl_get_data_by_unit)     -- values for one unit across variables.

Standard library only. See _http.py for the shared HTTP/retry helper.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from _http import build_query, fetch_json

API_BASE = "https://bdl.stat.gov.pl/api/v1"


def bdl_headers() -> Dict[str, str]:
    """Build request headers, adding X-ClientId only if BDL_CLIENT_ID is set.

    BDL_CLIENT_ID is entirely optional: anonymous requests work fine, just
    with a lower rate limit, so we never error out when it's absent.
    """
    headers: Dict[str, str] = {}
    client_id = os.environ.get("BDL_CLIENT_ID", "").strip()
    if client_id:
        headers["X-ClientId"] = client_id
    return headers


def _years_list(years: Optional[List[int]]) -> Optional[List[int]]:
    return years if years else None


# ── bdl_search_subjects ──────────────────────────────────────────────────────
def cmd_search_subjects(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "name": args.name,
        "page": args.page,
        "page-size": args.page_size,
        "lang": args.lang,
    }
    if args.sort:
        params["sort"] = args.sort
    url = f"{API_BASE}/subjects/search?{build_query(params)}"
    return fetch_json(url, headers=bdl_headers())


# ── bdl_search_variables ─────────────────────────────────────────────────────
def cmd_search_variables(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "page": args.page,
        "page-size": args.page_size,
        "lang": args.lang,
    }
    if args.name:
        params["name"] = args.name
    if args.subject_id:
        params["subject-id"] = args.subject_id
    if args.level is not None:
        params["level"] = args.level
    if args.years:
        params["year"] = args.years
    if args.sort:
        params["sort"] = args.sort
    url = f"{API_BASE}/variables/search?{build_query(params)}"
    return fetch_json(url, headers=bdl_headers())


# ── bdl_search_units ─────────────────────────────────────────────────────────
def cmd_search_units(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "page": args.page,
        "page-size": args.page_size,
        "lang": args.lang,
    }
    if args.name:
        params["name"] = args.name
    if args.levels:
        params["level"] = args.levels
    if args.years:
        params["year"] = args.years
    if args.sort:
        params["sort"] = args.sort
    url = f"{API_BASE}/units/search?{build_query(params)}"
    return fetch_json(url, headers=bdl_headers())


# ── bdl_get_variable ─────────────────────────────────────────────────────────
def cmd_get_variable(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {"lang": args.lang}
    url = f"{API_BASE}/variables/{args.variable_id}?{build_query(params)}"
    return fetch_json(url, headers=bdl_headers())


# ── bdl_get_data_by_variable ─────────────────────────────────────────────────
def cmd_get_data_by_variable(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "page": args.page,
        "page-size": args.page_size,
        "lang": args.lang,
        # NB: the upstream API expects "aggregate_id" with an underscore here,
        # unlike "page-size"/"unit-level" which use hyphens -- verified against
        # the source MCP server's bdl.ts (URLSearchParams key is aggregate_id).
        "aggregate_id": args.aggregate_id,
    }
    if args.years:
        params["year"] = args.years
    if args.unit_level is not None:
        params["unit-level"] = args.unit_level
    if args.unit_parent_id:
        params["unit-parent-id"] = args.unit_parent_id
    url = f"{API_BASE}/data/by-variable/{args.variable_id}?{build_query(params)}"
    return fetch_json(url, headers=bdl_headers())


# ── bdl_get_data_by_unit ──────────────────────────────────────────────────────
def cmd_get_data_by_unit(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {
        "page": args.page,
        "page-size": args.page_size,
        "lang": args.lang,
        # NB: underscore here matches the upstream API / source bdl.ts, unlike
        # the hyphenated "page-size" and "var-id" params.
        "aggregate_id": args.aggregate_id,
        "var-id": args.variable_ids,
    }
    if args.years:
        params["year"] = args.years
    import urllib.parse

    unit_id = urllib.parse.quote(args.unit_id, safe="")
    url = f"{API_BASE}/data/by-unit/{unit_id}?{build_query(params)}"
    return fetch_json(url, headers=bdl_headers())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bdl.py",
        description=(
            "Query GUS Bank Danych Lokalnych (BDL) regional/national statistics API v1."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    lang_kwargs = dict(default="pl", choices=["pl", "en"], help="Response language. Default pl.")
    page_kwargs = dict(type=int, default=0, help="Zero-based page index. Default 0.")
    page_size_kwargs = dict(type=int, default=20, help="Results per page (1-100). Default 20.")

    # search-subjects
    p_subj = subparsers.add_parser(
        "search-subjects", help="Search BDL subject tree by name fragment (bdl_search_subjects)."
    )
    p_subj.add_argument("--name", required=True, help="Subject name fragment (pl or en, per --lang).")
    p_subj.add_argument("--page", **page_kwargs)
    p_subj.add_argument("--page-size", dest="page_size", **page_size_kwargs)
    p_subj.add_argument(
        "--sort", default=None,
        help='Sort order, e.g. "Id", "-Id", "Name", "-Name", "Id,Name", etc. Optional.',
    )
    p_subj.add_argument("--lang", **lang_kwargs)
    p_subj.set_defaults(func=cmd_search_subjects)

    # search-variables
    p_var = subparsers.add_parser(
        "search-variables", help="Search BDL statistical variables (bdl_search_variables)."
    )
    p_var.add_argument("--name", default=None, help="Text matched in variable label fields (N1..N5).")
    p_var.add_argument(
        "--subject-id", dest="subject_id", default=None,
        help="Parent subject id from search-subjects or the BDL tree (e.g. P1312).",
    )
    p_var.add_argument("--level", type=int, default=None, help="Territorial/variable level filter.")
    p_var.add_argument(
        "--years", type=int, nargs="*", default=None,
        help="Restrict to variables available for these calendar years (space-separated).",
    )
    p_var.add_argument("--page", **page_kwargs)
    p_var.add_argument("--page-size", dest="page_size", **page_size_kwargs)
    p_var.add_argument(
        "--sort", default=None,
        help='Sort order, e.g. "Id", "-Id", "SubjectId", "Id,SubjectId", etc. Optional.',
    )
    p_var.add_argument("--lang", **lang_kwargs)
    p_var.set_defaults(func=cmd_search_variables)

    # search-units
    p_units = subparsers.add_parser(
        "search-units", help="Search BDL territorial units (bdl_search_units)."
    )
    p_units.add_argument("--name", default=None, help="Unit name fragment (e.g. city or voivodeship).")
    p_units.add_argument(
        "--levels", type=int, nargs="*", default=None,
        help="TERYT level filters (e.g. 2 = voivodeship). See BDL /levels metadata if unsure.",
    )
    p_units.add_argument(
        "--years", type=int, nargs="*", default=None,
        help="Years for which the unit definition should exist.",
    )
    p_units.add_argument("--page", **page_kwargs)
    p_units.add_argument("--page-size", dest="page_size", **page_size_kwargs)
    p_units.add_argument("--sort", default=None, help="Sort order (optional).")
    p_units.add_argument("--lang", **lang_kwargs)
    p_units.set_defaults(func=cmd_search_units)

    # get-variable
    p_getvar = subparsers.add_parser(
        "get-variable", help="Fetch metadata for one BDL variable by id (bdl_get_variable)."
    )
    p_getvar.add_argument("--id", required=True, type=int, dest="variable_id", help="Variable id.")
    p_getvar.add_argument("--lang", **lang_kwargs)
    p_getvar.set_defaults(func=cmd_get_variable)

    # get-data-by-variable
    p_dbv = subparsers.add_parser(
        "get-data-by-variable",
        help="Fetch values for one variable across territorial units (bdl_get_data_by_variable).",
    )
    p_dbv.add_argument("--variable-id", required=True, type=int, dest="variable_id", help="Variable id.")
    p_dbv.add_argument(
        "--years", type=int, nargs="*", default=None,
        help="Calendar years to include; omit for all available years.",
    )
    p_dbv.add_argument(
        "--unit-level", type=int, default=None, dest="unit_level",
        help="BDL territorial level (e.g. 2 = voivodeship). See BDL /levels if unsure.",
    )
    p_dbv.add_argument(
        "--unit-parent-id", default=None, dest="unit_parent_id",
        help="Parent unit id to restrict to its descendants (e.g. a voivodeship code).",
    )
    p_dbv.add_argument(
        "--aggregate-id", type=int, default=1, dest="aggregate_id",
        help="Aggregation level id. Default 1.",
    )
    p_dbv.add_argument("--page", **page_kwargs)
    p_dbv.add_argument("--page-size", dest="page_size", **page_size_kwargs)
    p_dbv.add_argument("--lang", **lang_kwargs)
    p_dbv.set_defaults(func=cmd_get_data_by_variable)

    # get-data-by-unit
    p_dbu = subparsers.add_parser(
        "get-data-by-unit",
        help="Fetch values for one territorial unit across one or more variables (bdl_get_data_by_unit).",
    )
    p_dbu.add_argument(
        "--unit-id", required=True, dest="unit_id",
        help="Territorial unit id from search-units (a TERYT-style code).",
    )
    p_dbu.add_argument(
        "--variable-ids", required=True, type=int, nargs="+", dest="variable_ids",
        help="One or more variable ids (space-separated).",
    )
    p_dbu.add_argument("--years", type=int, nargs="*", default=None, help="Calendar years to include.")
    p_dbu.add_argument(
        "--aggregate-id", type=int, default=1, dest="aggregate_id",
        help="Aggregation level id. Default 1.",
    )
    p_dbu.add_argument("--page", **page_kwargs)
    p_dbu.add_argument("--page-size", dest="page_size", **page_size_kwargs)
    p_dbu.add_argument("--lang", **lang_kwargs)
    p_dbu.set_defaults(func=cmd_get_data_by_unit)

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
