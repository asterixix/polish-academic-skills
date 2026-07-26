#!/usr/bin/env python3
"""Fototeka Slaska -- Muzeum Wsi Opolskiej, https://fototekaslaska.pl/

WordPress site. A general `/wp-json/` exists, but the gallery post type has
no public `wp/v2/{post_type}` endpoint for individual records (404).
Search is a GET on the homepage with form parameters (`s`, `t`, `y`,
optionally `paged`).

This script is a DIRECT PORT of the regex-based parsing in the source TS
tool (fototekaslaska.ts): parseSearchList / parsePhotoPage / stripToPlain /
decodeEntities match field-for-field, including the important detail that
search results are parsed ONLY from the `.search-list` block (up to the
`<h3 class="serch-recently-added">` marker) so the "recently added" section
on the same page is never mixed into search results.

Subcommands mirror the original MCP tools:
  search      -> GET /?s=&t=&y=&paged=  (parses only the .search-list block)
  get-photo   -> GET /galeria/{slug}/
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse

from _http import decode_entities, fail, print_result, request_text, strip_to_plain

SITE = "https://fototekaslaska.pl"
HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl,de;q=0.8,en;q=0.7",
}

MAX_DETAIL_CHARS = 20_000


def parse_search_list(html: str) -> dict:
    if re.search(r'class="result-empty"', html) or re.search(r"Nic nie znaleziono", html, re.IGNORECASE):
        m = re.search(r'<div class="result-empty">\s*([^<]+)', html, re.IGNORECASE)
        empty_message = re.sub(r"\s+", " ", m.group(1)).strip() if m else "Nic nie znaleziono."
        return {"items": [], "empty_message": empty_message}

    block = re.search(
        r'<div class="search-list">([\s\S]*?)<h3 class="serch-recently-added">', html, re.IGNORECASE
    )
    if not block:
        return {"items": [], "empty_message": "Brak sekcji wynikow (nieznany uklad strony)."}

    inner = block.group(1)
    items: list = []
    li_re = re.compile(
        r'<div class="gallery-listing-single">\s*<a href="(https?://[^"]+)"[^>]*>([\s\S]*?)</a>\s*</div>',
        re.IGNORECASE,
    )
    for m in li_re.finditer(inner):
        url = m.group(1)
        slug_m = re.search(r"/galeria/([^/]+)/?", url)
        if not slug_m:
            continue
        slug = slug_m.group(1)
        body = m.group(2)
        img_m = re.search(r'data-src="(https?://[^"]+)"', body, re.IGNORECASE) or re.search(
            r'<img[^>]*src="(https?://[^"]+)"', body, re.IGNORECASE
        )
        cap_m = re.search(r'<div class="gallery-listing-details">\s*([^<]+)', body, re.IGNORECASE)
        caption = re.sub(r"\s+", " ", decode_entities(cap_m.group(1))).strip() if cap_m else ""
        row = {"slug": slug, "url": url, "caption": caption}
        if img_m:
            row["image_url"] = img_m.group(1)
        items.append(row)

    return {"items": items}


def parse_photo_page(html: str) -> dict:
    title_m = re.search(
        r'<div class="[^"]*\bsingle-gallery\b[^"]*"[^>]*>\s*<h2>([^<]+)</h2>', html, re.IGNORECASE
    )
    title = title_m.group(1).strip() if title_m else None

    cat_m = re.search(r'<p class="single-gallery-n">([^<]+)</p>', html, re.IGNORECASE)
    catalog_note = cat_m.group(1).strip() if cat_m else None

    image_m = re.search(
        r'<a class="gallery-listing-box[^"]*" href="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"',
        html,
        re.IGNORECASE,
    )
    if not image_m:
        image_m = re.search(
            r'<img class="lazy single-gallery-image"[^>]*data-src="(https?://[^"]+)"', html, re.IGNORECASE
        )
    image_url = image_m.group(1) if image_m else None

    details_m = re.search(r'<div class="single-gallery-details">([\s\S]*?)</div>', html, re.IGNORECASE)
    details_html = details_m.group(1) if details_m else ""
    details_text = strip_to_plain(details_html)
    if len(details_text) > MAX_DETAIL_CHARS:
        details_text = f"{details_text[:MAX_DETAIL_CHARS]}… [truncated]"

    return {
        "title": decode_entities(title) if title else None,
        "catalog_note": decode_entities(catalog_note) if catalog_note else None,
        "image_url": image_url,
        "details_text": details_text,
    }


def cmd_search(args: argparse.Namespace) -> None:
    qs = {"s": args.query, "t": args.field}
    if args.year_period is not None:
        qs["y"] = args.year_period
    if args.page > 1:
        qs["paged"] = str(args.page)
    url = f"{SITE}/?{urllib.parse.urlencode(qs)}"

    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fototekaslaska_search: {e}")
        return

    parsed = parse_search_list(html)
    payload = {
        "source": "fototekaslaska.pl",
        "query": args.query,
        "field": args.field,
        "year_period": args.year_period,
        "page": args.page,
        "search_url": url,
        **parsed,
    }
    print_result(payload)


def cmd_get_photo(args: argparse.Namespace) -> None:
    safe = re.sub(r"^/+|/+$", "", args.slug)
    safe = re.sub(r"^galeria/", "", safe)
    url = f"{SITE}/galeria/{urllib.parse.quote(safe)}/"

    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fototekaslaska_get_photo: {e}")
        return

    parsed = parse_photo_page(html)
    if not parsed.get("title") and not parsed.get("details_text"):
        fail(
            f"Error calling fototekaslaska_get_photo: could not parse gallery record "
            f"for slug={safe} at {url} (layout changed?)."
        )
        return

    payload = {"slug": safe, "url": url, **parsed, "source": "fototekaslaska.pl"}
    print_result(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fototeka_slaska.py",
        description="Fototeka Slaska (Muzeum Wsi Opolskiej) HTML client. No API key required.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Search Fototeka Slaska (rural Silesia / Opole region historical photos)")
    p.add_argument("--query", required=True, dest="query", help="Search phrase.")
    p.add_argument(
        "--field", "--title", dest="field", default="title",
        choices=["title", "place", "district", "description", "catalog_n"],
        help="Metadata field to search (form param t): title (default), place, district, "
        "description, or catalog_n.",
    )
    p.add_argument(
        "--period", "--year-period", dest="year_period", default=None,
        choices=["do1900", "1900-1918", "1918-1939", "1939-1945"],
        help="Optional historical period filter (form param y). Omit to search all periods.",
    )
    p.add_argument("--page", type=int, default=1, help="Result page, 1-based (default 1).")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get-photo", help="Fetch one gallery photo page by URL slug")
    p.add_argument("--slug", required=True, dest="slug",
                    help="URL segment after /galeria/, e.g. dzieci-przed-domem "
                    "(value from fototeka_slaska.py search results).")
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
