#!/usr/bin/env python3
"""
Depot CeON -- Repozytorium Centrum Otwartej Nauki (CeON Repository), ICM
University of Warsaw. DSpace-based, public OAI-PMH 2.0 API, no auth.

This is metadata harvesting (not the portal's interactive full-text search
UI at https://depot.ceon.pl/) -- OAI-PMH does not accept a free-text query
parameter. No DSpace REST API (`/server/api`) has been confirmed publicly
documented for this installation, unlike RUJ/AGH/AMU/UAFM/ICM in this same
skill -- only OAI-PMH is supported here.

Covers journal articles, books, chapters, theses/dissertations, conference
materials, and reports shared by Polish researchers across all fields.

Subcommands (mirrors rcin.py's shape):
  search -- OAI ListRecords: slice by date range and/or OAI setSpec, paginated via resumption_token.
  get    -- OAI GetRecord for one object by OAI identifier or numeric handle suffix.

Source: https://depot.ceon.pl
"""

import argparse
import json
import re
from urllib.parse import quote

import _http

OAI_BASE = "https://depot.ceon.pl/oai/request"

METADATA_FORMATS = ["oai_dc"]


def normalize_identifier(record_id: str) -> str:
    t = record_id.strip()
    if re.match(r"^oai:", t, re.IGNORECASE):
        return t
    if re.match(r"^\d+/\d+$", t):
        return f"oai:depot.ceon.pl:{t}"
    return t


def cmd_search(args: argparse.Namespace) -> dict:
    if args.resumption_token:
        url = f"{OAI_BASE}?verb=ListRecords&resumptionToken={quote(args.resumption_token, safe='')}"
    else:
        params = [("verb", "ListRecords"), ("metadataPrefix", args.metadata_format)]
        if args.from_date:
            params.append(("from", args.from_date))
        if args.until_date:
            params.append(("until", args.until_date))
        if args.set:
            params.append(("set", args.set))
        url = f"{OAI_BASE}?{_http.build_query(params)}"

    xml = _http.fetch(url)
    return _http.parse_oai_pmh(xml, url)


def cmd_get(args: argparse.Namespace) -> dict:
    identifier = normalize_identifier(args.id)
    params = [("verb", "GetRecord"), ("metadataPrefix", args.metadata_format), ("identifier", identifier)]
    url = f"{OAI_BASE}?{_http.build_query(params)}"
    xml = _http.fetch(url)
    return _http.parse_oai_pmh(xml, url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Depot CeON -- Repozytorium Centrum Otwartej Nauki, OAI-PMH harvesting API."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser(
        "search",
        help="Harvest Depot CeON metadata via OAI-PMH ListRecords by date range and/or setSpec.",
    )
    s.add_argument("--from-date", dest="from_date", help="Earliest datestamp boundary, YYYY-MM-DD.")
    s.add_argument("--until-date", dest="until_date", help="Latest datestamp boundary, YYYY-MM-DD.")
    s.add_argument("--set", help="OAI setSpec identifier, e.g. col_123456789_58. Omit for all sets.")
    s.add_argument("--metadata-format", choices=METADATA_FORMATS, default="oai_dc")
    s.add_argument("--resumption-token", help="Token from a previous response to fetch the next chunk.")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="Fetch a single Depot CeON object via OAI-PMH GetRecord.")
    g.add_argument(
        "--id",
        required=True,
        help="Handle suffix (e.g. 123456789/12345) or full OAI identifier, e.g. oai:depot.ceon.pl:123456789/12345.",
    )
    g.add_argument("--metadata-format", choices=METADATA_FORMATS, default="oai_dc")
    g.set_defaults(func=cmd_get)

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
