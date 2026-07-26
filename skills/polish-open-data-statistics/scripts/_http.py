"""Shared HTTP helper for the polish-open-data-statistics skill scripts.

Standard-library only (urllib). No third-party dependencies.

Network policy (mirrors the source MCP server's cache.ts):
  - 30 second hard timeout per request.
  - A single automatic retry on transient network errors only
    (connection resets/refused, unreachable network, timeouts, generic
    URLError caused by an underlying OSError). HTTP 4xx/5xx responses are
    NEVER retried.
  - On failure, raise a RuntimeError with a clear message including the
    HTTP status (if any) and a short snippet of the response body.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

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


def fetch_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    """GET a URL and return the parsed JSON body.

    Retries once on transient network errors only. Raises RuntimeError with
    a clear, actionable message (including HTTP status and a body snippet)
    on any failure.
    """
    request_headers: Dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if headers:
        request_headers.update(headers)

    last_err: Optional[BaseException] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers=request_headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                snippet = text[:500]
                raise RuntimeError(
                    f"Failed to parse JSON response from {url}: {exc}. "
                    f"Response snippet: {snippet!r}"
                ) from exc
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
            raise RuntimeError(
                f"Network error fetching {url}: {exc}"
            ) from exc

    # Defensive: the loop above always returns or raises.
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def build_query(params: Dict[str, Any]) -> str:
    """Build a URL query string from a dict, supporting repeated params for
    list values (e.g. {'year': [2020, 2021]} -> 'year=2020&year=2021').

    None values are dropped. Booleans/ints/floats are stringified.
    """
    import urllib.parse

    pairs = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if item is None:
                    continue
                pairs.append((key, str(item)))
        else:
            pairs.append((key, str(value)))
    return urllib.parse.urlencode(pairs)
