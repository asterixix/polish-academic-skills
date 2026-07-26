#!/usr/bin/env python3
"""PBN -- Polska Bibliografia Naukowa (REST API v1).

Swagger: https://pbn.nauka.gov.pl/api/
Help:    https://pbn.nauka.gov.pl/centrum-pomocy/kategoria/api/

Search and metadata endpoints require institutional credentials
(X-App-Id / X-App-Token). Obtain access via the PBN Helpdesk after
integration on the test environment:
  https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/
  https://pbn.nauka.gov.pl/centrum-pomocy/baza-wiedzy/sposob-uzyskania-dostepu-do-api-w-wersji-produkcyjnej/

Reads credentials from the environment:
  PBN_APP_ID     (required)
  PBN_APP_TOKEN  (required)
  PBN_USER_TOKEN (optional, for operations needing a user context)

Subcommands mirror the original MCP tools:
  search-publications  -> POST /v1/search/publications
  search-persons       -> POST /v1/search/persons
  get-publication      -> GET  /v1/publications/id/{id}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse

from _http import fail, print_result, prune, request

API_BASE = "https://pbn.nauka.gov.pl/api/v1"

PBN_ACCESS_HELP = (
    "PBN API requires PBN_APP_ID and PBN_APP_TOKEN environment variables "
    "(optionally PBN_USER_TOKEN for user-context operations).\n"
    "Get access: https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/\n"
    "Details: https://pbn.nauka.gov.pl/centrum-pomocy/baza-wiedzy/sposob-uzyskania-dostepu-do-api-w-wersji-produkcyjnej/"
)


def require_pbn_headers(with_json_body: bool) -> dict:
    """Build PBN auth headers from the environment, or fail(1) with a clear
    message BEFORE any network call is attempted."""
    app_id = (os.environ.get("PBN_APP_ID") or "").strip()
    app_token = (os.environ.get("PBN_APP_TOKEN") or "").strip()
    if not app_id or not app_token:
        fail(PBN_ACCESS_HELP)

    headers = {
        "Accept": "application/json",
        "X-App-Id": app_id,
        "X-App-Token": app_token,
    }
    if with_json_body:
        headers["Content-Type"] = "application/json"
    user_token = (os.environ.get("PBN_USER_TOKEN") or "").strip()
    if user_token:
        headers["X-User-Token"] = user_token
    return headers


def handle_http_error(err: RuntimeError, tool_name: str) -> None:
    msg = str(err)
    if "HTTP 401" in msg or "HTTP 403" in msg:
        fail(
            f"Error calling {tool_name}: {msg}\n"
            "Authentication failed or forbidden. Verify PBN_APP_ID / PBN_APP_TOKEN "
            "(and PBN_USER_TOKEN if the operation needs a user context). "
            "See https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/"
        )
    fail(f"Error calling {tool_name}: {msg}")


def cmd_search_publications(args: argparse.Namespace) -> None:
    headers = require_pbn_headers(with_json_body=True)
    body = prune(
        {
            "title": args.title,
            "doi": args.doi,
            "isbn": args.isbn,
            "issn": args.issn,
            "year": args.year,
            "yearFrom": args.year_from,
            "yearTo": args.year_to,
            "type": args.type,
            "authors": args.authors or [],
            "objectId": args.object_id,
            "page": args.page,
            "size": args.size,
        }
    )
    url = f"{API_BASE}/search/publications"
    try:
        _status, resp_body, _h = request(
            url, method="POST", headers=headers, data=json.dumps(body).encode("utf-8")
        )
    except RuntimeError as e:
        handle_http_error(e, "pbn_search_publications")
        return
    print_result(json.loads(resp_body.decode("utf-8")))


def cmd_search_persons(args: argparse.Namespace) -> None:
    headers = require_pbn_headers(with_json_body=True)
    body = prune(
        {
            "firstName": args.first_name,
            "lastName": args.last_name,
            "orcid": args.orcid,
            "objectId": args.object_id,
            "page": args.page,
            "size": args.size,
        }
    )
    url = f"{API_BASE}/search/persons"
    try:
        _status, resp_body, _h = request(
            url, method="POST", headers=headers, data=json.dumps(body).encode("utf-8")
        )
    except RuntimeError as e:
        handle_http_error(e, "pbn_search_persons")
        return
    print_result(json.loads(resp_body.decode("utf-8")))


def cmd_get_publication(args: argparse.Namespace) -> None:
    headers = require_pbn_headers(with_json_body=False)
    encoded_id = urllib.parse.quote(args.id, safe="")
    url = f"{API_BASE}/publications/id/{encoded_id}"
    try:
        _status, resp_body, _h = request(url, method="GET", headers=headers)
    except RuntimeError as e:
        handle_http_error(e, "pbn_get_publication")
        return
    print_result(json.loads(resp_body.decode("utf-8")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pbn.py",
        description="PBN (Polska Bibliografia Naukowa) REST API v1 client. "
        "Requires PBN_APP_ID and PBN_APP_TOKEN environment variables.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search-publications", help="POST /v1/search/publications")
    p.add_argument("--title", help="Title fragment.")
    p.add_argument("--doi", help="DOI identifier.")
    p.add_argument("--isbn", help="ISBN number.")
    p.add_argument("--issn", help="ISSN number.")
    p.add_argument("--year", type=int, help="Single publication year.")
    p.add_argument("--year-from", type=int, help="Lower bound of year range.")
    p.add_argument("--year-to", type=int, help="Upper bound of year range.")
    p.add_argument(
        "--type",
        choices=["BOOK", "EDITED_BOOK", "CHAPTER", "ARTICLE", "PROCEEDINGS"],
        help="Publication type.",
    )
    p.add_argument("--authors", nargs="+", help="List of authors (API applies AND).")
    p.add_argument("--object-id", help="PBN object id, if known.")
    p.add_argument("--page", type=int, default=0, help="Zero-based page index (default 0).")
    p.add_argument("--size", type=int, default=20, help="Page size, 1-100 (default 20).")
    p.set_defaults(func=cmd_search_publications)

    p = sub.add_parser("search-persons", help="POST /v1/search/persons")
    p.add_argument("--first-name", help="First name.")
    p.add_argument("--last-name", help="Last name.")
    p.add_argument("--orcid", help="ORCID identifier.")
    p.add_argument("--object-id", help="PBN person object id.")
    p.add_argument("--page", type=int, default=0, help="Zero-based page index (default 0).")
    p.add_argument("--size", type=int, default=20, help="Page size, 1-100 (default 20).")
    p.set_defaults(func=cmd_search_persons)

    p = sub.add_parser("get-publication", help="GET /v1/publications/id/{id}")
    p.add_argument("--id", required=True, dest="id", help="PBN publication object id.")
    p.set_defaults(func=cmd_get_publication)

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
