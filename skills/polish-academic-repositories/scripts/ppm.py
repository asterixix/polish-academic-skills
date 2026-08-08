#!/usr/bin/env python3
"""
PPM -- Polska Platforma Medyczna (Polish Platform of Medical Research), a
joint CRIS repository run by 7 Polish medical universities + 1 research
institute. Public OAI-PMH 2.0 API (OCLC OAICat implementation), no auth.

*** UNVERIFIED BASE URL: found via web search, not a live-tested response
    from this environment (outbound HTTPS to ppm.edu.pl is not reachable
    from this sandbox). https://ppm.edu.pl:7443/oaicat/ was reported as the
    OAI-PMH access point; the OCLC OAICat reference servlet is
    conventionally mapped at .../oaicat/OAIHandler. Run `identify` first --
    it is a single cheap harmless call -- and if it 404s, retry with
    OAI_BASE = "https://ppm.edu.pl:7443/oaicat/OAIHandler" (edit this file
    or pass a full URL override once confirmed working; report back which
    one worked so this can be fixed upstream). ***

This is metadata harvesting only -- OAI-PMH does not accept a free-text
query parameter. No REST/JSON search API has been confirmed public for PPM.

Subcommands:
  identify -- OAI Identify (cheap sanity check -- run this first).
  search   -- OAI ListRecords: slice by date range and/or OAI setSpec, paginated via resumption_token.
  get      -- OAI GetRecord for one object by full OAI identifier.

Source: https://ppm.edu.pl
"""

import argparse
import json
from urllib.parse import quote

import _http

OAI_BASE = "https://ppm.edu.pl:7443/oaicat/"

METADATA_FORMATS = ["oai_dc"]


def cmd_identify(_args: argparse.Namespace) -> dict:
    url = f"{OAI_BASE}?verb=Identify"
    xml = _http.fetch(url)
    return _http.parse_oai_pmh(xml, url)


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
    params = [("verb", "GetRecord"), ("metadataPrefix", args.metadata_format), ("identifier", args.id)]
    url = f"{OAI_BASE}?{_http.build_query(params)}"
    xml = _http.fetch(url)
    return _http.parse_oai_pmh(xml, url)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PPM -- Polska Platforma Medyczna, OAI-PMH harvesting API (unverified base URL, see module docstring)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    i = sub.add_parser("identify", help="OAI Identify -- cheap sanity check, run this first.")
    i.set_defaults(func=cmd_identify)

    s = sub.add_parser(
        "search",
        help="Harvest PPM metadata via OAI-PMH ListRecords by date range and/or setSpec.",
    )
    s.add_argument("--from-date", dest="from_date", help="Earliest datestamp boundary, YYYY-MM-DD.")
    s.add_argument("--until-date", dest="until_date", help="Latest datestamp boundary, YYYY-MM-DD.")
    s.add_argument("--set", help="OAI setSpec identifier. Omit for all sets. Run identify/ListSets to discover valid values.")
    s.add_argument("--metadata-format", choices=METADATA_FORMATS, default="oai_dc")
    s.add_argument("--resumption-token", help="Token from a previous response to fetch the next chunk.")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="Fetch a single PPM object via OAI-PMH GetRecord.")
    g.add_argument("--id", required=True, help="Full OAI identifier, from a prior search's 'identifier' field.")
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
