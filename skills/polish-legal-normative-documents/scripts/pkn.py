#!/usr/bin/env python3
"""PKN -- Polski Komitet Normalizacyjny main website (www.pkn.pl), a Drupal
site backed by Search API / Solr.

There is no published JSON/REST API (/jsonapi returns 404); the public site
search view accepts GET query parameters and returns an HTML results page.

This does NOT search the WIEDZA norms catalog (wiedza.pkn.pl) -- for actual
Polish Standard (PN) metadata use wiedza.py's search-norms / get-standard.
This tool only searches general pkn.pl web content (news, sections, etc.).

Subcommand:
  search  (pkn_search) -- GET /wyszukiwarka (or /en/search, /ru/poisk)

Standard library only. See _http.py for the shared HTTP/retry helper.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from _http import fetch_text

SITE_ORIGIN = "https://www.pkn.pl"

SEARCH_PATH = {
    "pl": "/wyszukiwarka",
    "en": "/en/search",
    "ru": "/ru/poisk",
}


class LinkCollector(HTMLParser):
    """Generic best-effort scrape of every anchor with non-empty text.

    The upstream Drupal/Solr result markup on pkn.pl is not documented and
    the original MCP tool never parsed it (it just returned raw HTML) --
    there is no TS selector to mirror here. This generic pass gives a rough
    "links" convenience list; `html` is always included too and remains the
    authoritative source if the markup does not match expectations. See
    reference/API.md for details on this limitation.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[Dict[str, Optional[str]]] = []
        self._current_href: Optional[str] = None
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if not href:
            return
        self._current_href = href
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            text = "".join(self._text_parts).strip()
            if text:
                self.links.append({"href": self._current_href, "text": text})
            self._current_href = None
            self._text_parts = []


def cmd_search(args: argparse.Namespace) -> Any:
    path = SEARCH_PATH[args.language]
    params = {
        "szukaj": args.query,
        "sort_by": args.sort_by,
        "page": args.page,
    }
    url = f"{SITE_ORIGIN}{path}?{urllib.parse.urlencode(params)}"
    html = fetch_text(url)

    collector = LinkCollector()
    collector.feed(html)

    return {
        "url": url,
        "links": collector.links,
        "html": html,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pkn.py",
        description="Full-text search on the PKN main website (pkn.pl) -- not the WIEDZA norms catalog.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser("search", help="Search pkn.pl site content (pkn_search).")
    p_search.add_argument("--query", required=True, help="Search phrase (plain text).")
    p_search.add_argument(
        "--language", default="pl", choices=["pl", "en", "ru"],
        help="Site language / search path: pl=/wyszukiwarka, en=/en/search, ru=/ru/poisk.",
    )
    p_search.add_argument(
        "--sort-by", default="search_api_relevance", dest="sort_by",
        choices=["search_api_relevance", "changed"],
        help="search_api_relevance=by relevance (default); changed=by last modification date.",
    )
    p_search.add_argument("--page", type=int, default=0, help="Zero-based page number (Drupal pagination).")
    p_search.set_defaults(func=cmd_search)

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
