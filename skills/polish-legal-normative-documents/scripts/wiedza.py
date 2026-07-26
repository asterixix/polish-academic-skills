#!/usr/bin/env python3
"""WIEDZA (wiedza.pkn.pl) -- PKN's Polish Standards (PN) search portal.

Backend is Liferay 6.1. There is no public JSON API; the search form is a
Liferay portlet that needs a session cookie plus a `p_auth` CSRF-style token
scraped out of the landing page HTML, then a POST (search) or GET (detail)
against the portlet's resource URL. This is unrelated to pkn_search
(pkn.py), which searches the general pkn.pl Drupal site instead.

IMPORTANT -- session, not cache: every call here does a fresh landing-page
GET to mint a new session + token before the real request. The original MCP
tool explicitly does NOT cache these responses (the token/session is only
valid briefly and is tied to a specific Liferay session cookie), and this
standalone script has no cache layer to speak of anyway -- treat every
invocation as doing 2 HTTP round-trips.

Subcommands (mirroring the original MCP tools):
  search-norms  (wiedza_search_norms) -- POST search (HTML result list)
  get-standard  (wiedza_get_standard) -- GET one standard's detail page (HTML)

Standard library only (http.cookiejar + urllib for the session; see
_http.py for the shared cookie-opener helper and retry/timeout policy).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from typing import Any, Dict, Optional

from _http import build_cookie_opener, fetch_text

WIEDZA_ORIGIN = "https://wiedza.pkn.pl"
PREFIX = "_searchstandards_WAR_p4scustomerpknzwnelsearchstandardsportlet"
PORTLET_ID = "searchstandards_WAR_p4scustomerpknzwnelsearchstandardsportlet"

LANDING = {
    "pl": "/web/guest/wyszukiwarka-norm",
    "en": "/en/wyszukiwarka-norm",
    "ru": "/ru/wyszukiwarka-norm",
}

_AUTH_TOKEN_RE = re.compile(r"Liferay\.authToken = '([^']+)'")


def _form_date_re() -> "re.Pattern[str]":
    escaped = re.escape(PREFIX)
    return re.compile(rf'name="{escaped}_formDate" type="hidden" value="(\d+)"')


def parse_auth_token(html: str) -> Optional[str]:
    """Mirrors parseAuthToken() in src/tools/wiedza.ts exactly."""
    m = _AUTH_TOKEN_RE.search(html)
    return m.group(1) if m else None


def parse_form_date(html: str) -> Optional[str]:
    """Mirrors parseFormDate() in src/tools/wiedza.ts exactly."""
    m = _form_date_re().search(html)
    return m.group(1) if m else None


def fetch_landing_session(locale: str, opener) -> Dict[str, str]:
    """GET the search landing page to mint a session cookie (via `opener`'s
    cookie jar) and scrape the Liferay auth token out of the HTML.

    Raises RuntimeError if no cookies were set, or the token is missing --
    matching the two explicit checks in wiedza.ts's registerWiedzaTools.
    """
    landing_path = LANDING[locale]
    url = f"{WIEDZA_ORIGIN}{landing_path}"
    html = fetch_text(url, method="GET", headers={"Accept": "text/html"}, opener=opener)
    return {"html": html, "landing_path": landing_path}


def build_search_body(form_date: str, p: Dict[str, Any]) -> bytes:
    """Mirrors buildSearchBody() in src/tools/wiedza.ts."""
    fields = [
        (f"{PREFIX}_formDate", form_date),
        ("hiddenInputStandardNumber", p.get("standard_number") or ""),
        (f"{PREFIX}_standardNumber", p.get("standard_number") or ""),
        ("searchType", "2" if p.get("title_match") == "phrase" else "1"),
        (f"{PREFIX}_standardIcs", p.get("ics") or ""),
        (f"{PREFIX}_standardTitle", p.get("title") or ""),
        (f"{PREFIX}_standardTitleEnglish", p.get("title_english") or ""),
        (f"{PREFIX}_standardContent", p.get("content") or ""),
        (f"{PREFIX}_startDate", p.get("publish_from") or ""),
        (f"{PREFIX}_endDate", p.get("publish_to") or ""),
        (f"{PREFIX}_withdrawalStartDate", p.get("withdrawal_from") or ""),
        (f"{PREFIX}_withdrawalEndDate", p.get("withdrawal_to") or ""),
        (f"{PREFIX}_standardDirectiveNumber", p.get("directive") or ""),
        (f"{PREFIX}_standardIntroducted", p.get("introduction") or ""),
        (f"{PREFIX}_standardKt", p.get("technical_committee") or ""),
        (f"{PREFIX}_standardSector", p.get("sector") or ""),
        (f"{PREFIX}_standardLanguage", p.get("language", "ALL")),
        (f"{PREFIX}_standardActual", p.get("status", "all")),
        (f"{PREFIX}_standardRowsOnPage", p.get("rows_on_page", "50")),
    ]
    return urllib.parse.urlencode(fields).encode("utf-8")


def post_search_url(token: str) -> str:
    q = {
        "p_auth": token,
        "p_p_id": PORTLET_ID,
        "p_p_lifecycle": "1",
        "p_p_state": "normal",
        "p_p_mode": "view",
        "p_p_col_id": "column-1",
        "p_p_col_pos": "1",
        "p_p_col_count": "2",
        f"{PREFIX}_javax.portlet.action": "searchStandardsAction",
    }
    return f"{WIEDZA_ORIGIN}/wyszukiwarka-norm?{urllib.parse.urlencode(q)}"


def get_standard_url(token: str, standard_number: str) -> str:
    q = {
        "p_auth": token,
        "p_p_id": PORTLET_ID,
        "p_p_lifecycle": "1",
        "p_p_state": "normal",
        "p_p_mode": "view",
        "p_p_col_id": "column-1",
        "p_p_col_pos": "1",
        "p_p_col_count": "2",
        f"{PREFIX}_standardNumber": standard_number,
        f"{PREFIX}_javax.portlet.action": "showStandardDetailsAction",
    }
    return f"{WIEDZA_ORIGIN}/wyszukiwarka-norm?{urllib.parse.urlencode(q)}"


_TEXT_FIELDS = [
    "standard_number", "title", "title_english", "content", "ics", "sector",
    "technical_committee", "directive", "introduction",
]
_DATE_FIELDS = ["publish_from", "publish_to", "withdrawal_from", "withdrawal_to"]


def _validate_search_args(args: argparse.Namespace) -> None:
    has_text = any((getattr(args, f) or "").strip() for f in _TEXT_FIELDS)
    has_date = any((getattr(args, f) or "").strip() for f in _DATE_FIELDS)
    if not (has_text or has_date):
        raise RuntimeError(
            "Provide at least one criterion: number/title/content/ICS/sector/"
            "technical-committee/directive/introduction, or a date range."
        )


def cmd_search_norms(args: argparse.Namespace) -> Any:
    _validate_search_args(args)

    opener, jar = build_cookie_opener()
    session = fetch_landing_session(args.locale, opener)
    if len(list(jar)) == 0:
        raise RuntimeError(
            "Server did not return session cookies (Set-Cookie) -- Liferay search will not work."
        )
    token = parse_auth_token(session["html"])
    form_date = parse_form_date(session["html"])
    if not token or not form_date:
        raise RuntimeError("Could not find the Liferay auth token or formDate in the search page HTML.")

    body = build_search_body(form_date, vars(args))
    post_url = post_search_url(token)
    referer = f"{WIEDZA_ORIGIN}{session['landing_path']}"
    html = fetch_text(
        post_url,
        method="POST",
        data=body,
        headers={
            "Accept": "text/html",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": referer,
        },
        opener=opener,
    )
    return {"url": post_url, "html": html}


def cmd_get_standard(args: argparse.Namespace) -> Any:
    opener, jar = build_cookie_opener()
    session = fetch_landing_session(args.locale, opener)
    if len(list(jar)) == 0:
        raise RuntimeError("Server did not return session cookies (Set-Cookie).")
    token = parse_auth_token(session["html"])
    if not token:
        raise RuntimeError("Could not find the Liferay auth token in the search page HTML.")

    url = get_standard_url(token, args.standard_number)
    referer = f"{WIEDZA_ORIGIN}{session['landing_path']}"
    html = fetch_text(
        url,
        method="GET",
        headers={"Accept": "text/html", "Referer": referer},
        opener=opener,
    )
    return {"url": url, "html": html}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wiedza.py",
        description=(
            "Search and fetch Polish Standards (PN) metadata from the WIEDZA-PKN "
            "portal (wiedza.pkn.pl). Session-based Liferay portlet -- not cached."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_search = subparsers.add_parser(
        "search-norms", help="Search the WIEDZA norms catalog (wiedza_search_norms)."
    )
    p_search.add_argument("--locale", default="pl", choices=["pl", "en", "ru"],
                           help="Search page language / Liferay path.")
    p_search.add_argument("--standard-number", default=None, dest="standard_number",
                           help='e.g. "PN-EN ISO 9001".')
    p_search.add_argument("--title", default=None, help="Standard title (Polish).")
    p_search.add_argument("--title-english", default=None, dest="title_english", help="Title in English.")
    p_search.add_argument("--content", default=None, help="Search within standard content.")
    p_search.add_argument("--ics", default=None, help="ICS classification code.")
    p_search.add_argument("--sector", default=None, help="Standardization sector id.")
    p_search.add_argument("--technical-committee", default=None, dest="technical_committee",
                           help="PKN technical committee id, e.g. PKN/KT 40.")
    p_search.add_argument("--directive", default=None, help="EU directive number, e.g. 2009/48/EC.")
    p_search.add_argument("--introduction", default=None, help="Introducing standard, e.g. EN ISO 9001.")
    p_search.add_argument("--publish-from", default=None, dest="publish_from", help="YYYY-MM-DD.")
    p_search.add_argument("--publish-to", default=None, dest="publish_to", help="YYYY-MM-DD.")
    p_search.add_argument("--withdrawal-from", default=None, dest="withdrawal_from", help="YYYY-MM-DD.")
    p_search.add_argument("--withdrawal-to", default=None, dest="withdrawal_to", help="YYYY-MM-DD.")
    p_search.add_argument(
        "--title-match", default="words", dest="title_match", choices=["words", "phrase"],
        help="words=match any word (default), phrase=exact phrase.",
    )
    p_search.add_argument(
        "--language", default="ALL", choices=["ALL", "P", "E", "D", "F"],
        help="Standard language version: ALL, P=Polish, E=English, D=German, F=French.",
    )
    p_search.add_argument(
        "--status", default="all", choices=["all", "standard-actual", "standard-withdrawal"],
        help="all (default), standard-actual, or standard-withdrawal.",
    )
    p_search.add_argument(
        "--rows-on-page", default="50", dest="rows_on_page", choices=["20", "30", "50", "75"],
        help="Result rows per page. Default 50.",
    )
    p_search.set_defaults(func=cmd_search_norms)

    p_get = subparsers.add_parser(
        "get-standard", help="Fetch one standard's detail page by exact number (wiedza_get_standard)."
    )
    p_get.add_argument(
        "--number", "--standard-number", dest="standard_number", required=True,
        help='Exact standard number from a search result, e.g. "PN-EN ISO 9001:2015-10F".',
    )
    p_get.add_argument("--locale", default="pl", choices=["pl", "en", "ru"],
                        help="Referer page language (session from the same path as search).")
    p_get.set_defaults(func=cmd_get_standard)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        result = args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
