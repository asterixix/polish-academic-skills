#!/usr/bin/env python3
"""ISAP -- Internetowy System Aktow Prawnych, browsed via the ELI JSON API.

Public read API: https://api.sejm.gov.pl/eli (no key required). This is a
JSON API run by the Sejm (api.sejm.gov.pl) -- NOT the same service as the
Biblioteka Sejmowa OPAC catalog (see biblioteka_sejmowa.py), which is an
HTML-only Aleph system with no JSON API at all.

Subcommands (mirroring the original MCP tools):
  search-acts  (isap_search_acts) -- GET /eli/acts/search
  get-act      (isap_get_act)     -- GET /eli/acts/{publisher}/{year}/{position}

Standard library only. See _http.py for the shared HTTP/retry helper.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

from _http import build_query, fetch_json

ELI_BASE = "https://api.sejm.gov.pl/eli"


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def eli_to_path(eli: str) -> str:
    """Validate and turn "DU/2026/370" into a safe URL path segment.

    Mirrors eliToPath() in src/tools/isap.ts: at least 3 non-empty
    segments (publisher/year/position/...), no ".." traversal segments,
    each segment percent-encoded independently.
    """
    trimmed = eli.strip().lstrip("/")
    segments = [s for s in trimmed.split("/") if s != ""]
    if len(segments) < 3:
        raise RuntimeError(
            'ELI must look like "DU/2026/370" (publisher/year/position).'
        )
    if any(s == ".." for s in segments):
        raise RuntimeError("Invalid ELI")
    return "/".join(urllib.parse.quote(seg, safe="") for seg in segments)


def cmd_search_acts(args: argparse.Namespace) -> Any:
    params: Dict[str, Any] = {}
    if args.title:
        params["title"] = args.title
    keywords = _split_csv(args.keyword)
    if keywords:
        params["keyword"] = keywords
    if args.year is not None:
        params["year"] = args.year
    if args.publisher:
        params["publisher"] = args.publisher
    if args.type:
        params["type"] = args.type
    if args.position is not None:
        params["position"] = args.position
    if args.volume is not None:
        params["volume"] = args.volume
    if args.in_force:
        params["inForce"] = "1"
    if args.date_from:
        params["dateFrom"] = args.date_from
    if args.date_to:
        params["dateTo"] = args.date_to
    if args.date_effect_from:
        params["dateEffectFrom"] = args.date_effect_from
    if args.date_effect_to:
        params["dateEffectTo"] = args.date_effect_to
    if args.pub_date_from:
        params["pubDateFrom"] = args.pub_date_from
    if args.pub_date_to:
        params["pubDateTo"] = args.pub_date_to
    params["limit"] = args.limit
    params["offset"] = args.offset
    params["sortBy"] = args.sort_by
    params["sortDir"] = args.sort_dir

    url = f"{ELI_BASE}/acts/search?{build_query(params)}"
    return fetch_json(url)


def cmd_get_act(args: argparse.Namespace) -> Any:
    path = eli_to_path(args.eli)
    url = f"{ELI_BASE}/acts/{path}"
    return fetch_json(url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="isap.py",
        description=(
            "Search and fetch Polish legal acts from ISAP via the Sejm ELI "
            "JSON API (api.sejm.gov.pl/eli)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser(
        "search-acts",
        help="Full-text-ish search across ISAP acts (isap_search_acts).",
    )
    p_search.add_argument("--title", default=None, help="Words to find in the act title.")
    p_search.add_argument(
        "--keyword",
        default=None,
        help=(
            "Comma-separated ISAP controlled-vocabulary keyword tag(s), e.g. "
            '"szkolnictwo,podatki". Matches tags, not free text.'
        ),
    )
    p_search.add_argument("--year", type=int, default=None, help="Calendar year of the act, e.g. 2025.")
    p_search.add_argument(
        "--publisher", default=None,
        help='Publisher code, e.g. "DU" (Dziennik Ustaw), "MP" (Monitor Polski).',
    )
    p_search.add_argument("--type", default=None, help='Act type, e.g. "Ustawa", "Rozporzadzenie".')
    p_search.add_argument("--position", type=int, default=None, help="Position number (poz.) in the journal.")
    p_search.add_argument("--volume", type=int, default=None, help="Journal volume number.")
    p_search.add_argument(
        "--in-force", action="store_true", dest="in_force",
        help="Only acts currently in force (API: inForce=1).",
    )
    p_search.add_argument("--date-from", default=None, help="Announcement date from (yyyy-MM-dd).")
    p_search.add_argument("--date-to", default=None, help="Announcement date to (yyyy-MM-dd).")
    p_search.add_argument("--date-effect-from", default=None, help="Effective date from (yyyy-MM-dd).")
    p_search.add_argument("--date-effect-to", default=None, help="Effective date to (yyyy-MM-dd).")
    p_search.add_argument("--pub-date-from", default=None, help="Publication date from (yyyy-MM-dd).")
    p_search.add_argument("--pub-date-to", default=None, help="Publication date to (yyyy-MM-dd).")
    p_search.add_argument(
        "--limit", type=int, default=20,
        help="Max results, 1-100 (default 20; upstream API default is 500).",
    )
    p_search.add_argument("--offset", type=int, default=0, help="Zero-based pagination offset.")
    p_search.add_argument(
        "--sort-by", default="publisher",
        choices=["publisher", "position", "title", "change"],
        help="Sort field. Default publisher.",
    )
    p_search.add_argument(
        "--sort-dir", default="asc", choices=["asc", "desc"],
        help="Sort direction. Default asc.",
    )
    p_search.set_defaults(func=cmd_search_acts)

    p_get = subparsers.add_parser(
        "get-act", help="Fetch one legal act by ELI id (isap_get_act)."
    )
    p_get.add_argument(
        "--eli", required=True,
        help='ELI identifier, e.g. "DU/2026/370" (publisher/year/position).',
    )
    p_get.set_defaults(func=cmd_get_act)

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
