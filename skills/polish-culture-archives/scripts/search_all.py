#!/usr/bin/env python3
"""
Fan out one query across every free-text-searchable source in this skill and
return combined results in a single JSON document.

USE THIS FIRST for any broad "find X in Polish cultural heritage archives"
question -- it queries BazTOL, Baza Legalnych Zrodel (BLZ), NAC, PAUart, and
Katalog SUM (Aleph) in parallel so nothing gets missed just because only one
source was tried. Call an individual script directly only once you already
know which single source has the answer.

NOT included (no free-text query concept -- call these directly):
  dokumenty_slaska.py  -- fixed-path document series browsing, not searchable by keyword.
  wolne_lektury.py     -- taxonomy/filter browsing (author slug, genre, epoch), not free-text.

Per-source failures (timeout, HTTP error, known upstream outage such as
sum_aleph's missing SRU gate) never abort the others -- each source's
outcome is reported independently under "results".
"""

from __future__ import annotations

import argparse
import json

from _aggregate import run_sources


def build_jobs(args: argparse.Namespace) -> dict[str, list[str]]:
    return {
        "baztol": ["search", "--query", args.query],
        "blz": ["search", "--query", args.query],
        "nac": ["site-search", "--query", args.query],
        "pauart": ["search", "--query", args.query],
        "sum_aleph": ["find", "--base", args.sum_base, "--request", f"wrd={args.query}"],
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Query every free-text source in polish-culture-archives at once."
    )
    p.add_argument("--query", required=True, help="Search phrase, applied to every source.")
    p.add_argument(
        "--sum-base", dest="sum_base", default="SUM01",
        help="Aleph bibliographic base for the Katalog SUM source. Default SUM01 (main catalog).",
    )
    args = p.parse_args()

    jobs = build_jobs(args)
    results = run_sources(jobs)

    print(json.dumps({
        "query": args.query,
        "sources_queried": sorted(jobs.keys()),
        "sources_not_included": ["dokumenty_slaska", "wolne_lektury"],
        "sources_not_included_reason": "Path/taxonomy browsing only -- no free-text query parameter. Call directly.",
        "results": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
