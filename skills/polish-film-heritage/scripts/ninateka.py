#!/usr/bin/env python3
"""Ninateka -- VOD platform of Filmoteka Narodowa (FINA), https://ninateka.pl/

No published OpenAPI, but the front-end SPA calls a JSON API under
`/api/products/...`. The `platform` query parameter is required (`BROWSER`
for web-style access) -- omitting it returns a `PLATFORM_UNDEFINED` error
from the upstream. Search uses `keyword` (not `query`).

Subcommands mirror the original MCP tools:
  search   -> GET /api/products/vods/search?keyword=&platform=BROWSER&limit=&firstResult=
  get-vod  -> GET /api/products/vods/{id}?platform=BROWSER

Both return the raw upstream JSON (meta.totalCount + items[] for search;
full item metadata for get-vod) unmodified -- there is no HTML to parse
here, unlike every other script in this skill.
"""

from __future__ import annotations

import argparse
import sys

from _http import build_query, fail, print_result, request_json

API_BASE = "https://ninateka.pl/api"
JSON_HEADERS = {"Accept": "application/json"}


def cmd_search(args: argparse.Namespace) -> None:
    url = build_query(
        f"{API_BASE}/products/vods/search",
        {
            "keyword": args.query,
            "platform": args.platform,
            "limit": args.limit,
            "firstResult": args.first_result,
        },
    )
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling ninateka_search: {e}")
        return
    print_result(result)


def cmd_get_vod(args: argparse.Namespace) -> None:
    url = build_query(
        f"{API_BASE}/products/vods/{args.id}",
        {"platform": args.platform},
    )
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling ninateka_get_vod: {e}")
        return
    print_result(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ninateka.py",
        description="Ninateka (Filmoteka Narodowa VOD) JSON API client. "
        "No API key required.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Search Ninateka (films, episodes, series, audio, ...)")
    p.add_argument("--query", required=True, dest="query",
                    help="Search phrase (mapped to the API's `keyword` parameter).")
    p.add_argument("--limit", type=int, default=20,
                    help="Page size; the API typically accepts up to 100 (default 20).")
    p.add_argument("--first-result", type=int, default=0, dest="first_result",
                    help="Zero-based offset for pagination (API param firstResult, default 0).")
    p.add_argument("--platform", default="BROWSER", choices=["BROWSER"],
                    help="Required platform token for the public API (default/only value: BROWSER).")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get-vod", help="Get full metadata for one Ninateka item by numeric id")
    p.add_argument("--id", required=True, type=int, dest="id",
                    help="Numeric id from search results (items[].id).")
    p.add_argument("--platform", default="BROWSER", choices=["BROWSER"],
                    help="Required platform token for the public API (default/only value: BROWSER).")
    p.set_defaults(func=cmd_get_vod)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        fail(f"Error: {e}")
    except Exception as e:  # noqa: BLE001 - top-level CLI safety net
        fail(f"Unexpected error: {e}")


if __name__ == "__main__":
    sys.exit(main() or 0)
