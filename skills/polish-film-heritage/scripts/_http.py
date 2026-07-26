"""Shared HTTP helper for the polish-film-heritage skill scripts.

Standard library only (urllib). Mirrors the network policy used by the
source TypeScript project's cache.ts:
  - Hard timeout of 30 seconds per attempt.
  - A single automatic retry, only for transient network errors (connection
    reset, DNS hiccups, timeouts) -- never for HTTP error responses.
  - HTTP 4xx and 5xx responses are never retried; they are raised
    immediately as a RuntimeError carrying the status code and a short
    (<=1024 char) body snippet for debugging.

All six sources in this skill (Ninateka, Gapla, Fototeka, FilmPolski,
Fototeka Śląska, Repozytorium FN) are fetched as plain GET requests --
either JSON (Ninateka) or HTML (the other five) -- so this helper only
needs a GET path plus JSON decoding for Ninateka.

Not a general-purpose library -- kept intentionally small and embedded in
this skill only, per the "no shared deps across skills" rule.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)"
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 2  # one initial try + one retry on transient network errors


def request(url: str, method: str = "GET", headers: dict | None = None,
            data: bytes | None = None, timeout: int = TIMEOUT_SECONDS):
    """Perform an HTTP request.

    Returns (status_code, body_bytes, response_headers_dict).

    Raises RuntimeError with a clear message on:
      - HTTP error status (4xx/5xx) -- includes status + short body snippet,
        never retried.
      - Network errors (after exhausting the single retry).
    """
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    last_network_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return resp.status, body, dict(resp.headers)
        except urllib.error.HTTPError as e:
            # HTTP 4xx/5xx: the upstream answered, so this is never retried.
            try:
                body_snippet = e.read().decode("utf-8", errors="replace")[:1024]
            except Exception:
                body_snippet = "[unable to read response body]"
            raise RuntimeError(
                f"HTTP {e.code} {e.reason} fetching {url}: {body_snippet}"
            ) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # Transient network-level failure (DNS, connection reset, timeout).
            last_network_error = e
            if attempt < MAX_ATTEMPTS:
                continue
            raise RuntimeError(f"Network error fetching {url}: {e}") from e

    # Defensive: the loop above always either returns or raises.
    raise RuntimeError(f"Network error fetching {url}: {last_network_error}")


def request_text(url: str, headers: dict | None = None, timeout: int = TIMEOUT_SECONDS) -> str:
    """GET a URL and decode the body as UTF-8 text (HTML pages)."""
    _status, body, _headers = request(url, method="GET", headers=headers, timeout=timeout)
    return body.decode("utf-8", errors="replace")


def request_json(url: str, headers: dict | None = None, timeout: int = TIMEOUT_SECONDS):
    """Like request(), but decodes the response body as JSON.

    Falls back to {"_raw": <text>} if the body is not valid JSON (some of
    these public endpoints occasionally answer with plain text or HTML on
    unexpected upstream errors).
    """
    _status, body, _headers = request(url, method="GET", headers=headers, timeout=timeout)
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


def build_query(base_url: str, params: dict) -> str:
    """Append a query string built from params, skipping None/empty values."""
    query = {k: v for k, v in params.items() if v is not None and v != ""}
    if not query:
        return base_url
    return f"{base_url}?{urllib.parse.urlencode(query)}"


def fail(message: str) -> None:
    """Print a clear error to stderr and exit(1)."""
    print(message, file=sys.stderr)
    sys.exit(1)


def print_result(result) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# HTML parsing helpers.
#
# The first two (decode_entities / strip_to_plain) are a direct line-by-line
# port of the identical decodeEntities()/stripToPlain() helpers duplicated in
# filmpolski.ts and fototekaslaska.ts -- same regex, same order of
# replacements, same semantics.
#
# The next three (extract_id_links / extract_title / extract_body_text) are
# NEW generic best-effort extractors used by gapla.py, fototeka.py, and
# fn_repozytorium.py. The upstream TS tools for those sources (gapla.ts,
# fototeka.ts, filmoteka-repo.ts) do NOT parse HTML at all -- they return the
# raw page verbatim as the MCP tool result. For a standalone skill that is
# too much raw markup to be useful, so these scripts add lightweight,
# conservative structural extraction on top. Because this sandbox blocks
# outbound HTTPS, none of this could be verified against a live fetch of
# gapla.fn.org.pl / fototeka.fn.org.pl / repozytorium.fn.org.pl -- see
# reference/API.md for the exact caveat per source. Each script always
# degrades gracefully (empty list / null fields) rather than raising if the
# expected structure isn't found, since a wrong guess about CSS classes on
# unverified sites is a real risk.
# ---------------------------------------------------------------------------


def decode_entities(s: str) -> str:
    """Decode the small, fixed set of HTML entities the TS source sites are
    known to emit (mirrors decodeEntities() in filmpolski.ts/fototekaslaska.ts).
    Not a full HTML5 entity table -- intentionally matches upstream scope."""
    s = re.sub(r"&nbsp;", " ", s, flags=re.IGNORECASE)
    s = s.replace("&#8211;", "–")
    s = s.replace("&#8217;", "'")
    s = s.replace("&amp;", "&")
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    return s


def strip_to_plain(html: str) -> str:
    """Strip HTML down to readable plain text (mirrors stripToPlain() in
    filmpolski.ts/fototekaslaska.ts): drop <script>/<style> bodies, turn <br>
    and block-closing tags into newlines, strip remaining tags, decode
    entities, collapse repeated whitespace/blank lines."""
    s = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    s = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)
    s = decode_entities(s)
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extract_id_links(html: str, path_fragment: str, base_url: str = "") -> list:
    """Generic best-effort tile extractor: find every anchor whose href
    contains `{path_fragment}/{numeric-id}` and return de-duplicated
    {id, url, title?, image_url?} rows (first non-empty title/image per id
    wins -- these gallery sites commonly wrap both an <img> link and a text
    link around the same detail page).

    Relative hrefs are resolved against base_url. Returns [] if nothing
    matches -- callers should treat that as "layout changed or no results",
    not necessarily an error.
    """
    pattern = re.compile(
        r'<a[^>]+href="([^"]*' + re.escape(path_fragment) + r'/(\d+)[^"]*)"[^>]*>([\s\S]*?)</a>',
        re.IGNORECASE,
    )
    by_id: dict = {}
    for m in pattern.finditer(html):
        href, item_id, inner = m.group(1), m.group(2), m.group(3)
        url = href
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = f"{base_url}{url if url.startswith('/') else '/' + url}"
        row = by_id.get(item_id)
        if row is None:
            row = {"id": int(item_id), "url": url}
            by_id[item_id] = row
        if not row.get("title"):
            title = re.sub(r"\s+", " ", strip_to_plain(inner)).strip()
            if title:
                row["title"] = title
        if not row.get("image_url"):
            img_m = re.search(r'<img[^>]+(?:data-src|src)="([^"]+)"', inner, re.IGNORECASE)
            if img_m:
                row["image_url"] = img_m.group(1)
    return list(by_id.values())


def extract_title(html: str) -> str | None:
    """Best-effort page title: first <h1>, falling back to <title>."""
    m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.IGNORECASE)
    if not m:
        m = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, re.IGNORECASE)
    if not m:
        return None
    text = re.sub(r"\s+", " ", strip_to_plain(m.group(1))).strip()
    return text or None


def extract_body_text(html: str, max_chars: int) -> tuple:
    """Best-effort stripped body text, capped at max_chars.

    Returns (text, truncated). Prefers the <body> region if present so
    <head>/<script> boilerplate doesn't dilute the result, but falls back to
    the whole document. This is a whole-page fallback -- it does not attempt
    to isolate a specific content region, since the exact per-site markup
    could not be verified live (see reference/API.md).
    """
    body_m = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.IGNORECASE)
    content = body_m.group(1) if body_m else html
    text = strip_to_plain(content)
    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True
    return text, truncated
