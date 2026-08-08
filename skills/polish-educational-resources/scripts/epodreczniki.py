#!/usr/bin/env python3
"""
epodreczniki.pl -- Zintegrowana Platforma Edukacyjna (Integrated Educational
Platform), Osrodek Rozwoju Edukacji (ORE)/MEN. Free K-12 e-textbooks and
learning resources, Creative Commons licensed.

Public "otwarte API" (open API), documented in a PDF from ORE:
https://ore.edu.pl/attachments/article/6993/Otwarte_API_platformy.pdf
It is a Django REST Framework (DRF) browsable API: the root endpoint lists
links to every available resource collection, each of which supports
`?format=json` for machine-readable output.

*** PARTIALLY VERIFIED: the root endpoint and the `?format=json` content
    negotiation convention are confirmed from the ORE documentation. The
    exact set of collection names/paths under the root, and whether
    individual collections support filtering (?search=, ?page=), were NOT
    independently confirmed (no live network access from this environment)
    -- DRF's own conventions are assumed. Always run `root` first to see
    the real, current list of collections before guessing a --path. ***

Subcommands:
  root    -- GET the API root (collections index); lists every available resource endpoint.
  browse  -- GET an arbitrary relative path under the API root, with optional
             passthrough query parameters (e.g. search, page) and format=json forced.

Source: https://epodreczniki.pl (API: http://api.epodreczniki.pl)
"""

from __future__ import annotations

import argparse
import json

import _http

API_BASE = "http://api.epodreczniki.pl"


def cmd_root(_args: argparse.Namespace) -> dict:
    url = f"{API_BASE}/collections/?format=json"
    raw = _http.fetch(url, headers={"Accept": "application/json"})
    return {"url": url, "collections": _http.parse_json_response(raw, url)}


def cmd_browse(args: argparse.Namespace) -> dict:
    path = args.path.strip("/")
    params: list[tuple[str, str]] = [("format", "json")]
    if args.search:
        params.append(("search", args.search))
    if args.page:
        params.append(("page", str(args.page)))
    for kv in args.param or []:
        if "=" not in kv:
            raise ValueError(f"--param must be KEY=VALUE, got: {kv!r}")
        k, v = kv.split("=", 1)
        params.append((k, v))

    url = f"{API_BASE}/{path}/?{_http.build_query(params)}"
    raw = _http.fetch(url, headers={"Accept": "application/json"})
    return {"url": url, "data": _http.parse_json_response(raw, url)}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="epodreczniki.pl -- Integrated Educational Platform (ORE/MEN) open API client."
    )
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("root", help="List every available resource collection (run this first).")
    r.set_defaults(func=cmd_root)

    b = sub.add_parser(
        "browse",
        help="Fetch/search a specific collection path (from `root`'s output) with optional filters.",
    )
    b.add_argument("--path", required=True, help="Relative collection path, e.g. 'textbooks' or 'units' (from `root`'s output). No leading/trailing slash needed.")
    b.add_argument("--search", default=None, help="Best-effort free-text filter (DRF SearchFilter convention -- not confirmed supported on every collection).")
    b.add_argument("--page", type=int, default=None, help="Best-effort page number (DRF PageNumberPagination convention).")
    b.add_argument(
        "--param", action="append", default=None,
        help="Extra raw query parameter as KEY=VALUE (repeatable), for filters discovered via `root`/trial and error.",
    )
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
