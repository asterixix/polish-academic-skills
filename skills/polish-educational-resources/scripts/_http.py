"""
Shared HTTP + parsing helpers for the polish-educational-resources skill.

Standard-library only. Embedded in THIS skill only -- do not import from
sibling skill directories.

Network policy (mirrors the original polish-academic-mcp TypeScript
`cachedFetch` in src/cache.ts):
  - Hard timeout of 30 seconds per attempt.
  - Exactly one retry, and only for transient network errors (timeouts,
    connection reset/refused, DNS/socket errors). HTTP 4xx/5xx responses
    are NEVER retried -- they are raised immediately as HttpError.
  - On HTTP error, raise HttpError with the status code and a short
    (first ~300 chars) snippet of the response body for debugging.
"""

from __future__ import annotations

import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = "polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)"
DEFAULT_TIMEOUT = 30
MAX_ATTEMPTS = 2


class HttpError(RuntimeError):
    """Raised for non-2xx HTTP responses. Never retried."""

    def __init__(self, status: int, url: str, body_snippet: str):
        super().__init__(f"HTTP {status} fetching {url}: {body_snippet}")
        self.status = status
        self.url = url
        self.body_snippet = body_snippet


def _is_transient(exc: BaseException) -> bool:
    """True for network-level glitches worth a single retry (never for HTTP 4xx/5xx)."""
    if isinstance(exc, socket.timeout):
        return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return True
        msg = str(reason).lower()
        transient_markers = (
            "connection reset",
            "econnreset",
            "connection refused",
            "econnrefused",
            "timed out",
            "etimedout",
            "network is unreachable",
            "enetunreach",
            "temporary failure in name resolution",
        )
        if any(marker in msg for marker in transient_markers):
            return True
    if isinstance(exc, (ConnectionResetError, ConnectionRefusedError, OSError)):
        return True
    return False


