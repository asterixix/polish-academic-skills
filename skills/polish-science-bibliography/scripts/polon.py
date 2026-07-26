#!/usr/bin/env python3
"""POL-on public registry data via the RAD-on Open Data API (no API key).

Base:    https://radon.nauka.gov.pl/opendata/polon
Catalog: https://radon.nauka.gov.pl/pomoc/knowledge-base/katalog-udostepnianych-danych-api/

Same open data as polon.nauka.gov.pl / radon.nauka.gov.pl/dane.
Returns raw JSON: results[], pagination.maxCount, pagination.token
(pass pagination.token back in as --page-token for the next page).

Subcommand mirrors the original MCP tool:
  search  -> GET /opendata/polon/{resource}?resultNumbers=...&token=...&<filters>
"""

from __future__ import annotations

import argparse
import json
import sys

from _http import build_query, fail, print_result, request

API_BASE = "https://radon.nauka.gov.pl/opendata/polon"
JSON_HEADERS = {"Accept": "application/json"}

RESOURCE_SEGMENTS = {
    "institutions": "institutions",
    "employees": "employees",
    "projects": "projects",
    "publications": "publications",
    "courses": "courses",
    "branches": "branches",
}


def build_polon_url(resource: str, args: argparse.Namespace) -> str:
    segment = RESOURCE_SEGMENTS[resource]
    params = {
        "resultNumbers": args.result_numbers,
        "token": args.page_token,
    }

    if resource == "institutions":
        params["city"] = args.city
        params["voivodeship"] = args.voivodeship
        params["name"] = args.institution_name
    elif resource == "branches":
        params["city"] = args.city
        params["voivodeship"] = args.voivodeship
    elif resource == "employees":
        params["firstName"] = args.first_name
        params["lastName"] = args.last_name
        params["disciplineName"] = args.discipline_name
    elif resource == "projects":
        params["projectTitlePl"] = args.project_title_pl
        params["projectTitleEn"] = args.project_title_en
        params["projectNumber"] = args.project_number
        params["keywords"] = args.keywords
    elif resource == "publications":
        params["title"] = args.publication_title
        params["lastName"] = args.last_name
    elif resource == "courses":
        params["courseName"] = args.course_name

    return build_query(f"{API_BASE}/{segment}", params)


def cmd_search(args: argparse.Namespace) -> None:
    url = build_polon_url(args.resource, args)
    try:
        _status, body, _h = request(url, method="GET", headers=JSON_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling polon_search: {e}")
        return
    print_result(json.loads(body.decode("utf-8")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polon.py",
        description="POL-on / RAD-on Open Data API client (no API key required).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="Query one of the POL-on open datasets.")
    p.add_argument(
        "--resource",
        required=True,
        choices=["institutions", "employees", "projects", "publications", "courses", "branches"],
        help="POL-on dataset to query.",
    )
    p.add_argument(
        "--result-numbers", type=int, default=20,
        help="Page size (resultNumbers), 1-100 (default 20).",
    )
    p.add_argument(
        "--page-token", help="Pagination token from a previous response's pagination.token field.",
    )
    p.add_argument("--city", help="Filter: city -- institutions or branches only.")
    p.add_argument("--voivodeship", help="Filter: Polish voivodeship name -- institutions or branches only.")
    p.add_argument("--institution-name", help="Filter: institution name fragment -- institutions only.")
    p.add_argument("--first-name", help="Filter: employee first name -- employees only.")
    p.add_argument(
        "--last-name",
        help="Filter: last name -- employees (with first-name) or publications (author surname).",
    )
    p.add_argument("--discipline-name", help="Filter: scientific discipline name -- employees only (e.g. astronomia).")
    p.add_argument("--project-title-pl", help="Filter: Polish project title -- projects only.")
    p.add_argument("--project-title-en", help="Filter: English project title -- projects only.")
    p.add_argument("--project-number", help="Filter: grant/project number -- projects only.")
    p.add_argument("--keywords", help="Filter: project keywords -- projects only.")
    p.add_argument("--publication-title", help="Filter: publication title fragment -- publications only.")
    p.add_argument("--course-name", help="Filter: field-of-study name -- courses only.")
    p.set_defaults(func=cmd_search)

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
