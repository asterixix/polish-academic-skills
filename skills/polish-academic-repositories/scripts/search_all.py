#!/usr/bin/env python3
"""
Fan out one query across every free-text-searchable source in this skill and
return combined results in a single JSON document.

USE THIS FIRST for any broad "find publications/theses/datasets about X"
question -- it queries Biblioteka Nauki, RUJ, AGH, AMU, UAFM, ICM, RODBuK,
and RePOD in parallel so nothing gets missed just because only one source
was tried. Call an individual script directly only once you already know
which single source has the answer (e.g. `get`/`get-dataset` by id/UUID/DOI,
or an OAI-PMH date-range harvest).

NOT included (no free-text query concept -- OAI-PMH metadata harvesting
only; call these directly with --from-date/--until-date/--set instead):
  rcin.py, depot_ceon.py, ppm.py, biblioteka_nauki.py search-articles

Per-source failures (timeout, HTTP error, empty backend) never abort the
others -- each source's outcome is reported independently under "results".
"""

from __future__ import annotations

import argparse
import json

from _aggregate import run_sources

DSPACE_SOURCES = ["ruj", "agh", "amu", "uafm", "icm"]


def build_jobs(args: argparse.Namespace) -> dict[str, list[str]]:
    jobs: dict[str, list[str]] = {}

    for name in DSPACE_SOURCES:
        job = ["search", "--query", args.query, "--size", str(args.size)]
        if args.author:
            job += ["--author", args.author]
        jobs[name] = job

    jobs["biblioteka_nauki"] = [
        "search-publications", "--query", args.query, "--page-size", str(args.size)
    ]
    jobs["repod"] = ["search", "--query", args.query, "--per-page", str(args.size)]
    jobs["rodbuk"] = ["search", "--query", args.query, "--per-page", str(args.size)]

    return jobs


def main() -> None:
    p = argparse.ArgumentParser(
        description="Query every free-text source in polish-academic-repositories at once."
    )
    p.add_argument("--query", required=True, help="Full-text search expression, applied to every source.")
    p.add_argument("--author", default=None, help="Author filter, applied to the DSpace sources that support it (RUJ/AGH/AMU/UAFM/ICM).")
    p.add_argument("--size", type=int, default=10, help="Results per source (each source's own cap applies). Default 10.")
    args = p.parse_args()

    jobs = build_jobs(args)
    results = run_sources(jobs)

    print(json.dumps({
        "query": args.query,
        "sources_queried": sorted(jobs.keys()),
        "sources_not_included": ["rcin", "depot_ceon", "ppm", "biblioteka_nauki.search-articles"],
        "sources_not_included_reason": "OAI-PMH metadata harvesting only -- no free-text query parameter. Call directly with --from-date/--until-date/--set.",
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
