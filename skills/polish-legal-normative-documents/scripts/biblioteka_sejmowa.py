#!/usr/bin/env python3
"""Biblioteka Sejmowa -- Aleph OPAC catalog at https://bs.sejm.gov.pl/F

No public JSON API or documented SRU interface. Machine access is the same
web interface a browser uses (GET requests to the /F script), returning raw
HTML. This is a *different* Sejm service from the ISAP/ELI JSON API at
api.sejm.gov.pl -- see isap.py for that one.

Subcommands (mirroring the original MCP tools):
  search    (bs_sejm_search)    -- func=find-b, word search, HTML result list
  get-item  (bs_sejm_get_item)  -- func=item-global, one bibliographic record

The original MCP tool just returns the raw HTML result list and expects the
caller (an LLM) to read doc_library/doc_number out of the item-global links
by eye. Since this skill has no such calling LLM baked into the plumbing,
`search` additionally extracts those item-global links itself (via a small
html.parser.HTMLParser subclass) into a `hits` array, alongside the full
`html` body -- see reference/API.md for the exact extraction rule. Treat
`hits` as a best-effort convenience; if the markup changes upstream, fall
back to reading `html` directly.

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

OPAC_BASE = "https://bs.sejm.gov.pl/F"

FIND_CODES = ["WRD", "WST", "WHF", "WNW", "WMW", "WSE", "WHP", "WTE", "TXT", "SYS", "WOB"]


class ItemGlobalLinkParser(HTMLParser):
    """Collects <a href="...func=item-global...."> links from a result-list page.

    These links are how the Aleph catalog wires a search hit to its full
    bibliographic record; the query string carries doc_library, doc_number,
    sub_library, year and volume -- exactly the arguments bs_sejm_get_item
    (get-item here) needs.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hits: List[Dict[str, Optional[str]]] = []
        self._current: Optional[Dict[str, Optional[str]]] = None
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href") or ""
        if "func=item-global" not in href:
            return
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)

        def first(key: str) -> Optional[str]:
            values = qs.get(key)
            return values[0] if values else None

        self._current = {
            "doc_library": first("doc_library"),
            "doc_number": first("doc_number"),
            "sub_library": first("sub_library"),
            "year": first("year"),
            "volume": first("volume"),
            "href": href,
        }
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current is not None:
            text = "".join(self._text_parts).strip()
            self._current["text"] = text or None
            self.hits.append(self._current)
            self._current = None
            self._text_parts = []


def _dedupe_hits(hits: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    seen = set()
    out = []
    for hit in hits:
        key = (hit.get("doc_library"), hit.get("doc_number"))
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out


class TitleParser(HTMLParser):
    """Grabs the text of the first <title> element, for a human-readable hint."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        if tag == "title" and self.title is None:
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title = (self.title or "") + data


def cmd_search(args: argparse.Namespace) -> Any:
    params = {
        "func": "find-b",
        "local_base": args.local_base,
        "request": args.request,
        "find_code": args.find_code,
        "adjacent": args.adjacent,
    }
    url = f"{OPAC_BASE}?{urllib.parse.urlencode(params)}"
    html = fetch_text(url)

    parser = ItemGlobalLinkParser()
    parser.feed(html)
    hits = _dedupe_hits(parser.hits)

    return {
        "url": url,
        "hits": hits,
        "hit_count": len(hits),
        "html": html,
    }


def cmd_get_item(args: argparse.Namespace) -> Any:
    params = {
        "func": "item-global",
        "doc_library": args.doc_library,
        "doc_number": args.doc_number,
        "year": args.year or "",
        "volume": args.volume or "",
        "sub_library": args.sub_library,
    }
    url = f"{OPAC_BASE}?{urllib.parse.urlencode(params)}"
    html = fetch_text(url)

    title_parser = TitleParser()
    title_parser.feed(html)

    return {
        "url": url,
        "page_title": title_parser.title.strip() if title_parser.title else None,
        "html": html,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biblioteka_sejmowa.py",
        description=(
            "Search and fetch records from the Biblioteka Sejmowa Aleph OPAC "
            "catalog (bs.sejm.gov.pl/F). HTML scraping -- no JSON API exists."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser(
        "search", help="Word search against the Aleph OPAC (bs_sejm_search)."
    )
    p_search.add_argument(
        "--query", "--request", dest="request", required=True,
        help="Search expression (same syntax as the OPAC search box).",
    )
    p_search.add_argument(
        "--local-base", required=True,
        help=(
            "Aleph local base code, lowercase, e.g. bis01 (main catalog), "
            "bis05 (journal articles), pos01 (Sejm session recordings), "
            "tek01 (constitutional texts), sta01 (old prints), ars01."
        ),
    )
    p_search.add_argument(
        "--find-code", default="WRD", choices=FIND_CODES,
        help="Index to search: WRD=all fields (default), WST=title, WHF=author, "
             "WNW=publisher, WHP=subject heading, SYS=record number, etc.",
    )
    p_search.add_argument(
        "--adjacent", default="N", choices=["N", "Y"],
        help="Require adjacent words: N=no (default), Y=yes.",
    )
    p_search.set_defaults(func=cmd_search)

    p_item = subparsers.add_parser(
        "get-item",
        help="Fetch one bibliographic record by doc_library + doc_number (bs_sejm_get_item).",
    )
    p_item.add_argument(
        "--doc-library", required=True,
        help="Document library code from an item-global link, e.g. BIS01, BIS05, POS01.",
    )
    p_item.add_argument(
        "--doc-number", required=True,
        help="Nine-digit document number from the result list, e.g. 000179010.",
    )
    p_item.add_argument(
        "--sub-library", default="BS",
        help="Sub-library code from the link, usually BS.",
    )
    p_item.add_argument(
        "--year", default=None,
        help="Usually empty; only set if the item-global link includes a year param.",
    )
    p_item.add_argument(
        "--volume", default=None,
        help="Usually empty; only set if the item-global link includes a volume param.",
    )
    p_item.set_defaults(func=cmd_get_item)

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
