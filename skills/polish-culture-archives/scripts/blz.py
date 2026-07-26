#!/usr/bin/env python3
"""Baza Legalnych Zrodel -- Legalna Kultura (bazalegalnychzrodel.pl).

WordPress site with a custom post type `listing` ("Zrodla"); public REST,
no API key required.

Discovery: header `Link: <https://bazalegalnychzrodel.pl/wp-json/>; rel="https://api.w.org/"`.

Subcommands mirror the original MCP tools:
  search           -> GET /wp/v2/listings (search + optional listing_cat)
  get-listing      -> GET /wp/v2/listings/{id}
  list-categories  -> GET /wp/v2/listing_cat (taxonomy terms, id -> use as listing_cat)
"""

from __future__ import annotations

import argparse
import sys

from _http import build_query, fail, print_result, request_json

API_BASE = "https://bazalegalnychzrodel.pl/wp-json/wp/v2"
JSON_HEADERS = {"Accept": "application/json"}

ORDERBY_CHOICES = ["date", "modified", "relevance", "title", "slug", "id"]
ORDER_CHOICES = ["asc", "desc"]


def cmd_search(args: argparse.Namespace) -> None:
    query = (args.query or "").strip()
    # WP returns HTTP 400 for orderby=relevance without a search string.
    effective_orderby = "date" if (args.orderby == "relevance" and len(query) == 0) else args.orderby

    params = {
        "page": args.page,
        "per_page": args.per_page,
        "orderby": effective_orderby,
        "order": args.order,
    }
    if query:
        params["search"] = query
    if args.listing_cat is not None:
        params["listing_cat"] = args.listing_cat

    url = build_query(f"{API_BASE}/listings", params)
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling blz_search: {e}")
        return
    print_result(result)


def cmd_get_listing(args: argparse.Namespace) -> None:
    url = f"{API_BASE}/listings/{args.id}"
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling blz_get_listing: {e}")
        return
    print_result(result)


def cmd_list_categories(args: argparse.Namespace) -> None:
    params = {"page": args.page, "per_page": args.per_page}
    if args.parent is not None:
        params["parent"] = args.parent
    url = build_query(f"{API_BASE}/listing_cat", params)
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling blz_listing_categories: {e}")
        return
    print_result(result)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="blz.py",
        description="Baza Legalnych Zrodel (bazalegalnychzrodel.pl) -- legal digital-culture sources directory.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("search", help="Full-text and/or category search across listings.")
    ps.add_argument("--query", default=None, help="Full-text search phrase (WP `search` param). Omit to browse by category only.")
    ps.add_argument("--listing-cat", type=int, default=None, help="listing_cat taxonomy term id (see list-categories), e.g. 78 Biblioteki, 82 Muzea.")
    ps.add_argument("--page", type=int, default=1, help="Page number (1-based). Default 1.")
    ps.add_argument("--per-page", type=int, default=20, help="Items per page (max 100). Default 20.")
    ps.add_argument("--orderby", choices=ORDERBY_CHOICES, default="relevance", help="Sort field. relevance requires a query; falls back to date otherwise.")
    ps.add_argument("--order", choices=ORDER_CHOICES, default="desc", help="Sort direction.")
    ps.set_defaults(func=cmd_search)

    pg = sub.add_parser("get-listing", help="Fetch a single listing (source) by numeric WordPress post id.")
    pg.add_argument("--id", type=int, required=True, help="Listing post id (the `id` field from search results).")
    pg.set_defaults(func=cmd_get_listing)

    pc = sub.add_parser("list-categories", help="List listing_cat taxonomy terms (categories such as Filmy, Muzyka, Biblioteki, Muzea).")
    pc.add_argument("--page", type=int, default=1, help="Page number (1-based). Default 1.")
    pc.add_argument("--per-page", type=int, default=100, help="Terms per page. Default 100.")
    pc.add_argument("--parent", type=int, default=None, help="Only terms with this parent id (0 = top-level, if supported).")
    pc.set_defaults(func=cmd_list_categories)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
