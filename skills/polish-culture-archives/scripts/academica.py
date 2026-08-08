#!/usr/bin/env python3
"""Academica -- Biblioteka Narodowa (National Library of Poland) digital
inter-library lending catalog, https://academica.edu.pl

CONFIRMED live (2026-08-09): a JSF (JavaServer Faces)/RichFaces 4.5.10
application. The homepage's inline search form is:
  <form id="simpleSearchForm" name="simpleSearchForm" method="post" action="/">
  input name="simpleSearchForm:j_idt117Input" (query text)
  input name="simpleSearchForm:simpleSearchButton" (submit, empty value)
  hidden input name="javax.faces.ViewState" (JSF postback token -- MUST be
  scraped fresh from the immediately preceding GET response and submitted
  back together with the JSESSIONID cookie from that same GET, or the
  server rejects the postback)

NOT YET CONFIRMED: the HTML/shape of an actual search-results response --
only the empty homepage has been observed live. RichFaces forms without an
explicit <a4j:.../f:ajax wrapper typically do a full-page postback (not a
partial ajax fragment), so a successful search is expected to render a
normal HTML page, but this has not been verified. This tool performs the
real two-step JSF flow (GET to capture ViewState + session cookie, then
POST the search) and returns whatever HTML comes back, plus a best-effort
generic link scrape. Report back a real result page if you want structured
per-record parsing added.

Publicly viewable metadata only (catalog search, bibliographic records) --
full text of copyright-protected works requires a library-terminal login
per academica.edu.pl's own terms; this tool never attempts that.

Uses its own small cookie-jar session helper rather than a shared _http.py
(this is the only source in this skill needing multi-request session
state), so it does not get the shared module's automatic retry-once policy.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)"
TIMEOUT = 30
SITE = "https://academica.edu.pl"

VIEWSTATE_RE = re.compile(r'name="javax\.faces\.ViewState"\s+value="([^"]*)"')


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = "".join(self._text).strip()
            if text:
                self.links.append({"href": self._href, "text": text})
            self._href = None
            self._text = []


def _session():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _get(opener, url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _post(opener, url: str, form: list[tuple[str, str]]) -> str:
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener.open(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def cmd_search(args: argparse.Namespace) -> dict:
    opener = _session()
    home_html = _get(opener, f"{SITE}/")
    m = VIEWSTATE_RE.search(home_html)
    if not m:
        raise RuntimeError(
            "Could not find javax.faces.ViewState on the Academica homepage -- the page layout may have changed."
        )
    view_state = m.group(1)

    form = [
        ("simpleSearchForm", "simpleSearchForm"),
        ("simpleSearchForm:j_idt117Input", args.query),
        ("simpleSearchForm:simpleSearchButton", ""),
        ("javax.faces.ViewState", view_state),
    ]
    result_html = _post(opener, f"{SITE}/", form)

    collector = _LinkCollector()
    collector.feed(result_html)

    return {
        "url": f"{SITE}/",
        "query": args.query,
        "links": collector.links,
        "html": result_html,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Academica -- Biblioteka Narodowa digital inter-library lending catalog search (JSF postback)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search the Academica catalog via the homepage's simple search form.")
    s.add_argument("--query", required=True, help="Search phrase.")
    s.set_defaults(func=cmd_search)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
