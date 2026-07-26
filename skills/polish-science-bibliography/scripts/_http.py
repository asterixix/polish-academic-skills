"""Shared HTTP helper for the polish-science-bibliography skill scripts.

Standard library only (urllib). Mirrors the network policy used by the
source TypeScript project's cache.ts:
  - Hard timeout of 30 seconds per attempt.
  - A single automatic retry, only for transient network errors (connection
    reset, DNS hiccups, timeouts) -- never for HTTP error responses.
  - HTTP 4xx and 5xx responses are never retried; they are raised
    immediately as a RuntimeError carrying the status code and a short
    (<=1024 char) body snippet for debugging.

Not a general-purpose library -- kept intentionally small and embedded in
this skill only, per the "no shared deps across skills" rule.
"""

from __future__ import annotations

import json
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


def request_json(url: str, method: str = "GET", headers: dict | None = None,
                  data: bytes | None = None, timeout: int = TIMEOUT_SECONDS):
    """Like request(), but decodes the response body as JSON.

    Falls back to {"_raw": <text>} if the body is not valid JSON (some of
    these public endpoints occasionally answer with plain text or HTML on
    unexpected upstream errors).
    """
    _status, body, _headers = request(url, method=method, headers=headers, data=data, timeout=timeout)
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


def prune(obj: dict) -> dict:
    """Drop keys whose value is None or an empty list, like the TS prune()."""
    out = {}
    for k, v in obj.items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)) and len(v) == 0:
            continue
        out[k] = v
    return out


def fail(message: str) -> None:
    """Print a clear error to stderr and exit(1)."""
    print(message, file=sys.stderr)
    sys.exit(1)


def print_result(result) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2))
