"""Shared HTTP helper for the polish-weather-hydrology skill.

Standard-library only (urllib). Implements the same network policy as the
source MCP server's cache.ts:
  - Hard timeout of 30 seconds per attempt.
  - A single automatic retry on transient network errors only (connection
    reset/refused/unreachable, timeouts, generic URLError caused by an
    underlying OSError). HTTP 4xx/5xx responses are NEVER retried.
  - On a non-2xx HTTP response, raise a RuntimeError with the status code
    and a truncated body snippet for debugging.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

USER_AGENT = "polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)"
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 2


def _is_transient_network_error(exc: BaseException) -> bool:
    """Mirror cache.ts's isTransientNetworkError: retry only wire glitches,
    never HTTP status errors (those are urllib.error.HTTPError, a distinct
    subclass handled separately by the caller)."""
    if isinstance(exc, urllib.error.HTTPError):
        return False
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, urllib.error.URLError):
        # URLError.reason is often an OSError/socket.timeout for connection
        # resets, refusals, unreachable hosts, or DNS/timeout hiccups.
        return True
    return False


def fetch_json(url: str) -> Any:
    """GET a URL and return the parsed JSON body.

    Raises RuntimeError with a clear message (including HTTP status and a
    body snippet) on failure, after applying the retry policy above.
    """
    last_error: Optional[BaseException] = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                if not body.strip():
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            # Never retried, even on the first attempt.
            snippet = ""
            try:
                snippet = exc.read().decode("utf-8", errors="replace")[:1024]
            except Exception:
                snippet = "[unable to read response body]"
            raise RuntimeError(
                f"HTTP {exc.code} {exc.reason} fetching {url}: {snippet}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if _is_transient_network_error(exc) and attempt < MAX_ATTEMPTS:
                continue
            raise RuntimeError(f"Network error fetching {url}: {exc}") from exc

    # Defensive: the loop above always returns or raises.
    raise RuntimeError(f"Network error fetching {url}: {last_error}")
