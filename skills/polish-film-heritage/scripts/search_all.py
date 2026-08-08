#!/usr/bin/env python3
"""
Fan out one query across every source in this skill and return combined
results in a single JSON document.

USE THIS FIRST for any broad "find X in Polish film/photography heritage"
question -- it queries FilmPolski.pl, Repozytorium FN, Fototeka, Fototeka
Slaska, Gapla, and Ninateka in parallel so nothing gets missed just because
only one source was tried. Call an individual script directly only once you
already know which single source has the answer (e.g. `get-item`/`get-node`/
`get-photo`/`get-poster`/`get-vod` by id/slug).

All six scripts in this skill support a --query search, so every source is
included here.

Per-source failures (timeout, HTTP error, layout-change scraping breakage)
never abort the others -- each source's outcome is reported independently
under "results".
"""

from __future__ import annotations

import argparse
import json

from _aggregate import run_sources

SOURCES = ["filmpolski", "fn_repozytorium", "fototeka", "fototeka_slaska", "gapla", "ninateka"]


def build_jobs(args: argparse.Namespace) -> dict[str, list[str]]:
    return {name: ["search", "--query", args.query] for name in SOURCES}


def main() -> None:
    p = argparse.ArgumentParser(
        description="Query every source in polish-film-heritage at once."
    )
    p.add_argument("--query", required=True, help="Search phrase, applied to every source.")
    args = p.parse_args()

    jobs = build_jobs(args)
    results = run_sources(jobs)

    print(json.dumps({
        "query": args.query,
        "sources_queried": sorted(jobs.keys()),
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
