---
name: polish-educational-resources
description: Search and browse free, Creative-Commons-licensed K-12 e-textbooks and learning materials from epodreczniki.pl (Zintegrowana Platforma Edukacyjna / ORE-MEN, Poland's Integrated Educational Platform). Use for "Polish e-textbooks", "podreczniki szkolne", "e-podreczniki", "materialy edukacyjne MEN", "otwarte zasoby edukacyjne", "ORE", "K-12 education Poland", "lekcje online". Not for university/academic-level sources -- see polish-academic-repositories and polish-science-bibliography for those. No API key needed.
---

# Polish Educational Resources (epodreczniki.pl)

## Overview

This skill provides access to **epodreczniki.pl**, Poland's Ministry of
Education (MEN) / Osrodek Rozwoju Edukacji (ORE) platform of free,
Creative-Commons-licensed K-12 e-textbooks and learning materials, via its
public "open API" (documented by ORE in a PDF, referenced below).

This is a **different domain** from the other skills in this collection:
it covers primary/secondary school (K-12) teaching materials, not
university-level publications, theses, or research data. If the user is
asking about academic/scientific literature, use `polish-academic-repositories`
or `polish-science-bibliography` instead.

No API key or authentication is required.

`scripts/epodreczniki.py` is standard-library-only Python 3 (`urllib`,
`json`, `argparse`) — no dependencies to install.

## Important caveat: partially self-discovering API

The exact list of resource collections (textbooks, units, exercises, etc.)
under the API root, and which filters each one supports, were **not**
independently verified against a live response — only the existence of the
root/`?format=json` convention is confirmed from ORE's own documentation.
**Always call `root` first** to see the platform's current, real list of
collections before guessing a `--path` for `browse`. If a `--search`/`--page`
filter has no visible effect on a collection, that collection likely doesn't
support it — try `--param KEY=VALUE` with a name you see in that collection's
own JSON structure instead.

## Scripts

| Script | Subcommand | Description |
|---|---|---|
| `scripts/epodreczniki.py` | `root` | Lists every available resource collection and its URL. **Run this first.** |
| `scripts/epodreczniki.py` | `browse` | Fetches/searches one collection by relative `--path` (from `root`'s output), with optional `--search`, `--page`, and raw `--param KEY=VALUE` passthrough filters. |

## Usage

Discover what's available:

```bash
python3 scripts/epodreczniki.py root
```

Browse (or best-effort search within) a discovered collection:

```bash
python3 scripts/epodreczniki.py browse --path textbooks --search "matematyka"
python3 scripts/epodreczniki.py browse --path units --page 2
python3 scripts/epodreczniki.py browse --path textbooks --param subject=biologia
```

Every command prints pretty-printed JSON to stdout on success, or a clear
`Error: ...` message to stderr with a non-zero exit code on failure.

## Notes

- All content is Creative Commons licensed and free to read; the platform
  targets Polish primary and secondary school curricula.
- Source: https://epodreczniki.pl (API: http://api.epodreczniki.pl,
  documented in ORE's "Otwarte API platformy" PDF:
  https://ore.edu.pl/attachments/article/6993/Otwarte_API_platformy.pdf).
- Only one source is in this skill, so there is no `search_all.py`
  aggregator here (unlike the multi-source skills in this collection).

## Attribution

This skill is not a port from `polish-academic-mcp` (that project does not
cover K-12 educational content) — it was added directly to
`polish-academic-skills` to extend coverage into Polish public educational
resources, following the same standalone-script conventions as the rest of
this collection.
