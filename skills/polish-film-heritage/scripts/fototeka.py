#!/usr/bin/env python3
"""Fototeka (Filmoteka Narodowa - INA), https://fototeka.fn.org.pl/

Photo/stills archive of Polish cinema history (~300k+ records). No
documented public REST API; the search page serves results as HTML
(`/pl/strona/wyszukiwarka.html`). There is an internal `ajax.html` endpoint
that returns JSON with HTML fragments, but it requires a fully serialized
form (including a session hash), so it is not usable statelessly here --
this mirrors the upstream MCP tool's own documented reasoning for using the
plain HTML page instead.

The upstream MCP tool (fototeka.ts) returns these pages as raw, unparsed
HTML. This script additionally extracts a best-effort structured
`items`/title/text on top of the raw page, for the same usability reasons
as gapla.py. That extraction is a generic heuristic, NOT verified against
a live fetch of fototeka.fn.org.pl (this sandbox blocks outbound HTTPS) --
see reference/API.md. `raw_html` (capped) is always included as a fallback.

Subcommands mirror the original MCP tools:
  search      -> GET /pl/strona/wyszukiwarka.html?key=&search_type=&pageNumber=&howmany=
  get-photo   -> GET /pl/foto/view/{id}.html
"""

from __future__ import annotations

import argparse
import sys

from _http import (
    build_query,
    extract_body_text,
    extract_id_links,
    extract_title,
    fail,
    print_result,
    request_text,
)

SITE = "https://fototeka.fn.org.pl"
SEARCH_URL = f"{SITE}/pl/strona/wyszukiwarka.html"
HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl,en;q=0.8",
}

MAX_RAW_HTML_CHARS = 20_000
MAX_DETAIL_TEXT_CHARS = 15_000


def cmd_search(args: argparse.Namespace) -> None:
    url = build_query(
        SEARCH_URL,
        {
            "key": args.query,
            "search_type": args.search_type,
            "pageNumber": args.page,
            "howmany": args.how_many,
        },
    )
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fototeka_search: {e}")
        return

    items = extract_id_links(html, "foto/view", base_url=SITE)
    raw_html = html
    raw_truncated = False
    if len(raw_html) > MAX_RAW_HTML_CHARS:
        raw_html = raw_html[:MAX_RAW_HTML_CHARS]
        raw_truncated = True

    payload = {
        "source": "fototeka.fn.org.pl",
        "query": args.query,
        "search_type": args.search_type,
        "page": args.page,
        "how_many": args.how_many,
        "search_url": url,
        "items": items,
        "items_note": (
            "Best-effort extraction from photo tile links (pl/foto/view/{id}); "
            "unverified against live markup -- use raw_html to cross-check "
            "if this list looks incomplete or empty."
        ),
        "raw_html": raw_html,
        "raw_html_truncated": raw_truncated,
    }
    print_result(payload)


def cmd_get_photo(args: argparse.Namespace) -> None:
    url = f"{SITE}/pl/foto/view/{args.id}.html"
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fototeka_get_photo: {e}")
        return

    title = extract_title(html)
    text, truncated = extract_body_text(html, MAX_DETAIL_TEXT_CHARS)

    payload = {
        "photo_id": args.id,
        "url": url,
        "title": title,
        "text": text,
        "text_truncated": truncated,
        "source": "fototeka.fn.org.pl",
        "note": (
            "title/text are a best-effort whole-page extraction, unverified "
            "against live markup (sandbox blocks outbound HTTPS). Re-fetch "
            "the url directly if fields look wrong or incomplete. This does "
            "not return the full-resolution image file, only page text."
        ),
    }
    print_result(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fototeka.py",
        description="Fototeka (Filmoteka Narodowa photo archive) HTML client. "
        "No API key required.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Search the Fototeka photo database")
    p.add_argument("--query", required=True, dest="query",
                    help="Search phrase (film title, person name, or keywords).")
    p.add_argument("--search-type", default="slowo_kluczowe", dest="search_type",
                    choices=["tytul", "osoba", "rezyseria", "slowo_kluczowe"],
                    help="Search field: tytul (film title), osoba (person), rezyseria (director), "
                    "slowo_kluczowe (keywords, default).")
    p.add_argument("--page", type=int, default=1, help="Result page, 1-based (default 1).")
    p.add_argument("--how-many", type=int, default=25, dest="how_many",
                    help="Photos per page, 1-100 (default 25; API param howmany).")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get-photo", help="Fetch one photo detail page by numeric id")
    p.add_argument("--id", required=True, type=int, dest="id",
                    help="Numeric photo id from search results (pl/foto/view/{id}.html).")
    p.set_defaults(func=cmd_get_photo)

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
