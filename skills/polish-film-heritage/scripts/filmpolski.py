#!/usr/bin/env python3
"""FilmPolski.pl -- Internetowa Baza Filmu Polskiego (PWSFTviT Lodz).

No public JSON API; search is a GET on HTML (`index.php?szukaj=&rodzaj=`).
This script parses that HTML into compact JSON, and extracts a truncated
plain-text excerpt from the record page for get-item -- this is a DIRECT
PORT of the regex-based parsing in the source TS tool (filmpolski.ts):
parseSearchPage / parsePeopleList / parseFilmsList / extractArticleHtml /
stripToPlain / decodeEntities all match the TS field-for-field.

IMPORTANT -- site usage policy: filmpolski.pl's terms of use restrict bulk
copying of database content. Use short excerpts only and always cite
filmpolski.pl as the source. get-item deliberately returns a truncated
excerpt (default cap 25000 chars, matching the TS MAX_RECORD_CHARS), never
the full page, and prints a one-line reminder to stderr on every call.

Subcommands mirror the original MCP tools:
  search     -> GET index.php?szukaj=&rodzaj=  (rodzaj: 1=fragment, 2=start, 3=exact)
  get-item   -> GET index.php/{id}, extract <article id="film|osoba">, strip to text
"""

from __future__ import annotations

import argparse
import re
import sys

from _http import build_query, decode_entities, fail, print_result, request_text, strip_to_plain

SITE = "https://www.filmpolski.pl/fp"
INDEX = f"{SITE}/index.php"
HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl,en;q=0.8",
}

MAX_RECORD_CHARS = 25_000

USAGE_POLICY_NOTE = (
    "filmpolski.pl terms of use restrict bulk copying of database content -- "
    "use short excerpts only and cite filmpolski.pl as the source."
)

MATCH_MODE_TO_RODZAJ = {"fragment": 1, "start": 2, "exact": 3}


def _parse_entry_list(inner: str, id_key: str, label_key: str, hint_key: str) -> list:
    """Shared body of parsePeopleList()/parseFilmsList() from filmpolski.ts --
    both iterate <li> blocks, take the LAST index.php/{id} link inside (the
    site sometimes has more than one link per row) and an optional
    ``.rodzajfilmu`` hint/details div."""
    out: list = []
    li_re = re.compile(r"<li\b[^>]*>([\s\S]*?)</li>", re.IGNORECASE)
    link_re = re.compile(r'<a href="index\.php/(\d+)"[^>]*>([^<]*)</a>', re.IGNORECASE)
    hint_re = re.compile(r'<div class="rodzajfilmu">([^<]*)</div>', re.IGNORECASE)
    for lm in li_re.finditer(inner):
        li = lm.group(1) or ""
        hint_m = hint_re.search(li)
        hint = hint_m.group(1).strip() if hint_m else None
        last = None
        for m in link_re.finditer(li):
            label = decode_entities(m.group(2)).strip()
            if label:
                last = {"id": m.group(1), label_key: label}
        if last:
            row = dict(last)
            if hint:
                row[hint_key] = re.sub(r"\s+", " ", decode_entities(hint)).strip()
            out.append(row)
    return out


def parse_people_list(inner: str) -> list:
    return _parse_entry_list(inner, "id", "label", "hint")


def parse_films_list(inner: str) -> list:
    return _parse_entry_list(inner, "id", "title", "details")


def parse_search_page(html: str) -> dict:
    if re.search(r"<b>\s*Nic nie znalazłem\s*</b>", html, re.IGNORECASE):
        return {"people": [], "films": [], "empty_message": "Nic nie znalazłem"}
    people_block = re.search(
        r'<ul class="wynikiszukania wynikiszukaniaosoba">([\s\S]*?)</ul>', html, re.IGNORECASE
    )
    films_block = re.search(r'<ul class="wynikiszukania">([\s\S]*?)</ul>', html, re.IGNORECASE)
    people = parse_people_list(people_block.group(1)) if people_block else []
    films = parse_films_list(films_block.group(1)) if films_block else []
    return {"people": people, "films": films}


def extract_article_html(page: str) -> str | None:
    m = re.search(r'<article id="(?:film|osoba)"[^>]*>([\s\S]*?)</article>', page, re.IGNORECASE)
    if m and m.group(1):
        return m.group(1)
    m2 = re.search(r"<article\b[^>]*>([\s\S]*?)</article>", page, re.IGNORECASE)
    if m2 and m2.group(1):
        return m2.group(1)
    m3 = re.search(r"<main\b[^>]*>([\s\S]*?)</main>", page, re.IGNORECASE)
    return m3.group(1) if m3 else None


def cmd_search(args: argparse.Namespace) -> None:
    print(USAGE_POLICY_NOTE, file=sys.stderr)
    rodzaj = MATCH_MODE_TO_RODZAJ[args.match_mode]
    url = build_query(INDEX, {"szukaj": args.query, "rodzaj": rodzaj})
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling filmpolski_search: {e}")
        return

    parsed = parse_search_page(html)
    payload = {
        "source": "filmpolski.pl",
        "query": args.query,
        "match_mode": args.match_mode,
        "rodzaj": rodzaj,
        **parsed,
        "ui_search": url,
        "ui_record": f"{INDEX}/{{id}}",
    }
    print_result(payload)


def cmd_get_item(args: argparse.Namespace) -> None:
    print(USAGE_POLICY_NOTE, file=sys.stderr)
    url = f"{INDEX}/{args.id}"
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling filmpolski_get_item: {e}")
        return

    inner = extract_article_html(html)
    if not inner:
        fail(
            f"Error calling filmpolski_get_item: could not find record body for "
            f"item_id={args.id} at {url} (wrong id, or page layout changed)."
        )
        return

    text = strip_to_plain(inner)
    truncated = False
    if len(text) > MAX_RECORD_CHARS:
        text = text[:MAX_RECORD_CHARS]
        truncated = True
    kind = "film" if re.search(r'<article id="film"', html, re.IGNORECASE) else "osoba"

    payload = {
        "item_id": args.id,
        "kind": kind,
        "url": url,
        "text": text,
        "truncated": truncated,
        "source": "filmpolski.pl",
    }
    print_result(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filmpolski.py",
        description="FilmPolski.pl (Polish Film Database) HTML client. No API key required. "
        + USAGE_POLICY_NOTE,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Search FilmPolski.pl (films, TV, theatre, people/institutions)")
    p.add_argument("--query", required=True, dest="query",
                    help="Search phrase (film title fragment or person's surname).")
    p.add_argument(
        "--mode", "--match-mode", dest="match_mode", default="fragment",
        choices=["fragment", "start", "exact"],
        help="Match mode: fragment (substring, rodzaj=1, default), start (title/name prefix, "
        "rodzaj=2, Polish: poczatek), exact (exact title/name, rodzaj=3, Polish: dokladnie; "
        "for persons use 'Surname, Firstname' with a comma).",
    )
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get-item", help="Fetch one FilmPolski.pl record by numeric id")
    p.add_argument("--id", required=True, type=int, dest="id",
                    help="Numeric record id from search results (index.php/{id}).")
    p.set_defaults(func=cmd_get_item)

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
