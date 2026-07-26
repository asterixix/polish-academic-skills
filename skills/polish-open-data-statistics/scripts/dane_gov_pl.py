#!/usr/bin/env python3
"""dane.gov.pl -- Poland's national open data portal.

43,000+ datasets from 500+ public institutions. No API key required.
API version: 1.4. Pagination is 1-based.

Subcommands (mirroring the original MCP tools):
  search  (dane_search)       -- full-text search across all datasets.
  get     (dane_get_dataset)  -- dataset detail plus its downloadable resources.

Standard library only. See _http.py for the shared HTTP/retry helper.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from _http import build_query, fetch_json

API_BASE = "https://api.dane.gov.pl/1.4"


def cmd_search(args: argparse.Namespace) -> Any:
    def build_url(with_category: bool) -> str:
        params: Dict[str, Any] = {
            "q": args.query,
            "per_page": args.per_page,
            "page": args.page,
            "sort": args.sort,
        }
        if with_category and args.category:
            params["category[id]"] = args.category
        return f"{API_BASE}/datasets?{build_query(params)}"

    try:
        return fetch_json(build_url(True))
    except RuntimeError as exc:
        # Robustness fallback: some category values (labels vs IDs) cause a
        # 400 Bad Request. Retry once without the category filter so search
        # stays usable, mirroring dane.ts's behavior.
        if args.category and "HTTP 400" in str(exc):
            return fetch_json(build_url(False))
        raise


def cmd_get(args: argparse.Namespace) -> Any:
    dataset_url = f"{API_BASE}/datasets/{args.id}"
    resources_url = f"{API_BASE}/datasets/{args.id}/resources"

    dataset = fetch_json(dataset_url)
    resources = fetch_json(resources_url)

    return {"dataset": dataset, "resources": resources}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dane_gov_pl.py",
        description="Search and fetch datasets from dane.gov.pl (Polish open data portal).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser(
        "search", help="Full-text search across dane.gov.pl datasets (dane_search)."
    )
    p_search.add_argument("--query", required=True, help="Search phrase.")
    p_search.add_argument(
        "--category",
        default=None,
        help='DCAT category name, e.g. "Nauka i technika", "Edukacja", "Zdrowie", "Transport".',
    )
    p_search.add_argument(
        "--per-page", type=int, default=20, dest="per_page",
        help="Results per page (1-100). Default 20.",
    )
    p_search.add_argument(
        "--page", type=int, default=1,
        help="1-based page number. Default 1.",
    )
    p_search.add_argument(
        "--sort", default="relevance",
        choices=["relevance", "date", "-date", "title", "views_count"],
        help="Sort order (-date = newest first). Default relevance.",
    )
    p_search.set_defaults(func=cmd_search)

    p_get = subparsers.add_parser(
        "get", help="Fetch dataset detail + resources by numeric id (dane_get_dataset)."
    )
    p_get.add_argument(
        "--id", required=True, type=int,
        help="Numeric dataset id from the id field returned by 'search'.",
    )
    p_get.set_defaults(func=cmd_get)

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
