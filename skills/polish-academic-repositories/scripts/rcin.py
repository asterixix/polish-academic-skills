#!/usr/bin/env python3
"""
RCIN -- Repozytorium Cyfrowe Instytutow Naukowych (Digital Repository of
Scientific Institutes). Public OAI-PMH 2.0 API, no authentication required.

This is metadata harvesting (not the portal's interactive full-text search
UI at https://rcin.org.pl/dlibra/) -- OAI-PMH does not accept a free-text
query parameter.

Subcommands (ported from rcin_search / rcin_get_record):
  search -- OAI ListRecords: slice by date range and/or OAI setSpec, paginated via resumption_token.
  get    -- OAI GetRecord for one object by OAI identifier or numeric id.

Source: https://rcin.org.pl
"""

import argparse
import json
import re
from urllib.parse import quote

import _http

OAI_BASE = "https://rcin.org.pl/oai-pmh-repository.xml"

METADATA_FORMATS = ["oai_dc", "oai_qdc", "mets", "oai_etdms", "dlibra_avs"]


def normalize_identifier(record_id: str) -> str:
    t = record_id.strip()
    if re.match(r"^oai:", t, re.IGNORECASE):
        return t
    if re.match(r"^\d+$", t):
        return f"oai:rcin.org.pl:{t}"
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
        description="RCIN -- Repozytorium Cyfrowe Instytutow Naukowych, OAI-PMH harvesting API."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser(
        "search",
        help="Harvest RCIN metadata via OAI-PMH ListRecords by date range and/or setSpec.",
    )
    s.add_argument("--from-date", dest="from_date", help="Earliest datestamp boundary, YYYY-MM-DD.")
    s.add_argument("--until-date", dest="until_date", help="Latest datestamp boundary, YYYY-MM-DD.")
    s.add_argument("--set", help="OAI setSpec identifier, e.g. rcin.org.pl:literature. Omit for all sets.")
    s.add_argument("--metadata-format", choices=METADATA_FORMATS, default="oai_dc")
    s.add_argument("--resumption-token", help="Token from a previous response to fetch the next chunk.")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="Fetch a single RCIN object via OAI-PMH GetRecord.")
    g.add_argument(
        "--id",
        required=True,
        help="Numeric content id or full OAI identifier, e.g. 204728 or oai:rcin.org.pl:204728.",
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
