#!/usr/bin/env python3
"""
RODBuK -- Krakow inter-university open research data repository
(AGH, UEK, UP, UR, UJ, PK). Powered by Harvard Dataverse. All read
endpoints are open, no authentication required.

Subcommand (ported from rodbuk_search):
  search -- search datasets, dataverses, and files. Use --query '*' to browse everything.

Source: https://rodbuk.pl
"""

import argparse
import json

import _http

API_BASE = "https://rodbuk.pl/api"


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="RODBuK -- Krakow inter-university open research data repository (Harvard Dataverse)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search datasets/dataverses/files. Use --query '*' to list everything.")
    s.add_argument("--query", required=True, help="Search query. Use '*' to list all available collections.")
    s.add_argument("--type", choices=["dataset", "dataverse", "file"], help="Restrict results to one content type.")
    s.add_argument("--per-page", dest="per_page", type=int, default=10, help="Results per page (max 100). Default: 10.")
    s.add_argument("--start", type=int, default=0, help="Zero-based offset for pagination. Default: 0.")
    s.set_defaults(func=cmd_search)

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
