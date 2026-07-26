#!/usr/bin/env python3
"""Ludzie Nauki (ludzie.nauka.gov.pl) -- public registry of scientist profiles
(OPI / POL-on). SPA under /ln/; REST under /api/profiles-api (no API key).

Subcommands mirror the original MCP tools:
  search           -> GET /v1.1/public/profile/scientistSearchData (paginated)
  semantic-search  -> GET /v1.0/public/profile/semanticSearchData (free text)
  get              -> GET .../{id}/orcid + .../degreesAndTitles + .../keyWords
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse

from _http import build_query, fail, print_result, request_json

API_BASE = "https://ludzie.nauka.gov.pl/api/profiles-api"
PROFILE_URL = "https://ludzie.nauka.gov.pl/ln/profile"
JSON_HEADERS = {"Accept": "application/json"}


def display_name(p: dict) -> str:
    parts = [p.get("title"), p.get("firstName"), p.get("secondName"), p.get("surname")]
    return " ".join(x for x in parts if x).strip()


def summarize_scientist_search(data: dict) -> dict:
    page = data.get("page") or {}
    content = page.get("content") or []
    profiles = []
    for p in content:
        profiles.append(
            {
                "profileId": p.get("profileId"),
                "name": display_name(p) or None,
                "institution": p.get("calculatedInstitutionName"),
                "domainCode": p.get("domainCode"),
                "disciplines": p.get("disciplines"),
                "dead": p.get("dead"),
                "url": f"{PROFILE_URL}/{p.get('profileId')}",
            }
        )
    pageable = page.get("pageable") or {}
    return {
        "totalHits": data.get("totalHits"),
        "page": {
            "number": pageable.get("pageNumber"),
            "size": pageable.get("pageSize"),
            "totalInResponse": page.get("total"),
        },
        "isSemanticSearchNeeded": data.get("isSemanticSearchNeeded"),
        "filterHint": data.get("filterHint"),
        "profiles": profiles,
    }


def summarize_semantic_search(data: dict, max_items: int) -> dict:
    arr = data.get("profileDataResponses") or []
    sliced = arr[:max_items]
    profiles = []
    for p in sliced:
        profiles.append(
            {
                "profileId": p.get("profileId"),
                "name": display_name(p) or None,
                "institution": p.get("calculatedInstitutionName"),
                "domainCode": p.get("domainCode"),
                "disciplines": p.get("disciplines"),
                "dead": p.get("dead"),
                "url": f"{PROFILE_URL}/{p.get('profileId')}",
            }
        )
    return {
        "totalReturned": len(arr),
        "showing": len(profiles),
        "truncated": len(arr) > max_items,
        "profiles": profiles,
    }


def cmd_search(args: argparse.Namespace) -> None:
    params = {
        "page": args.page,
        "size": args.size,
        # Match the TS convention: withTheDead is always sent as "true"/"false".
        "withTheDead": "true" if args.include_deceased else "false",
        "surname": args.surname,
        "firstName": args.first_name,
        "domainCode": args.domain_code,
    }
    url = build_query(f"{API_BASE}/v1.1/public/profile/scientistSearchData", params)
    try:
        data = request_json(url, method="GET", headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error ludzie_search: {e}")
        return
    print_result(summarize_scientist_search(data))


def cmd_semantic_search(args: argparse.Namespace) -> None:
    params = {
        "fullQuery": args.full_query,
        "withTheDead": "true" if args.include_deceased else "false",
    }
    url = build_query(f"{API_BASE}/v1.0/public/profile/semanticSearchData", params)
    try:
        data = request_json(url, method="GET", headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error ludzie_semantic_search: {e}")
        return
    print_result(summarize_semantic_search(data, args.max_profiles))


def cmd_get(args: argparse.Namespace) -> None:
    profile_id = args.id
    encoded = urllib.parse.quote(profile_id, safe="")
    orcid_url = f"{API_BASE}/v1.0/public/profile/{encoded}/orcid"
    degrees_url = f"{API_BASE}/v1.0/public/profile/{encoded}/degreesAndTitles"
    kw_url = f"{API_BASE}/v1.0/public/profile/{encoded}/keyWords"
    try:
        orcid = request_json(orcid_url, method="GET", headers=JSON_HEADERS)
        degrees = request_json(degrees_url, method="GET", headers=JSON_HEADERS)
        keywords = request_json(kw_url, method="GET", headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error ludzie_get_scientist: {e}")
        return
    print_result(
        {
            "profileId": profile_id,
            "profileUrl": f"{PROFILE_URL}/{profile_id}",
            "orcid": orcid,
            "degreesAndTitles": degrees,
            "keywords": keywords,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ludzie_nauki.py",
        description="Ludzie Nauki (ludzie.nauka.gov.pl) public scientist profile registry client (no API key required).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="List/filter profiles (GET scientistSearchData).")
    p.add_argument("--surname", help="Surname filter (partial match). Omit surname/first-name to browse alphabetically.")
    p.add_argument("--first-name", help="First name filter (optional, with or without surname).")
    p.add_argument("--domain-code", help="Scientific domain code, e.g. DZ0106N (exact sciences), DZ0105N (social sciences).")
    p.add_argument("--page", type=int, default=0, help="Zero-based page number (default 0).")
    p.add_argument("--size", type=int, default=10, help="Results per page, 1-50 (default 10).")
    p.add_argument(
        "--include-deceased", action="store_true",
        help="Include profiles of deceased researchers (sends withTheDead=true).",
    )
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("semantic-search", help="Free-text / semantic profile search (GET semanticSearchData).")
    p.add_argument("--full-query", "--query", dest="full_query", required=True,
                    help="Search phrase (Polish or English), e.g. 'uczenie maszynowe', 'bioinformatics'.")
    p.add_argument(
        "--include-deceased", action="store_true",
        help="Include profiles marked as deceased.",
    )
    p.add_argument("--max-profiles", type=int, default=40,
                    help="Max profiles in the trimmed summary, 1-100 (default 40); the API may return more.")
    p.set_defaults(func=cmd_semantic_search)

    p = sub.add_parser("get", help="Fetch ORCID, degrees/titles, and keywords for one profile.")
    p.add_argument("--id", required=True, dest="id",
                    help="profileId from `search` or `semantic-search` results, e.g. jhMVc1vG5Yz.")
    p.set_defaults(func=cmd_get)

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
