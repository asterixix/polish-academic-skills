#!/usr/bin/env python3
"""
EMIS/ELibM -- European Mathematical Information Service / Electronic
Library of Mathematics, http://emis.icm.edu.pl (the Warsaw/ICM mirror of a
European math-resources hub founded 1995; 100+ open-access math journals,
proceedings, and electronic books).

CONFIRMED live (2026-08-09): this is a fully static, hand-built HTML site
with no search form and no API -- navigation is entirely link-based
(Journals / Proceedings & Collections / Monographs & Lecture Notes /
Classics & Opera Omnia / Other Electronic Resources / Databases). There is
nothing to query; the only meaningful operation is browsing one of these
fixed category index pages and following the links inside.

Subcommands:
  categories -- list the fixed top-level ELibM categories (no network request).
  browse     -- fetch one category's index page and extract every link on it.

Source: http://emis.icm.edu.pl
"""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser

import _http

SITE = "http://emis.icm.edu.pl"

CATEGORIES = {
    "journals": "elibm/journals/index.html",
    "proceedings": "elibm/proceedings/index.html",
    "monographs": "elibm/monographs/index.html",
    "classics": "elibm/classics/index.html",
    "other": "elibm/misc/index.html",
    "databases": "databases/index.html",
}


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
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


def cmd_categories(_args: argparse.Namespace) -> dict:
    return {"categories": {k: f"{SITE}/{v}" for k, v in CATEGORIES.items()}}


def cmd_browse(args: argparse.Namespace) -> dict:
    path = CATEGORIES[args.category]
    url = f"{SITE}/{path}"
    html = _http.fetch(url)
    collector = _LinkCollector()
    collector.feed(html)
    return {"url": url, "category": args.category, "links": collector.links}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="EMIS/ELibM -- browse the European math resources index (static site, no search)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("categories", help="List the fixed top-level categories (no network request).")
    c.set_defaults(func=cmd_categories)

    b = sub.add_parser("browse", help="Fetch one category's index page and list every link on it.")
    b.add_argument("--category", required=True, choices=sorted(CATEGORIES), help="Which category to browse.")
    b.set_defaults(func=cmd_browse)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except _http.HttpError as e:
        _http.fail(f"{e} (status={e.status})")
    except Exception as e:  # noqa: BLE001
        _http.fail(str(e))


if __name__ == "__main__":
    main()
