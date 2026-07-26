"""Shared HTTP helper for the polish-legal-normative-documents skill scripts.

Standard-library only (urllib, http.cookiejar). No third-party dependencies.

Network policy (mirrors the source MCP server's src/cache.ts):
  - 30 second hard timeout per request.
  - A single automatic retry on transient network errors only
    (connection resets/refused, unreachable network, timeouts, generic
    URLError caused by an underlying OSError). HTTP 4xx/5xx responses are
    NEVER retried.
  - On failure, raise a RuntimeError with a clear message including the
    HTTP status (if any) and a short snippet of the response body.

A few sources in this skill (WIEDZA / wiedza.pkn.pl) need a stateful
session: an initial GET to pick up Liferay session cookies, followed by a
POST that carries those cookies plus a CSRF-ish `p_auth` token scraped out
of the landing page HTML. `build_cookie_opener()` below wires up a
`http.cookiejar.CookieJar` + `HTTPCookieProcessor` opener for exactly that
case -- still 100% standard library.
"""

from __future__ import annotations

import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

USER_AGENT = (
    "polish-academic-skills/1.0 "
    "(+https://github.com/asterixix/polish-academic-skills)"
)

TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 2

# Errno-style transient network error indicators we consider safe to retry.
_TRANSIENT_MARKERS = (
    "timed out",
    "timeout",
    "connection reset",
    "connection refused",
    "network is unreachable",
    "temporary failure",
    "econnreset",
    "econnrefused",
    "enetunreach",
    "etimedout",
)


def _is_transient(err: BaseException) -> bool:
    """Best-effort classification of transient vs. permanent network errors.

    Never treat an HTTPError (a real HTTP response with a 4xx/5xx status)
    as transient -- those must not be retried.
    """
    if isinstance(err, urllib.error.HTTPError):
        return False
    if isinstance(err, urllib.error.URLError):
        reason = err.reason
        text = str(reason).lower()
        return any(marker in text for marker in _TRANSIENT_MARKERS)
    if isinstance(err, TimeoutError):
        return True
    return False


def build_cookie_opener() -> Tuple[urllib.request.OpenerDirector, http.cookiejar.CookieJar]:
    """Build a urllib opener that keeps cookies across requests (a session).

    Used by wiedza.py to carry the Liferay session cookie from the initial
    landing-page GET into the subsequent search POST / detail GET.
    """
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return opener, jar


def raw_request(
    url: str,
    method: str = "GET",
    data: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
    opener: Optional[urllib.request.OpenerDirector] = None,
    timeout: int = TIMEOUT_SECONDS,
) -> Tuple[int, "urllib.request.addinfourl", str]:
    """Perform an HTTP request with the shared retry/timeout policy.

    Returns (status_code, response_headers, decoded_text_body).
    Raises RuntimeError on HTTP error status or exhausted network retries.
    """
    request_headers: Dict[str, str] = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)

    opener_open = opener.open if opener is not None else urllib.request.urlopen

    last_err: Optional[BaseException] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with opener_open(req, timeout=timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                return resp.status, resp.headers, text
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:
                pass
            snippet = body.decode("utf-8", errors="replace")[:500]
            raise RuntimeError(
                f"HTTP {exc.code} {exc.reason} fetching {url}. "
                f"Response snippet: {snippet!r}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if _is_transient(exc) and attempt < MAX_ATTEMPTS:
                continue
            raise RuntimeError(f"Network error fetching {url}: {exc}") from exc

    # Defensive: the loop above always returns or raises.
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def fetch_json(url: str, headers: Optional[Dict[str, str]] = None) -> Any:
    """GET a URL and return the parsed JSON body."""
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    _status, _resp_headers, text = raw_request(url, method="GET", headers=request_headers)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = text[:500]
        raise RuntimeError(
            f"Failed to parse JSON response from {url}: {exc}. "
            f"Response snippet: {snippet!r}"
        ) from exc


def fetch_text(
    url: str,
    method: str = "GET",
    data: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
    opener: Optional[urllib.request.OpenerDirector] = None,
) -> str:
    """Fetch a URL (GET or POST) and return the raw decoded text body (HTML)."""
    request_headers = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"}
    if headers:
        request_headers.update(headers)
    _status, _resp_headers, text = raw_request(
        url, method=method, data=data, headers=request_headers, opener=opener
    )
    return text


def build_query(params: Dict[str, Any]) -> str:
    """Build a URL query string from a dict, supporting repeated params for
    list values (e.g. {'year': [2020, 2021]} -> 'year=2020&year=2021').

    None values and empty strings are dropped (mirrors the source TS
    `appendIfDefined` helper used across these tools). Booleans/ints/floats
    are stringified.
    """
    pairs = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if item is None or item == "":
                    continue
                pairs.append((key, str(item)))
        else:
            pairs.append((key, str(value)))
    return urllib.parse.urlencode(pairs)
