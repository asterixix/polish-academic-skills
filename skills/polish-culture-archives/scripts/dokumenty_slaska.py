#!/usr/bin/env python3
"""Dokumenty Slaska -- https://www.dokumentyslaska.pl/

Edycja Wieslawa Dlugosza: medieval Silesian documents, regesty, heraldry,
iconographic materials.

No public REST API and no full-text search: this is a static HTML site
(frames-based navigation) with `indeks *.html` (tables of contents) and
`dokument *.html` (content) files, plus assorted subdirectories. Pretending
to offer whole-domain "search" without an external index would be
misleading, so this script only exposes safe single-page fetches plus a
fixed navigation list for the main medieval document series.

Subcommands mirror the original MCP tools:
  get-page          -> fetch one HTML/text resource by a validated relative path
  medieval-catalog  -> fixed JSON list of paths for the main pre-1333 document series
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse

from _http import fail, print_result, request_text

SITE_ORIGIN = "https://www.dokumentyslaska.pl"

HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    "Accept-Language": "pl,de;q=0.8,en;q=0.6",
}

# Main "Dokumenty" series from the homepage menu (relative paths on the site).
MEDIEVAL_CATALOG = [
    {"label": "Do 1200 roku", "indeks": "indeks 1200.html", "dokument": "dokument 1200.html"},
    {"label": "1201-1230", "indeks": "indeks 1201-1230.html", "dokument": "dokument 1201-1230.html"},
    {"label": "1231-1250", "indeks": "indeks 1231-1250.html", "dokument": "dokument 1231-1250.html"},
    {"label": "1251-1266", "indeks": "indeks 1251-1266.html", "dokument": "dokument 1251-1266.html"},
    {"label": "1267-1281", "indeks": "indeks 1267-1281.html", "dokument": "dokument 1267-1281.html"},
    {"label": "1282-1290", "indeks": "indeks 1282-1290.html", "dokument": "dokument 1282-1290.html"},
    {"label": "1291-1300", "indeks": "indeks 1291-1300.html", "dokument": "dokument 1291-1300.html"},
    {"label": "1301-1315", "indeks": "indeks 1301-1315.html", "dokument": "dokument 1301-1315.html"},
    {"label": "1316-1326", "indeks": "indeks 1316-1326.html", "dokument": "dokument 1316-1326.html"},
    {"label": "1327-1333", "indeks": "indeks 1327-1333.html", "dokument": "dokument 1327-1333.html"},
]

_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def _decode_uri_component_strict(s: str) -> str:
    """Mimic JS decodeURIComponent()'s strictness: raise on malformed
    percent-escapes or invalid UTF-8 byte sequences, instead of silently
    passing them through the way urllib.parse.unquote does by default."""
    if _PERCENT_RE.search(s):
        raise ValueError("malformed percent-escape sequence")
    return urllib.parse.unquote(s, encoding="utf-8", errors="strict")


def to_safe_site_url(rel_path: str) -> str:
    """Port of the TypeScript `toSafeSiteUrl`: builds a URL under
    dokumentyslaska.pl from a relative path only, segment by segment,
    rejecting absolute URLs, protocol-relative paths, `..` traversal, and
    empty/`.`/`..` segments. Raises ValueError on any violation."""
    t = rel_path.strip()
    t = t.lstrip("/")
    if not t or len(t) > 512:
        raise ValueError("path must be non-empty and at most 512 characters")
    if re.match(r"^https?://", t, re.IGNORECASE) or t.startswith("//"):
        raise ValueError("only relative paths under the site are allowed")
    if ".." in t:
        raise ValueError("path must not contain ..")

    parts = t.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise ValueError("invalid path segment")

    encoded_parts = []
    for seg in parts:
        try:
            decoded = _decode_uri_component_strict(seg)
            encoded_parts.append(urllib.parse.quote(decoded, safe=""))
        except Exception:
            encoded_parts.append(urllib.parse.quote(seg, safe=""))
    encoded = "/".join(encoded_parts)
    return f"{SITE_ORIGIN}/{encoded}"


def cmd_get_page(args: argparse.Namespace) -> None:
    try:
        url = to_safe_site_url(args.path)
    except ValueError as e:
        fail(f"Error calling dokumenty_slaska_get_page: {e}")
        return
    try:
        html = request_text(url, headers=HTML_HEADERS, default_encoding="iso-8859-2")
    except RuntimeError as e:
        fail(f"Error calling dokumenty_slaska_get_page: {e}")
        return
    print_result({"path": args.path, "url": url, "html": html})


def cmd_medieval_catalog(args: argparse.Namespace) -> None:
    print_result({"site": SITE_ORIGIN, "periods": MEDIEVAL_CATALOG})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dokumenty_slaska.py",
        description=(
            "Dokumenty Slaska (dokumentyslaska.pl) -- static site of medieval Silesian "
            "documents, regesty, heraldry, iconography. No API, no full-text search."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    pg = sub.add_parser("get-page", help="Fetch a single page by relative path (validated, no traversal).")
    pg.add_argument("--path", required=True, help='Relative path from the site root, e.g. "indeks 1200.html", "dokument 1201-1230.html", "bibliografia.html", "kamenz/index.html". Spaces are allowed.')
    pg.set_defaults(func=cmd_get_page)

    pc = sub.add_parser("medieval-catalog", help="Fixed JSON list of paths for the main pre-1333 document series (navigation aid, not a search).")
    pc.set_defaults(func=cmd_medieval_catalog)

    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
