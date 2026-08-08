#!/usr/bin/env python3
"""Centrum Informacji o Ofiarach II Wojny Swiatowej (IPN) -- WWII Victims
Information Center database, https://ofiary.ipn.gov.pl

CONFIRMED from a live form dump (2026-08-09): the header mini-search form
POSTs to /ofi/search with fields `szukaj` (query text) and `szukajw[1]`/
`szukajw[2]`/`szukajw[3]` (search scope: 1=articles, 2=photos/files,
3=video/audio; the site's own default has only [1] checked). A larger
"wyszukiwarka_cms" form on the same page adds optional extras: `szukaj_d`
(exact phrase), `szukaj_w` (exclude words), `szukaj_o1`/`szukaj_o2`/
`szukaj_o3` (OR terms), `terminod`/`termindo` (date range, dd-mm-yyyy),
and `category[<id>]`/`subcategory[<id>]` checkboxes for category filters
(pass raw numeric ids -- none are validated locally).

NOT confirmed live: a search for "Kowalski" via a wrong GET param name
correctly returned zero effect (proving that param name is NOT it), but no
query with the *correct* field names above has yet been run against the
live server to see a populated results page -- only the empty search form
was observed. This tool always includes the raw HTML plus a best-effort
generic link/no-records extraction; report back a real results page if you
want structured per-record parsing added.

No public JSON API -- this POSTs the real HTML search form and returns the
parsed results page.
"""

from __future__ import annotations

import argparse
import urllib.parse
from html.parser import HTMLParser

from _http import fail, print_result, request_text

SITE = "https://ofiary.ipn.gov.pl"
SEARCH_URL = f"{SITE}/ofi/search"

SCOPE_LABELS = {"1": "artykuly", "2": "zdjecia i inne pliki", "3": "video i audio"}


class _ResultCollector(HTMLParser):
    """Best-effort: collects every anchor and flags the 'norecords' no-hits
    marker. The markup for an actual (non-empty) result set has not been
    observed live -- this is generic extraction, not a precise per-record
    parser. `raw_html`-equivalent (`html`) is always included too."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self.no_records = False
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "norecords" in (attrs_dict.get("class") or ""):
            self.no_records = True
        if tag == "a":
            href = attrs_dict.get("href")
            if href:
                self._href = href
                self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = "".join(self._text).strip()
            if text:
                self.links.append({"href": self._href, "text": text})
            self._href = None
            self._text = []


def cmd_search(args: argparse.Namespace) -> dict:
    form: list[tuple[str, str]] = [("szukaj", args.query)]
    for s in args.scope:
        form.append((f"szukajw[{s}]", "1"))
    if args.exact_phrase:
        form.append(("szukaj_d", args.exact_phrase))
    if args.exclude_words:
        form.append(("szukaj_w", args.exclude_words))
    for i, term in enumerate((args.or_term1, args.or_term2, args.or_term3), start=1):
        if term:
            form.append((f"szukaj_o{i}", term))
    if args.date_from:
        form.append(("terminod", args.date_from))
    if args.date_to:
        form.append(("termindo", args.date_to))
    for cat_id in args.category or []:
        form.append((f"category[{cat_id}]", "1"))
    form.append(("szukaj_button", "Szukaj"))

    body = urllib.parse.urlencode(form).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    html = request_text(SEARCH_URL, method="POST", headers=headers, data=body)

    collector = _ResultCollector()
    collector.feed(html)

    return {
        "url": SEARCH_URL,
        "query": args.query,
        "scope": [SCOPE_LABELS[s] for s in args.scope],
        "no_records": collector.no_records,
        "links": collector.links,
        "html": html,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Centrum Informacji o Ofiarach II Wojny Swiatowej (IPN) -- search the WWII victims/records database."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search ofiary.ipn.gov.pl (POSTs the real HTML search form).")
    s.add_argument("--query", required=True, help="Search phrase, e.g. a surname.")
    s.add_argument(
        "--scope", nargs="+", default=["1"], choices=["1", "2", "3"],
        help="Content types to search: 1=articles (default), 2=photos/files, 3=video/audio.",
    )
    s.add_argument("--exact-phrase", dest="exact_phrase", default=None, help="Require this exact phrase (szukaj_d).")
    s.add_argument("--exclude-words", dest="exclude_words", default=None, help="Exclude results containing these words (szukaj_w).")
    s.add_argument("--or-term1", dest="or_term1", default=None, help="One of these OR terms (szukaj_o1).")
    s.add_argument("--or-term2", dest="or_term2", default=None, help="One of these OR terms (szukaj_o2).")
    s.add_argument("--or-term3", dest="or_term3", default=None, help="One of these OR terms (szukaj_o3).")
    s.add_argument("--date-from", dest="date_from", default=None, help="Publication date lower bound, dd-mm-yyyy.")
    s.add_argument("--date-to", dest="date_to", default=None, help="Publication date upper bound, dd-mm-yyyy.")
    s.add_argument(
        "--category", nargs="+", default=None,
        help="Raw numeric category id(s) to filter by, e.g. 2725 (Z Archiwum IPN). See reference/API.md for known ids.",
    )
    s.set_defaults(func=cmd_search)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
    except RuntimeError as e:
        fail(f"Error: {e}")
        return
    print_result(result)


if __name__ == "__main__":
    main()
