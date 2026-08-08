#!/usr/bin/env python3
"""
Fan out one query across every source in this skill and return combined
results in a single JSON document.

USE THIS FIRST for any broad "find X in Polish law/standards/judgments/
parliamentary library" question -- it queries Biblioteka Sejmowa, ISAP,
PKN, SAOS, and WIEDZA-PKN in parallel so nothing gets missed just because
only one source was tried. Call an individual script directly once you
already know which single source has the answer, or when you need a filter
this aggregator doesn't expose (e.g. SAOS court/date filters, ISAP
publisher/year, WIEDZA ICS code).

Query mapping per source (each source's search shape differs -- this picks
the closest free-text-equivalent field):
  biblioteka_sejmowa search --query <q> --local-base bis01   (main catalog; WRD=all-fields index)
  isap               search-acts --title <q>                  (ISAP has no true full-text; title is closest)
  pkn                search --query <q>                        (pkn.pl site content, NOT the norms catalog)
  saos                search-judgments --all <q>                (full-text/metadata phrase)
  wiedza             search-norms --title <q>                   (Polish Standards catalog; title match)

Per-source failures (timeout, HTTP error) never abort the others -- each
source's outcome is reported independently under "results".
"""

from __future__ import annotations

import argparse
import json

from _aggregate import run_sources


def build_jobs(args: argparse.Namespace) -> dict[str, list[str]]:
    return {
        "biblioteka_sejmowa": ["search", "--query", args.query, "--local-base", args.sejm_base],
        "isap": ["search-acts", "--title", args.query],
        "pkn": ["search", "--query", args.query],
        "saos": ["search-judgments", "--all", args.query],
        "wiedza": ["search-norms", "--title", args.query],
    }


def main() -> None:
    p = argparse.ArgumentParser(
        description="Query every source in polish-legal-normative-documents at once."
    )
    p.add_argument("--query", required=True, help="Search phrase, mapped to each source's closest field.")
    p.add_argument(
        "--sejm-base", dest="sejm_base", default="bis01",
        help="Aleph local base for Biblioteka Sejmowa. Default bis01 (main catalog). "
        "Other options: bis05 (journal articles), pos01 (session recordings), tek01 (constitutional texts), sta01 (old prints).",
    )
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
