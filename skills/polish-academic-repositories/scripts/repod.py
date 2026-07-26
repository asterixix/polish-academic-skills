#!/usr/bin/env python3
"""
RePOD -- ICM University of Warsaw open research data repository. Runs a
CeON fork of Dataverse (branched from v4.11). ~3,737 datasets; all DOIs
use the 10.18150/ prefix. All search and read operations work anonymously.

Note: some Dataverse v5+/v6+ features (geo_point search, Croissant metadata)
may not be available due to the fork's age.

Subcommands (ported from repod_search / repod_get_dataset):
  search      -- search datasets, dataverses, and files.
  get-dataset -- retrieve a dataset's metadata by DOI (multiple export formats).

Source: https://repod.icm.edu.pl
"""

import argparse
import json
from urllib.parse import quote

import _http

API_BASE = "https://repod.icm.edu.pl/api"

EXPORT_FORMATS = ["datacite", "dcterms", "schema.org", "ddi", "dataverse_json"]


def normalize_search(raw: str) -> dict:
    parsed = _http.parse_json_response(raw, API_BASE)
    data = parsed.get("data") or {}
    raw_items = data.get("items") or []
    items = []
    for it in raw_items:
        global_id = it.get("global_id")
        doi = global_id[4:] if isinstance(global_id, str) and global_id.startswith("doi:") else global_id
        authors = it.get("authors")
        items.append(
            {
                "title": it.get("name"),
                "author": ", ".join(authors) if authors else None,
                "date": it.get("published_at"),
                "doi": doi,
                "url": it.get("url"),
                "type": it.get("type"),
                "abstract": it.get("description"),
                "source_raw": it,
            }
        )
    return {
        "query": data.get("q"),
        "total_count": data.get("total_count"),
        "start": data.get("start"),
        "items": items,
    }


def cmd_search(args: argparse.Namespace) -> dict:
    params = [("q", args.query), ("per_page", str(args.per_page)), ("start", str(args.start))]
    if args.type:
        params.append(("type", args.type))
    url = f"{API_BASE}/search?{_http.build_query(params)}"
    raw = _http.fetch(url)
    return normalize_search(raw)


def _maybe_json(text: str):
    """Best-effort parse; returns the parsed object, or the raw text if it isn't JSON
    (export formats other than dataverse_json/schema.org may be XML: datacite, dcterms, ddi)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def cmd_get_dataset(args: argparse.Namespace) -> dict:
    persistent_id = f"doi:{args.doi}"
    export_url = (
        f"{API_BASE}/datasets/export?exporter={quote(args.format, safe='')}"
        f"&persistentId={quote(persistent_id, safe='')}"
    )
    try:
        exported = _http.fetch(export_url)
        return {"requested_format": args.format, "content": _maybe_json(exported)}
    except _http.HttpError as e:
        if e.status not in (400, 404):
            raise
        # RePOD's export endpoint is intermittently broken for valid datasets;
        # fall back to the native Dataverse JSON representation.
        fallback_url = (
            f"{API_BASE}/datasets/:persistentId/versions/:latest"
            f"?persistentId={quote(persistent_id, safe='')}"
        )
        fallback_raw = _http.fetch(fallback_url)
        return {
            "requested_format": args.format,
            "fallback_format": "dataverse_json",
            "note": "RePOD export endpoint returned 400/404; served latest Dataverse JSON dataset version instead.",
            "dataset": _http.parse_json_response(fallback_raw, fallback_url),
        }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="RePOD -- ICM University of Warsaw open research data repository (Dataverse-based)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search datasets/dataverses/files.")
    s.add_argument("--query", required=True, help="Search query.")
    s.add_argument("--type", choices=["dataset", "dataverse", "file"], help="Restrict results to one content type.")
    s.add_argument("--per-page", dest="per_page", type=int, default=10, help="Results per page (max 100). Default: 10.")
    s.add_argument("--start", type=int, default=0, help="Zero-based offset for pagination. Default: 0.")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get-dataset", help="Retrieve dataset metadata by DOI.")
    g.add_argument("--doi", required=True, help="Dataset DOI without the doi: prefix, e.g. 10.18150/ABCDEF.")
    g.add_argument(
        "--format",
        choices=EXPORT_FORMATS,
        default="datacite",
        help="Metadata export format: datacite (DataCite XML), dcterms (Dublin Core RDF/XML), "
        "schema.org (JSON-LD), ddi, or dataverse_json (native record). Default: datacite.",
    )
    g.set_defaults(func=cmd_get_dataset)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except _http.HttpError as e:
        _http.fail(f"{e} (status={e.status})")
    except Exception as e:  # noqa: BLE001
        _http.fail(str(e))


if __name__ == "__main__":
    main()