def fetch(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    data: bytes | str | dict | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Fetch a URL, returning the decoded response body as text.

    Retries exactly once on transient network errors. HTTP error responses
    (4xx/5xx) raise HttpError immediately (no retry), including a short body
    snippet for debugging.
    """
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    body: bytes | None
    if isinstance(data, (dict, list)):
        body = json.dumps(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        body = data.encode("utf-8")
    else:
        body = data

    last_exc: BaseException | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            # HTTP status error -- never retried.
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            snippet = err_body[:300]
            raise HttpError(e.code, url, snippet) from e
        except Exception as e:  # noqa: BLE001 - broad on purpose, filtered by _is_transient
            last_exc = e
            if attempt < MAX_ATTEMPTS and _is_transient(e):
                time.sleep(0.5)
                continue
            raise RuntimeError(f"Network error fetching {url}: {e}") from e

    # Should be unreachable; loop either returns or raises.
    raise RuntimeError(f"Failed to fetch {url}: {last_exc}")


def build_query(params: list[tuple[str, str]]) -> str:
    """URL-encode a list of (key, value) pairs, preserving repeated keys (for DSpace f.* filters)."""
    return urllib.parse.urlencode(params)


def fail(message: str) -> None:
    """Print a clear error message to stderr and exit(1)."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


# ── DSpace 7/8 discovery-search helpers (RUJ, AGH, AMU, UAFM, ICM) ──────────

VALID_DSPACE_OPS = {
    "equals",
    "notequals",
    "contains",
    "notcontains",
    "authority",
    "notauthority",
    "query",
}


def add_dspace_filter(params: list[tuple[str, str]], field: str, value: str, default_op: str) -> None:
    """
    Append a DSpace discovery filter parameter `f.<field>=value[,op]`.

    If the caller already embedded a valid operator suffix after the last
    comma (e.g. "Smith,equals") it is used as-is; otherwise default_op is
    appended. Mirrors addFilter() in the original TS tools exactly.
    """
    last_comma = value.rfind(",")
    trailing_token = value[last_comma + 1 :] if last_comma != -1 else ""
    if trailing_token in VALID_DSPACE_OPS:
        params.append((f"f.{field}", value))
    else:
        params.append((f"f.{field}", f"{value},{default_op}"))


def dc_first(meta: dict, key: str) -> str:
    """First value of a DSpace metadata field array, or ''."""
    arr = meta.get(key) if isinstance(meta, dict) else None
    if isinstance(arr, list) and arr:
        v = arr[0]
        if isinstance(v, dict):
            return str(v.get("value") or "")
    return ""


def dc_all(meta: dict, key: str) -> list[str]:
    """All values of a DSpace metadata field array, as strings, empty ones dropped."""
    arr = meta.get(key) if isinstance(meta, dict) else None
    if not isinstance(arr, list):
        return []
    out = []
    for v in arr:
        if isinstance(v, dict):
            s = str(v.get("value") or "")
            if s:
                out.append(s)
    return out


def truncate(s: str, n: int) -> str:
    if s and len(s) > n:
        return s[:n] + "…"
    return s


def parse_json_response(raw: str, url: str):
    """Parse a JSON response body, raising a clear RuntimeError on failure."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        snippet = raw[:300].replace("\n", " ")
        raise RuntimeError(
            f"Could not parse JSON response from {url}: {e}. Body starts with: {snippet!r}"
        ) from e


# ── OAI-PMH XML helpers (Biblioteka Nauki articles, RCIN) ──────────────────

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
OAI_DC_NS = "http://www.openarchives.org/OAI/2.0/oai_dc/"
DC_NS = "http://purl.org/dc/elements/1.1/"

_DC_FIELDS = (
    "title",
    "creator",
    "subject",
    "description",
    "publisher",
    "contributor",
    "date",
    "type",
    "format",
    "identifier",
    "source",
    "language",
    "relation",
    "coverage",
    "rights",
)


def _local(tag: str) -> str:
    """Strip the {namespace} prefix from an ElementTree tag."""
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_oai_pmh(xml_text: str, url: str) -> dict:
    """
    Parse an OAI-PMH response (ListRecords or GetRecord) into a clean dict.

    Returns a dict with keys among: error, records, resumption_token,
    complete_list_size, cursor -- for ListRecords -- or `record` for
    GetRecord. Each record has: identifier, datestamp, set_spec (list),
    deleted (bool), and metadata.

    For oai_dc metadata, `metadata` is a dict of Dublin Core field name ->
    list of string values (e.g. {"title": [...], "creator": [...]}).
    For any other metadataPrefix (jats, mets, oai_etdms, dlibra_avs,
    oai_qdc), full structural parsing is out of scope (those are not
    Dublin Core); `metadata` instead contains `metadata_raw_xml`, a
    serialized XML string of the <metadata> element so no information is
    lost.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        snippet = xml_text[:300].replace("\n", " ")
        raise RuntimeError(
            f"Could not parse OAI-PMH XML response from {url}: {e}. Body starts with: {snippet!r}"
        ) from e

    # OAI-PMH-level <error code="...">message</error> (e.g. noRecordsMatch, idDoesNotExist, badArgument)
    for child in root:
        if _local(child.tag) == "error":
            return {
                "error": child.attrib.get("code", "unknown_error"),
                "message": (child.text or "").strip(),
            }

    def parse_record(record_el: ET.Element) -> dict:
        header_el = None
        metadata_el = None
        for c in record_el:
            tag = _local(c.tag)
            if tag == "header":
                header_el = c
            elif tag == "metadata":
                metadata_el = c

        rec: dict = {"identifier": None, "datestamp": None, "set_spec": [], "deleted": False}
        if header_el is not None:
            rec["deleted"] = header_el.attrib.get("status") == "deleted"
            for hc in header_el:
                tag = _local(hc.tag)
                if tag == "identifier":
                    rec["identifier"] = (hc.text or "").strip()
                elif tag == "datestamp":
                    rec["datestamp"] = (hc.text or "").strip()
                elif tag == "setSpec":
                    rec["set_spec"].append((hc.text or "").strip())

        if metadata_el is not None and len(metadata_el) > 0:
            dc_root = metadata_el[0]
            if _local(dc_root.tag) == "dc":
                fields: dict = {}
                for el in dc_root:
                    field = _local(el.tag)
                    text = (el.text or "").strip()
                    if not text:
                        continue
                    fields.setdefault(field, []).append(text)
                # Convenience singular accessors for the common fields.
                rec["metadata"] = {
                    "title": fields.get("title", []),
                    "creator": fields.get("creator", []),
                    "subject": fields.get("subject", []),
                    "description": fields.get("description", []),
                    "date": fields.get("date", []),
                    "publisher": fields.get("publisher", []),
                    "type": fields.get("type", []),
                    "language": fields.get("language", []),
                    "identifier": fields.get("identifier", []),
                    "source": fields.get("source", []),
                    "relation": fields.get("relation", []),
                    "rights": fields.get("rights", []),
                    "format": fields.get("format", []),
                    "coverage": fields.get("coverage", []),
                    "contributor": fields.get("contributor", []),
                }
            else:
                rec["metadata"] = {"metadata_raw_xml": ET.tostring(metadata_el, encoding="unicode")}
        else:
            rec["metadata"] = {}
        return rec

    # GetRecord response
    for child in root:
        if _local(child.tag) == "GetRecord":
            record_el = None
            for c in child:
                if _local(c.tag) == "record":
                    record_el = c
            if record_el is None:
                return {"error": "no_record", "message": "GetRecord response had no <record>."}
            return {"record": parse_record(record_el)}

    # ListRecords response
    for child in root:
        if _local(child.tag) == "ListRecords":
            records = []
            resumption_token = None
            complete_list_size = None
            cursor = None
            for c in child:
                tag = _local(c.tag)
                if tag == "record":
                    records.append(parse_record(c))
                elif tag == "resumptionToken":
                    token_text = (c.text or "").strip()
                    resumption_token = token_text or None
                    if "completeListSize" in c.attrib:
                        try:
                            complete_list_size = int(c.attrib["completeListSize"])
                        except ValueError:
                            complete_list_size = c.attrib["completeListSize"]
                    if "cursor" in c.attrib:
                        try:
                            cursor = int(c.attrib["cursor"])
                        except ValueError:
                            cursor = c.attrib["cursor"]
            return {
                "records": records,
                "resumption_token": resumption_token,
                "complete_list_size": complete_list_size,
                "cursor": cursor,
            }

    return {"error": "unrecognized_response", "message": "No GetRecord/ListRecords/error element found."}


def has_no_records_match(xml_text: str) -> bool:
    """True if the OAI-PMH response is an <error code="noRecordsMatch"> (used for RCIN/BN set-fallback retry)."""
    return 'code="noRecordsMatch"' in xml_text or "code='noRecordsMatch'" in xml_text


# ── PII scrubbing (mirrors scrubPiiXml / scrubPii in the TS tools) ─────────

import re as _re

_ORCID_RE = _re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")
_EMAIL_RE = _re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PESEL_RE = _re.compile(r"\b\d{11}\b")
_PHONE_RE = _re.compile(r"\+?[\d\s\-()]{9,}")


def scrub_pii(text: str) -> str:
    text = _ORCID_RE.sub("[REDACTED_ORCID]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PESEL_RE.sub("[REDACTED_PESEL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text
