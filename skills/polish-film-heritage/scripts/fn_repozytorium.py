#!/usr/bin/env python3
"""Repozytorium Cyfrowe Filmoteki Narodowej, https://repozytorium.fn.org.pl/

No public JSON REST API; the site is Drupal 7 + Apache Solr. Search and
browse replay the same GET URLs the browser itself uses (`?q=pl/...`);
responses are HTML (result tiles, facets, record pages). Terms of use /
overview: https://repozytorium.fn.org.pl/?q=pl/node/10 (no machine API doc).

The upstream MCP tool (filmoteka-repo.ts) returns ALL FOUR of these pages
as raw, unparsed HTML -- it does no extraction at all. This script
additionally extracts a best-effort `items`/`title`/`text` on top of the
raw page for usability, using a generic "any link to node/{id}" heuristic
(extract_id_links in _http.py). This could NOT be verified against a live
fetch of repozytorium.fn.org.pl (sandbox blocks outbound HTTPS) -- treat
`items`/`title`/`text` as best-effort only; `raw_html` (capped) is always
included as a fallback. See reference/API.md for the exact caveat and the
Drupal URL-encoding quirk reproduced by build_site_search_url() /
build_film_index_url() below.

Subcommands mirror the original MCP tools:
  search        -> GET /?q={lang}/search/site/{query}[&page=][&f[i]=facet]
  get-node      -> GET /?q={lang}/node/{id}
  film-index    -> GET /?q={lang}/fnsearch/film_index/{letter|-}
  browse-kind   -> GET /?q={lang}/search/{feature|doc|animation|magazine}
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse

from _http import (
    extract_body_text,
    extract_id_links,
    extract_title,
    fail,
    print_result,
    request_text,
)

ORIGIN = "https://repozytorium.fn.org.pl"
HTML_HEADERS = {"Accept": "text/html; charset=utf-8"}

MAX_RAW_HTML_CHARS = 20_000
MAX_DETAIL_TEXT_CHARS = 15_000

KIND_CHOICES = ["feature", "doc", "animation", "magazine"]


def build_site_search_url(query: str, lang: str, facets: list | None, page: int | None) -> str:
    """Mirrors buildSiteSearchUrl() in filmoteka-repo.ts, INCLUDING its
    double-encoding of `query`: the TS code encodeURIComponent()s the query
    into the path fragment first, then hands the whole `q` value to
    URLSearchParams.set(), which percent-encodes it a second time. That is
    reproduced here via urlencode() over an already-quoted path segment."""
    path = f"search/site/{urllib.parse.quote(query, safe='')}"
    q_value = f"{lang}/{path}"
    params = [("q", q_value)]
    if page is not None and page > 0:
        params.append(("page", str(page)))
    if facets:
        for i, f in enumerate(facets):
            params.append((f"f[{i}]", f))
    return f"{ORIGIN}/?{urllib.parse.urlencode(params)}"


def build_node_url(node_id: int, lang: str) -> str:
    q_value = f"{lang}/node/{node_id}"
    return f"{ORIGIN}/?{urllib.parse.urlencode({'q': q_value})}"


def build_film_index_url(letter: str, lang: str) -> str:
    # Mirrors the TS segment = letter === "-" ? "-" : encodeURIComponent(letter)
    # followed by a second encoding pass via URLSearchParams -- same
    # intentional double-encoding as build_site_search_url() above.
    segment = "-" if letter == "-" else urllib.parse.quote(letter, safe="")
    q_value = f"{lang}/fnsearch/film_index/{segment}"
    return f"{ORIGIN}/?{urllib.parse.urlencode({'q': q_value})}"


def build_browse_kind_url(kind: str, lang: str) -> str:
    q_value = f"{lang}/search/{kind}"
    return f"{ORIGIN}/?{urllib.parse.urlencode({'q': q_value})}"


def _cap_raw_html(html: str) -> tuple:
    if len(html) > MAX_RAW_HTML_CHARS:
        return html[:MAX_RAW_HTML_CHARS], True
    return html, False


def cmd_search(args: argparse.Namespace) -> None:
    url = build_site_search_url(args.query, args.lang, args.facets, args.page)
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fn_repo_search: {e}")
        return

    items = extract_id_links(html, "node", base_url=ORIGIN)
    raw_html, raw_truncated = _cap_raw_html(html)
    payload = {
        "source": "repozytorium.fn.org.pl",
        "query": args.query,
        "lang": args.lang,
        "facets": args.facets,
        "page": args.page,
        "search_url": url,
        "items": items,
        "items_note": (
            "Best-effort extraction from any link to node/{id} on the results "
            "page; unverified against live markup -- use raw_html to "
            "cross-check if this list looks incomplete or empty."
        ),
        "raw_html": raw_html,
        "raw_html_truncated": raw_truncated,
    }
    print_result(payload)


def cmd_get_node(args: argparse.Namespace) -> None:
    url = build_node_url(args.id, args.lang)
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fn_repo_get_node: {e}")
        return

    title = extract_title(html)
    text, truncated = extract_body_text(html, MAX_DETAIL_TEXT_CHARS)
    related = extract_id_links(html, "node", base_url=ORIGIN)
    # Drop self-link from "related" if present.
    related = [r for r in related if r["id"] != args.id]

    payload = {
        "node_id": args.id,
        "lang": args.lang,
        "url": url,
        "title": title,
        "text": text,
        "text_truncated": truncated,
        "related_nodes": related,
        "source": "repozytorium.fn.org.pl",
        "note": (
            "title/text are a best-effort whole-page extraction, unverified "
            "against live markup (sandbox blocks outbound HTTPS). Re-fetch "
            "the url directly if fields look wrong or incomplete."
        ),
    }
    print_result(payload)


def cmd_film_index(args: argparse.Namespace) -> None:
    url = build_film_index_url(args.letter, args.lang)
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fn_repo_film_index: {e}")
        return

    items = extract_id_links(html, "node", base_url=ORIGIN)
    raw_html, raw_truncated = _cap_raw_html(html)
    payload = {
        "letter": args.letter,
        "lang": args.lang,
        "url": url,
        "items": items,
        "items_note": (
            "Best-effort extraction from any link to node/{id} on the index "
            "page; unverified against live markup -- use raw_html to "
            "cross-check if this list looks incomplete or empty."
        ),
        "raw_html": raw_html,
        "raw_html_truncated": raw_truncated,
        "source": "repozytorium.fn.org.pl",
    }
    print_result(payload)


def cmd_browse_kind(args: argparse.Namespace) -> None:
    url = build_browse_kind_url(args.kind, args.lang)
    try:
        html = request_text(url, headers=HTML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling fn_repo_browse_kind: {e}")
        return

    items = extract_id_links(html, "node", base_url=ORIGIN)
    raw_html, raw_truncated = _cap_raw_html(html)
    payload = {
        "kind": args.kind,
        "lang": args.lang,
        "url": url,
        "items": items,
        "items_note": (
            "Best-effort extraction from any link to node/{id} on the browse "
            "page; unverified against live markup -- use raw_html to "
            "cross-check if this list looks incomplete or empty."
        ),
        "raw_html": raw_html,
        "raw_html_truncated": raw_truncated,
        "source": "repozytorium.fn.org.pl",
    }
    print_result(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fn_repozytorium.py",
        description="Repozytorium Cyfrowe Filmoteki Narodowej (Drupal+Solr) HTML client. "
        "No API key required.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Solr site search (result tiles)")
    p.add_argument("--query", required=True, dest="query", help="Search phrase (titles, people, topics).")
    p.add_argument("--lang", default="pl", choices=["pl", "en"], help="Site language segment (default pl).")
    p.add_argument(
        "--facet", action="append", dest="facets", default=None,
        help='Solr facet filter as "field:value", e.g. bundle:doc (documentary), '
        "bundle:feature (fiction), bundle:article, bundle:person, sm_field_year:1964. "
        "Repeat --facet for multiple filters.",
    )
    p.add_argument("--page", type=int, default=None, help="Zero-based result page index (omit for the first page).")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get-node", help="Fetch one catalog node by Drupal node id")
    p.add_argument("--id", required=True, type=int, dest="id", help="Numeric Drupal node id, e.g. 8937.")
    p.add_argument("--lang", default="pl", choices=["pl", "en"], help="Site language segment (default pl).")
    p.set_defaults(func=cmd_get_node)

    p = sub.add_parser("film-index", help="Browse the film title index by first letter")
    p.add_argument(
        "--letter", required=True, dest="letter",
        help="Index key: A-Z, Polish letters (Ą Ć E Ł Ń Ó Ś Ź Ż), or - (dash) for the "
        '"INNE" (other) bucket.',
    )
    p.add_argument("--lang", default="pl", choices=["pl", "en"], help="Site language segment (default pl).")
    p.set_defaults(func=cmd_film_index)

    p = sub.add_parser("browse-kind", help="Browse by production kind (menu presets)")
    p.add_argument(
        "--kind", required=True, dest="kind", choices=KIND_CHOICES,
        help="feature (fabularne), doc (dokumentalne), animation (animacje), "
        "magazine (magazyn filmowy).",
    )
    p.add_argument("--lang", default="pl", choices=["pl", "en"], help="Site language segment (default pl).")
    p.set_defaults(func=cmd_browse_kind)

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
