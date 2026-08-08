#!/usr/bin/env python3
"""
Fan out one query across every source in this skill and return combined
results in a single JSON document.

USE THIS FIRST for any broad "find X in Polish open data / official
statistics" question -- it queries dane.gov.pl and BDL/GUS (by subject name)
in parallel so nothing gets missed just because only one source was tried.
Call bdl.py directly for anything past subject discovery (variables, units,
actual data series by variable id) -- search_all only covers the first hop
(finding a matching BDL subject), since BDL's data itself is not free-text
searchable, it's a subject -> variable -> data drill-down.

Query mapping per source:
  dane_gov_pl search --query <q>          (open dataset catalog full-text search)
  bdl          search-subjects --name <q>  (BDL subject-tree name match; use the result's id with bdl.py search-variables/data-by-variable)

Per-source failures (timeout, HTTP error) never abort the others -- each
source's outcome is reported independently under "results".
"""

from __future__ import annotations

import argparse
import json

from _aggregate import run_sources


def build_jobs(args: argparse.Namespace) -> dict[str, list[str]]:
    return {
        "dane_gov_pl": ["search", "--query", args.query],
        "bdl": ["search-subjects", "--name", args.query],
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Query every source in polish-open-data-statistics at once."
    )
    p.add_argument("--query", required=True, help="Search phrase, applied to both sources.")
    args = p.parse_args()

    jobs = build_jobs(args)
    results = run_sources(jobs)

    print(json.dumps({
        "query": args.query,
        "sources_queried": sorted(jobs.keys()),
        "note": "BDL result is a subject-tree match only -- drill into bdl.py search-variables --subject-id <id>, then data-by-variable, to get actual statistics.",
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
