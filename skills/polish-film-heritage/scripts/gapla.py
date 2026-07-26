#!/usr/bin/env python3
"""Gapla -- Galeria plakatu filmowego (Filmoteka Narodowa - Instytut
Audiowizualny), https://gapla.fn.org.pl/

No public JSON API; this is a classic HTML GET-form site. Search:
`szukaj.html?q=...&typ=...&page=...&sort=...`. Poster detail page:
`plakat/{id}.html`.

The upstream MCP tool (gapla.ts) returns these pages as raw, unparsed HTML.
This script additionally extracts a best-effort structured `items`/`tiles`
list on top of the raw page, since dumping a full HTML page to an LLM
caller is much less useful than a short JSON list of poster ids/titles.
That extraction (extract_id_links / extract_title / extract_body_text in
_http.py) is a generic heuristic, NOT verified against a live fetch of
gapla.fn.org.pl (this sandbox blocks outbound HTTPS) -- see
reference/API.md. If the site's markup changes or differs from the
assumption, `items`/fields may come back empty; `raw_html` is always
included (capped) as a fallback so nothing is lost.

Subcommands mirror the original MCP tools:
  search       -> GET szukaj.html?q=&typ=&page=&sort=
  get-poster   -> GET plakat/{id}.html
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

SITE_BASE = "https://gapla.fn.org.pl"
HTML_HEADERS = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"}

# Caps on how much raw HTML we echo back as a fallback alongside the
# best-effort structured extraction (keeps output usable for an LLM caller).
MAX_RAW_HTML_CHARS = 20_000
MAX_DETAIL_TEXT_CHARS = 15_000


def cmd_search(args: argparse.Namespace) -> None:
    url = build_query(
        f"{SITE_BASE}/szukaj.html",
        {"q": args.query, "typ": args.typ, "page": args.page, "sort": args.sort},
    )
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling gapla_search: {e}")
        return

    items = extract_id_links(html, "plakat", base_url=SITE_BASE)
    raw_html = html
    raw_truncated = False
    if len(raw_html) > MAX_RAW_HTML_CHARS:
        raw_html = raw_html[:MAX_RAW_HTML_CHARS]
        raw_truncated = True

    payload = {
        "source": "gapla.fn.org.pl",
        "query": args.query,
        "typ": args.typ,
        "page": args.page,
        "sort": args.sort,
        "search_url": url,
        "items": items,
        "items_note": (
            "Best-effort extraction from poster tile links (plakat/{id}); "
            "unverified against live markup -- use raw_html to cross-check "
            "if this list looks incomplete or empty."
        ),
        "raw_html": raw_html,
        "raw_html_truncated": raw_truncated,
    }
    print_result(payload)


def cmd_get_poster(args: argparse.Namespace) -> None:
    url = f"{SITE_BASE}/plakat/{args.id}.html"
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling gapla_get_poster: {e}")
        return

    title = extract_title(html)
    text, truncated = extract_body_text(html, MAX_DETAIL_TEXT_CHARS)

    payload = {
        "poster_id": args.id,
        "url": url,
        "title": title,
        "text": text,
        "text_truncated": truncated,
        "source": "gapla.fn.org.pl",
        "note": (
            "title/text are a best-effort whole-page extraction, unverified "
            "against live markup (sandbox blocks outbound HTTPS). Re-fetch "
            "the url directly if fields look wrong or incomplete."
        ),
    }
    print_result(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gapla.py",
        description="Gapla (Filmoteka Narodowa film poster gallery) HTML client. "
        "No API key required.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Search the Gapla poster gallery (szukaj.html)")
    p.add_argument("--query", required=True, dest="query",
                    help="Search phrase (mapped to query param q).")
    p.add_argument("--typ", default="tytul", choices=["tytul", "autor", "rezyseria"],
                    help="Search field: tytul (title), autor (artist), rezyseria (director). Default tytul.")
    p.add_argument("--page", type=int, default=1, help="Result page, 1-based (default 1).")
    p.add_argument("--sort", default="alfabetycznie",
                    choices=["alfabetycznie", "chronologicznie_asc", "chronologicznie_desc"],
                    help="Sort order (default alfabetycznie).")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get-poster", help="Fetch one poster detail page by numeric id")
    p.add_argument("--id", required=True, type=int, dest="id",
                    help="Numeric poster id from search results (plakat/{id}.html).")
    p.set_defaults(func=cmd_get_poster)

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
