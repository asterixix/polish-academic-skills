#!/usr/bin/env python3
"""
Fan out one query across every free-text-searchable source in this skill and
return combined results in a single JSON document.

USE THIS FIRST for any broad "find this publication/researcher in Polish
science bibliography" question -- it queries PBN and Ludzie Nauki in
parallel so nothing gets missed just because only one source was tried.
Call an individual script directly once you already know which single
source has the answer, or for POL-on (structured filters only, see below).

NOT included (no free-text query concept -- call directly with structured
filters):
  polon.py -- POL-on/RAD-on datasets are queried by exact structured filters
  (--institution-name, --last-name, --project-number, ...), not free text.

Query mapping per source:
  pbn          search-publications --title <q>     (requires PBN_APP_ID/PBN_APP_TOKEN env vars -- errors cleanly if unset)
  ludzie_nauki semantic-search --full-query <q>     (free-text/semantic researcher profile search)

Per-source failures (timeout, HTTP error, missing PBN credentials) never
abort the others -- each source's outcome is reported independently under
"results".
"""

from __future__ import annotations

import argparse
import json

from _aggregate import run_sources


def build_jobs(args: argparse.Namespace) -> dict[str, list[str]]:
    return {
        "pbn": ["search-publications", "--title", args.query],
        "ludzie_nauki": ["semantic-search", "--full-query", args.query],
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Query every free-text source in polish-science-bibliography at once."
    )
    p.add_argument("--query", required=True, help="Search phrase, applied to both sources.")
    args = p.parse_args()

    jobs = build_jobs(args)
    results = run_sources(jobs)

    print(json.dumps({
        "query": args.query,
        "sources_queried": sorted(jobs.keys()),
        "sources_not_included": ["polon"],
        "sources_not_included_reason": "Structured-filter datasets only (institution/employee/project/publication fields) -- no free-text query parameter. Call polon.py directly.",
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
