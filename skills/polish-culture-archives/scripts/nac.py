#!/usr/bin/env python3
"""NAC -- Narodowe Archiwum Cyfrowe (www.nac.gov.pl).

The institutional site is WordPress (RSS + REST). Digitized archival
holdings are published separately in "Szukaj w Archiwach"
(https://szukajwarchiwach.gov.pl/) -- there is no documented public JSON API
for that archive search, and the service often sits behind bot/WAF
protection, so it is out of scope here.

WAF note: this script uses the `?rest_route=/wp/v2/...` query-string form of
the WordPress REST API instead of the prettier `/wp-json/wp/v2/...` path
form. This mirrors the original MCP server exactly -- the origin's WAF is
more likely to block the pretty-permalink `/wp-json/` path than the
`?rest_route=` query form, so the latter is the more robust choice here.

Subcommands mirror the original MCP tools:
  news-rss     -> GET https://www.nac.gov.pl/feed/ (RSS 2.0, XML)
  site-search  -> GET ?rest_route=/wp/v2/search
  get-post     -> GET ?rest_route=/wp/v2/posts/{id}
  get-page     -> GET ?rest_route=/wp/v2/pages/{id}
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse

from _http import fail, print_result, request_json, request_text

SITE = "https://www.nac.gov.pl"
RSS_URL = f"{SITE}/feed/"
WP_REST_BASE = f"{SITE}/?rest_route=/wp/v2"

JSON_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "pl,en;q=0.8",
    "Referer": f"{SITE}/",
}
RSS_HEADERS = {"Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8"}

SUBTYPE_CHOICES = ["post", "page"]


def build_wp_rest_url(path: str, params: dict | None = None) -> str:
    """Build a `?rest_route=/wp/v2/...` URL, appending extra params with `&`
    (the base URL already contains the `?rest_route=...` query string, so
    subsequent params must be joined with `&`, never a second `?`)."""
    clean_path = path.lstrip("/")
    base = f"{WP_REST_BASE}/{clean_path}"
    if not params:
        return base
    pairs = []
    for k, v in params.items():
        if v is None or v == "":
            continue
        if isinstance(v, (list, tuple)):
            for item in v:
                if item is None or item == "":
                    continue
                pairs.append((k, str(item)))
        else:
            pairs.append((k, str(v)))
    if not pairs:
        return base
    return f"{base}&{urllib.parse.urlencode(pairs)}"


def cmd_news_rss(args: argparse.Namespace) -> None:
    try:
        xml_text = request_text(RSS_URL, headers=RSS_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling nac_news_rss: {e}")
        return
    print_result({
        "url": RSS_URL,
        "note": (
            "This is the institutional news feed (aktualnosci), not the digitized "
            "archival catalogue -- that lives on szukajwarchiwach.gov.pl, which has "
            "no stable public REST API."
        ),
        "rss_xml": xml_text,
    })


def cmd_site_search(args: argparse.Namespace) -> None:
    params = {"search": args.query, "per_page": args.per_page, "subtype": args.subtypes}
    url = build_wp_rest_url("search", params)
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        msg = str(e)
        if "HTTP 403" in msg:
            fail(
                f"Error calling nac_site_search: {msg}\n"
                "HTTP 403 may indicate the origin's WAF is blocking automated clients; "
                "try again later, from a different network, or use the website directly."
            )
        fail(f"Error calling nac_site_search: {msg}")
        return
    print_result(result)


def cmd_get_post(args: argparse.Namespace) -> None:
    url = build_wp_rest_url(f"posts/{args.id}")
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling nac_get_post: {e}")
        return
    print_result(result)


def cmd_get_page(args: argparse.Namespace) -> None:
    url = build_wp_rest_url(f"pages/{args.id}")
    try:
        result = request_json(url, headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling nac_get_page: {e}")
        return
    print_result(result)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nac.py",
        description="NAC -- Narodowe Archiwum Cyfrowe (www.nac.gov.pl) institutional site: news feed + WordPress REST content.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("news-rss", help="Fetch the NAC institutional news RSS 2.0 feed (XML).")
    pr.set_defaults(func=cmd_news_rss)

    ps = sub.add_parser("site-search", help="Search posts/pages on nac.gov.pl via WordPress REST.")
    ps.add_argument("--query", required=True, help="Search phrase (Polish keywords).")
    ps.add_argument("--per-page", type=int, default=10, help="Max results (1-50). Default 10.")
    ps.add_argument("--subtypes", nargs="+", choices=SUBTYPE_CHOICES, default=["post", "page"], help="WordPress object subtypes to search. Default both.")
    ps.set_defaults(func=cmd_site_search)

    pp = sub.add_parser("get-post", help="Fetch a single blog post by numeric id.")
    pp.add_argument("--id", type=int, required=True, help="Post id from nac_site_search or a URL.")
    pp.set_defaults(func=cmd_get_post)

    pg = sub.add_parser("get-page", help="Fetch a single static page by numeric id.")
    pg.add_argument("--id", type=int, required=True, help="Page id from nac_site_search.")
    pg.set_defaults(func=cmd_get_page)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
