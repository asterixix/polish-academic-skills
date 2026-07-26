#!/usr/bin/env python3
"""Katalog Biblioteki Slaskiego Uniwersytetu Medycznego (SUM) -- Aleph / Ex Libris.

OPAC: https://katalog.sum.edu.pl/

Public machine interface: Aleph X-Server at `/X` (XML responses). See the
Ex Libris docs: https://developers.exlibrisgroup.com/aleph/apis/aleph-x-services/

*** KNOWN UPSTREAM LIMITATION: as observed 2026-03, `op=find` on this
    installation answers with `<error>SRU gate configuration file is
    missing.</error>` -- the library's SRU gateway is not configured
    server-side, so full-text/CCL search via X-Services may not work until
    the library fixes it. This is not a bug in this script. `op=present`
    (fetching MARC/XML for a known set_no/set_entry) has worked in tests. ***

Subcommands mirror the original MCP tools:
  find     -> op=find    (request uses Aleph WWW index prefixes: wrd=, wti=, wau=, ...)
  present  -> op=present (fetch MARC/XML for set_no/set_entry from a find result set)
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from _http import fail, print_result, request_text

CATALOG_ORIGIN = "https://katalog.sum.edu.pl"
X_URL = f"{CATALOG_ORIGIN}/X"

XML_HEADERS = {"Accept": "application/xml, text/xml;q=0.9, */*;q=0.8"}

SRU_GATE_MARKERS = ("sru gate", "sru-gate", "bramki sru", "bramka sru")


def _elem_to_obj(elem: ET.Element):
    """Recursively convert an ElementTree Element into a plain JSON-friendly
    structure: {"@attrib": ..., "#text": "...", "child_tag": <obj or [obj,...]>}.
    Kept intentionally simple/generic since Aleph X-Server response shapes
    vary by installation and operation.
    """
    obj: dict = {}
    if elem.attrib:
        obj["@attrib"] = dict(elem.attrib)
    text = (elem.text or "").strip()
    children = list(elem)
    if not children:
        if text:
            if obj:
                obj["#text"] = text
                return obj
            return text
        return obj if obj else None
    for child in children:
        child_obj = _elem_to_obj(child)
        if child.tag in obj:
            existing = obj[child.tag]
            if isinstance(existing, list):
                existing.append(child_obj)
            else:
                obj[child.tag] = [existing, child_obj]
        else:
            obj[child.tag] = child_obj
    if text:
        obj["#text"] = text
    return obj


def _find_error_text(root: ET.Element) -> str | None:
    for err in root.iter("error"):
        if err.text and err.text.strip():
            return err.text.strip()
    return None


def _parse_aleph_xml(raw_xml: str, url: str) -> dict:
    result: dict = {"url": url, "raw_xml": raw_xml}
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError as e:
        result["parse_error"] = f"Response was not well-formed XML: {e}"
        return result

    result["root_tag"] = root.tag
    result["parsed"] = {root.tag: _elem_to_obj(root)}

    error_text = _find_error_text(root)
    if error_text:
        result["error"] = error_text
        if any(marker in error_text.lower() for marker in SRU_GATE_MARKERS):
            result["known_upstream_limitation"] = (
                "The Aleph X-Server SRU gate is not configured on this installation "
                "(katalog.sum.edu.pl). This is a server-side configuration issue at "
                "the library, not a bug in this script -- op=find cannot work until "
                "it is fixed. Try sum_aleph.py present if you already have a "
                "set_no/set_entry."
            )
    return result


def cmd_find(args: argparse.Namespace) -> None:
    params = {"op": "find", "base": args.base, "request": args.request}
    url = f"{X_URL}?{urllib.parse.urlencode(params)}"
    try:
        raw_xml = request_text(url, headers=XML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling sum_aleph_find: {e}")
        return
    print_result(_parse_aleph_xml(raw_xml, url))


def cmd_present(args: argparse.Namespace) -> None:
    params = {
        "op": "present",
        "set_no": args.set_no,
        "set_entry": args.set_entry,
        "format": args.format,
    }
    url = f"{X_URL}?{urllib.parse.urlencode(params)}"
    try:
        raw_xml = request_text(url, headers=XML_HEADERS)
    except RuntimeError as e:
        fail(f"Error calling sum_aleph_present: {e}")
        return
    print_result(_parse_aleph_xml(raw_xml, url))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sum_aleph.py",
        description=(
            "Katalog Biblioteki SUM (katalog.sum.edu.pl) -- Aleph X-Services XML interface. "
            "NOTE: op=find may be broken server-side (missing SRU gate configuration)."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    pf = sub.add_parser("find", help="Search via Aleph X-Server op=find (WWW index prefixes).")
    pf.add_argument("--base", default="SUM01", help="Aleph bibliographic base code. Default SUM01.")
    pf.add_argument("--request", required=True, help="Find query in WWW prefix syntax, e.g. 'wrd=kardiologia' or 'wti=anestezjologia' or 'wau=nowak'.")
    pf.set_defaults(func=cmd_find)

    pp = sub.add_parser("present", help="Fetch record(s) via Aleph X-Server op=present.")
    pp.add_argument("--set-no", required=True, help="Result set number returned by find, e.g. 000001.")
    pp.add_argument("--set-entry", required=True, help="Entry index or range within the set, e.g. 000000001 or 000000001,000000005.")
    pp.add_argument("--format", default="marc", help="Presentation format for this installation. Default marc.")
    pp.set_defaults(func=cmd_present)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
