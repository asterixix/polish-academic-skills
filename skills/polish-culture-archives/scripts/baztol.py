#!/usr/bin/env python3
"""BazTOL -- subject gateway of Polish technical-science web resources
(Biblioteka Politechniki Poznanskiej).

Web UI: https://baztol.library.put.poznan.pl/ -- there is no public JSON API;
this script replays the same HTML form POST / detail GET the browser uses
(Apache + Perl CGI).

*** KNOWN LIMITATION: the portal has NOT been actively updated since
    2022-01-01 (per the site's own notice). Content returned here may be
    stale -- treat it as a historical snapshot, not a live catalogue. ***

Subcommands mirror the original MCP tools:
  search          -> POST akcja=szukanie_proste (full-text, wyr_wysz=), 20 hits/page
  browse-domain   -> POST akcja=przegladanie&dziedzina_id=... (sidebar subject domains)
  get-resource    -> GET  ?id=... (resource detail page)

All responses are raw HTML (Apache + Perl CGI, no JSON), returned wrapped in
a small JSON envelope: {"url": ..., "html": "<...>"}.
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse

from _http import fail, print_result, request_text

API_ORIGIN = "http://baztol.library.put.poznan.pl"
READER_PATH = "/baztol_czytelnik/baztol"
READER_URL = f"{API_ORIGIN}{READER_PATH}"
HTML_ACCEPT = "text/html; charset=utf-8"

PAGE_SIZE = 20

STALE_NOTE = (
    "BazTOL has not been actively updated since 2022-01-01 (site notice). "
    "Results reflect a historical snapshot of the catalogue, not current holdings."
)

# Subject domain ids (sidebar) -- same as BazTOL "przegladanie" links.
BAZTOL_DOMAINS = {
    24: "Architektura",
    25: "Automatyka",
    26: "Biotechnologia",
    27: "Budownictwo",
    28: "Chemia",
    29: "Elektronika i Telekomunikacja",
    30: "Elektrotechnika i Energetyka",
    31: "Fizyka i Astronomia",
    32: "Geodezja i Kartografia",
    33: "Gornictwo i Geologia",
    34: "Informatyka",
    35: "Inzynieria i Ochrona Srodowiska",
    36: "Inzynieria Materialowa",
    37: "Matematyka",
    38: "Mechanika",
    39: "Oceanologia i Oceanotechnika",
    40: "Transport",
    41: "Zarzadzanie",
    42: "Zrodla ogolne",
}


def _post_form(body_params: dict) -> str:
    body = urllib.parse.urlencode(body_params).encode("utf-8")
    headers = {
        "Accept": HTML_ACCEPT,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    return request_text(READER_URL, method="POST", headers=headers, data=body)


def cmd_search(args: argparse.Namespace) -> None:
    body_params = {
        "akcja": "szukanie_proste",
        "dziedzina_id": "",
        "wyr_wysz": args.query,
        "button_proste": "Szukaj",
    }
    if args.page > 1:
        body_params["offset"] = str((args.page - 1) * PAGE_SIZE)
        body_params["kierunek"] = "przod"
    try:
        html = _post_form(body_params)
    except RuntimeError as e:
        fail(f"Error calling baztol_search: {e}")
        return
    print_result({
        "query": args.query,
        "page": args.page,
        "page_size": PAGE_SIZE,
        "url": READER_URL,
        "note": STALE_NOTE,
        "html": html,
    })


def cmd_browse_domain(args: argparse.Namespace) -> None:
    if args.domain_id not in BAZTOL_DOMAINS:
        fail(
            f"Error calling baztol_browse_domain: domain_id must be one of the sidebar ids "
            f"(24-42): {sorted(BAZTOL_DOMAINS)}"
        )
        return
    body_params = {
        "akcja": "przegladanie",
        "dziedzina_id": str(args.domain_id),
    }
    if args.page > 1:
        body_params["offset"] = str((args.page - 1) * PAGE_SIZE)
        body_params["kierunek"] = "przod"
    try:
        html = _post_form(body_params)
    except RuntimeError as e:
        fail(f"Error calling baztol_browse_domain: {e}")
        return
    print_result({
        "domain_id": args.domain_id,
        "domain_label": BAZTOL_DOMAINS[args.domain_id],
        "page": args.page,
        "page_size": PAGE_SIZE,
        "url": READER_URL,
        "note": STALE_NOTE,
        "html": html,
    })


def cmd_get_resource(args: argparse.Namespace) -> None:
    url = f"{READER_URL}?id={args.id}"
    try:
        html = request_text(url, headers={"Accept": HTML_ACCEPT})
    except RuntimeError as e:
        fail(f"Error calling baztol_get_resource: {e}")
        return
    print_result({
        "resource_id": args.id,
        "url": url,
        "note": STALE_NOTE,
        "html": html,
    })


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="baztol.py",
        description=(
            "BazTOL (baztol.library.put.poznan.pl) -- Polish technical-science web resources "
            "gateway. HTML scraping, no JSON API. NOT updated since 2022-01-01."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("search", help="Full-text search (20 hits/page, server-side).")
    ps.add_argument("--query", required=True, help="Search phrase.")
    ps.add_argument("--page", type=int, default=1, help="Page number (1-based, 20 results/page). Default 1.")
    ps.set_defaults(func=cmd_search)

    pb = sub.add_parser("browse-domain", help="Browse by subject domain id (sidebar categories).")
    pb.add_argument("--domain-id", type=int, required=True, help="Domain id 24-42, e.g. 34=Informatyka. See reference/API.md for the full list.")
    pb.add_argument("--page", type=int, default=1, help="Page number (1-based, 20 results/page). Default 1.")
    pb.set_defaults(func=cmd_browse_domain)

    pr = sub.add_parser("get-resource", help="Fetch a single resource detail page by numeric id.")
    pr.add_argument("--id", type=int, required=True, help="Resource id from search/browse result links (?id=...).")
    pr.set_defaults(func=cmd_get_resource)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
