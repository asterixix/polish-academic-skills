#!/usr/bin/env python3
"""Chmura Czytania -- free digital library of classic literature (Polish
and translated), http://www.chmuraczytania.pl (Fundacja Festina Lente). No
login required.

CONFIRMED live (2026-08-09): a static PHP catalog with NO text search --
only category browsing (catalog.php?cat=<id>) and pagination
(catalog.php?page=<n>). Each catalog page lists ~16 books as
<a class='minibook preview' href='showbook.php?id=N'><img .../><br/>
<b>Title</b><br/>Author</a> -- id/title/author are reliably parsed from
this exact confirmed markup. Categories confirmed live:
  14=proza swiatowa, 15=proza polska, 19=poezja polska, 21=poezja swiatowa,
  22=poradniki, 23=oryginalne wersje jezykowe, 24=eseistyka

Because there is no server-side search, `search` here means: page through
the catalog (optionally restricted to one category) and keep only books
whose title or author contains the query (case-insensitive substring).
Bounded by --max-pages to avoid an unbounded crawl (the whole catalog was
~9 pages as of the live check).

NOT confirmed: the shape of a single book's detail page (showbook.php?id=N)
-- `get-book` returns the raw HTML for that page without further parsing.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser

from _http import fail, print_result, request_text

SITE = "http://www.chmuraczytania.pl"

CATEGORIES = {
    "14": "proza swiatowa",
    "15": "proza polska",
    "19": "poezja polska",
    "21": "poezja swiatowa",
    "22": "poradniki",
    "23": "oryginalne wersje jezykowe",
    "24": "eseistyka",
}


class _CatalogParser(HTMLParser):
    """Extracts (id, title, author) triples from the confirmed
    <a class='minibook preview' href='showbook.php?id=N'><img/><br/>
    <b>Title</b><br/>Author</a> markup, plus the highest page number seen
    in the pagination links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.books: list[dict] = []
        self.max_page = 1
        self._in_book = False
        self._book_id: str | None = None
        self._in_bold = False
        self._seen_bold = False
        self._title_parts: list[str] = []
        self._after_bold_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        if tag == "a" and "minibook" in classes:
            self._in_book = True
            href = attrs_dict.get("href", "")
            self._book_id = href.split("id=")[-1] if "id=" in href else None
            self._title_parts = []
            self._after_bold_text = []
            self._seen_bold = False
        elif tag == "b" and self._in_book:
            self._in_bold = True
        elif tag == "a" and "page=" in (attrs_dict.get("href") or ""):
            try:
                n = int(attrs_dict["href"].split("page=")[-1])
                self.max_page = max(self.max_page, n)
            except ValueError:
                pass

    def handle_data(self, data):
        if not self._in_book:
            return
        if self._in_bold:
            self._title_parts.append(data)
        elif self._seen_bold:
            self._after_bold_text.append(data)

    def handle_endtag(self, tag):
        if tag == "b" and self._in_bold:
            self._in_bold = False
            self._seen_bold = True
        elif tag == "a" and self._in_book:
            title = "".join(self._title_parts).strip()
            author = "".join(self._after_bold_text).strip()
            if self._book_id and title:
                self.books.append({"id": self._book_id, "title": title, "author": author or None})
            self._in_book = False


def _fetch_catalog_page(cat: str | None, page: int) -> _CatalogParser:
    params = []
    if cat:
        params.append(f"cat={cat}")
    if page > 1:
        params.append(f"page={page}")
    url = f"{SITE}/catalog.php"
    if params:
        url += "?" + "&".join(params)
    html = request_text(url)
    parser = _CatalogParser()
    parser.feed(html)
    return parser


def cmd_list_categories(_args: argparse.Namespace) -> dict:
    return {"categories": CATEGORIES}


def cmd_browse_category(args: argparse.Namespace) -> dict:
    parser = _fetch_catalog_page(args.category, args.page)
    return {"category": args.category, "page": args.page, "max_page": parser.max_page, "books": parser.books}


def cmd_search(args: argparse.Namespace) -> dict:
    query = args.query.lower()
    matches = []
    pages_scanned = 0
    page = 1
    max_page = 1
    while page <= max_page and pages_scanned < args.max_pages:
        parser = _fetch_catalog_page(args.category, page)
        max_page = parser.max_page
        pages_scanned += 1
        for book in parser.books:
            haystack = f"{book['title']} {book.get('author') or ''}".lower()
            if query in haystack:
                matches.append(book)
        page += 1

    return {
        "query": args.query,
        "category": args.category,
        "pages_scanned": pages_scanned,
        "total_pages": max_page,
        "truncated": pages_scanned < max_page,
        "matches": matches,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Chmura Czytania -- free digital library of classic literature (no server-side search, client-side filter)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    lc = sub.add_parser("list-categories", help="List the 7 fixed catalog categories (no network request).")
    lc.set_defaults(func=cmd_list_categories)

    bc = sub.add_parser("browse-category", help="List books on one catalog page, optionally filtered by category.")
    bc.add_argument("--category", default=None, choices=sorted(CATEGORIES), help="Category id. Omit for all categories.")
    bc.add_argument("--page", type=int, default=1, help="Page number, 1-based. Default 1.")
    bc.set_defaults(func=cmd_browse_category)

    s = sub.add_parser("search", help="Client-side title/author substring search across the paginated catalog.")
    s.add_argument("--query", required=True, help="Substring to match against title or author (case-insensitive).")
    s.add_argument("--category", default=None, choices=sorted(CATEGORIES), help="Restrict to one category. Omit to search everything.")
    s.add_argument(
        "--max-pages", dest="max_pages", type=int, default=20,
        help="Safety cap on pages fetched. Default 20 (the whole catalog was ~9 pages as of the live check).",
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
