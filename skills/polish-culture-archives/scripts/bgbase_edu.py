#!/usr/bin/env python3
"""EDUKATOR -- multi-discipline staff/doctoral-student publication
bibliography of the Pedagogical University of Krakow (Uniwersytet
Pedagogiczny im. Komisji Edukacji Narodowej w Krakowie), running an
Expertus/Splendor (ISIS-family) CGI system.

CONFIRMED live (2026-08-09): a GET request against
http://bgbase.up.krakow.pl/biblio/splendor/expertus3e.cgi with
KAT=/public/expertus/par/edu/, FST=data.fst, ekran=ISO, mask=1, I_XX=a,
F_00=02 (Autor), V_00=<surname> returned a real, correctly-formed "no
records match" response page (not an error) -- confirming the endpoint,
parameter names, and this field code are all correct, even though the site's
own HTML form submits via POST. Field codes for F_00/F_01/F_02 are taken
verbatim from the live search form's <select> options.

NOT YET CONFIRMED: the HTML shape of a page that actually has hits -- only
the "no records" response has been observed live. This tool always
includes the raw HTML plus a best-effort no-records flag; if a real query
returns hits and you want them parsed into structured fields, report the
HTML back so per-record markup can be added.

No JSON API -- HTML scraping of a legacy CGI system, encoded iso-8859-2 at
the source (request_text() auto-detects this from the response's
Content-Type header).
"""

from __future__ import annotations

import argparse

from _http import build_query, fail, print_result, request_text

BASE_URL = "http://bgbase.up.krakow.pl/biblio/splendor/expertus3e.cgi"

FIELD_CODES = {
    "author": "02",
    "author-unit": "03",
    "author-fulltext": "65",
    "title": "01",
    "title-words": "11",
    "source": "06",
    "source-words": "12",
    "series": "27",
    "series-words": "28",
    "language": "13",
    "pubtype-code": "07",
    "pubtype-name": "34",
    "journal-abbr": "26",
    "subject-heading": "10",
    "subject-heading-words": "41",
    "any-words": "99",
}

FORMATS = {"standard": "data.fdt", "short": "data01.fdt", "full": "data02.fdt"}


def cmd_search(args: argparse.Namespace) -> dict:
    params = {
        "KAT": "/public/expertus/par/edu/",
        "FST": "data.fst",
        "FDT": FORMATS[args.format],
        "ekran": "ISO",
        "mask": "1",
        "I_XX": "a",
        "cond": args.combine,
        "sort": args.sort,
        "F_00": FIELD_CODES[args.field1],
        "V_00": args.query1,
    }
    if args.field2 and args.query2:
        params["F_01"] = FIELD_CODES[args.field2]
        params["V_01"] = args.query2
    if args.field3 and args.query3:
        params["F_02"] = FIELD_CODES[args.field3]
        params["V_02"] = args.query3
    if args.page_size:
        params["R_0"] = str(args.page_size)

    url = build_query(BASE_URL, params)
    html = request_text(url)

    no_records = "norecords" in html or "nie odnaleziono" in html.lower()

    return {"url": url, "no_records": no_records, "html": html}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="EDUKATOR -- Uniwersytet Pedagogiczny w Krakowie staff publication bibliography (Expertus CGI)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search the EDUKATOR bibliography by up to 3 combined criteria.")
    s.add_argument("--query1", required=True, help="Search text for criterion 1.")
    s.add_argument("--field1", default="author", choices=sorted(FIELD_CODES), help="Field for criterion 1. Default: author.")
    s.add_argument("--query2", default=None, help="Search text for criterion 2 (optional).")
    s.add_argument("--field2", default=None, choices=sorted(FIELD_CODES), help="Field for criterion 2.")
    s.add_argument("--query3", default=None, help="Search text for criterion 3 (optional).")
    s.add_argument("--field3", default=None, choices=sorted(FIELD_CODES), help="Field for criterion 3.")
    s.add_argument("--combine", default="AND", choices=["AND", "OR", "NOT"], help="How to combine criteria 1-3. Default: AND.")
    s.add_argument(
        "--sort", default="-1",
        help="Sort order code from the site's own <select>, e.g. -1 (newest first), 1 (oldest first), '-1,2' (newest+title). Default: -1.",
    )
    s.add_argument("--format", default="standard", choices=sorted(FORMATS), help="Result detail level. Default: standard.")
    s.add_argument("--page-size", dest="page_size", type=int, default=None, help="Results per page (10/20/30/50/100). Omit for 'all'.")
    s.set_defaults(func=cmd_search)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
    except RuntimeError as e:
        fail(f"Error: {e}")
        return
    print_result(result)


if __name__ == "__main__":
    main()
