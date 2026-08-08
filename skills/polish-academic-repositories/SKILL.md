---
name: polish-academic-repositories
description: Search and fetch metadata from Polish academic institutional repositories and open research-data repositories -- Biblioteka Nauki, RCIN, RUJ (Jagiellonian University), AGH, AMU (Adam Mickiewicz University), UAFM, ICM Open, RODBuK, RePOD, Depot CeON, and PPM (Polska Platforma Medyczna). Covers publications, theses, dissertations, articles, book chapters, and research datasets. IMPORTANT -- for any broad topic search ("find publications about X"), run `scripts/search_all.py --query X` first: it fans out the query to every free-text-searchable source in this skill in parallel so results are never limited to a single repository. Use for "Polish academic repositories", "Polish university repository", "RCIN", "RUJ", "AGH repository", "AMU repository", "UAFM", "ICM open data", "RODBuK", "RePOD", "Depot CeON", "PPM", "Polska Platforma Medyczna", "Biblioteka Nauki", "polskie repozytoria naukowe", "prace naukowe", "publikacje naukowe", "rozprawy doktorskie", "prace dyplomowe", "dane badawcze", "repozytorium uczelniane", "DSpace", "OAI-PMH", "Dataverse". No API keys needed for any of these sources.
---

# Polish Academic Repositories

Standalone Python 3 CLI tools (standard library only, no dependencies, no
MCP server) for searching and fetching metadata from eleven Polish academic
and open research-data repositories:

- **Biblioteka Nauki** -- Poland's largest open-access publication database (articles, books, chapters).
- **RCIN** -- Repozytorium Cyfrowe Instytutów Naukowych (Digital Repository of Scientific Institutes).
- **RUJ** -- Repozytorium Uniwersytetu Jagiellońskiego (Jagiellonian University Repository).
- **AGH** -- Repozytorium AGH (AGH University of Krakow Repository).
- **AMU** -- Repozytorium UAM (Adam Mickiewicz University in Poznań Repository).
- **UAFM** -- Repozytorium UAFM / eRIKA (Andrzej Frycz Modrzewski Krakow University Repository).
- **ICM** -- Otwarte Dane Badawcze UW (ICM Open Research Data Repository, University of Warsaw).
- **RODBuK** -- Krakow inter-university open research-data repository (6 member universities).
- **RePOD** -- ICM Warsaw open research-data repository.
- **Depot CeON** -- Repozytorium Centrum Otwartej Nauki (ICM University of Warsaw), OAI-PMH only.
- **PPM** -- Polska Platforma Medyczna, a joint CRIS repository of 7 medical universities + 1 institute, OAI-PMH only.
- **EMIS/ELibM** -- European Mathematical Information Service / Electronic Library of Mathematics, a static browsable index of 100+ open-access math journals/proceedings/books (no search, no query -- category browsing only).

Use this skill when someone wants to find Polish theses, dissertations,
journal articles, book chapters, or open research datasets, or needs to
pull structured metadata (title, authors, abstract, DOI, dates, license)
for a specific item once its ID/UUID/DOI is known.

## Search across every source at once

For any broad topic query, don't stop at the first source that answers --
run **`scripts/search_all.py --query "..."`** first. It fans the query out
in parallel to Biblioteka Nauki, RUJ, AGH, AMU, UAFM, ICM, RODBuK, and RePOD
(everything with a real free-text search), and returns one combined JSON
with a `results` object keyed by source. Per-source failures never abort
the others. RCIN, Depot CeON, PPM, and Biblioteka Nauki's `search-articles`
are OAI-PMH-only (no keyword query) and are listed separately in the
aggregator's output as `sources_not_included` -- call them directly with
`--from-date`/`--until-date`/`--set` when a date-range harvest is what's
needed instead.

```bash
python3 scripts/search_all.py --query "sztuczna inteligencja" --size 5
```

**No API keys required for any source in this skill.** All endpoints are
public, read-only, and anonymous.

This is a pure port of the tool logic from the [polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp)
MCP server into standalone scripts -- see Attribution at the end.

## Quick start

```bash
# Keyword search across Biblioteka Nauki's full-text index
python3 scripts/biblioteka_nauki.py search-publications --query "sztuczna inteligencja" --page-size 5

# Harvest RCIN records from a date range
python3 scripts/rcin.py search --from-date 2020-01-01 --until-date 2020-12-31

# Search a DSpace repository (RUJ, AGH, AMU, UAFM, ICM all share this pattern)
python3 scripts/ruj.py search --query "quantum computing" --size 5

# Fetch one item by UUID once you have it from a search result
python3 scripts/ruj.py get --uuid 3fa85f64-5717-4562-b3fc-2c963f66afa6

# Browse/search open research datasets
python3 scripts/repod.py search --query "*" --per-page 5
python3 scripts/repod.py get-dataset --doi 10.18150/ABCDEF --format datacite
```

Every command prints a JSON object to stdout on success, or a clear
`Error: ...` message to stderr and exits non-zero on failure.

## Available scripts and subcommands

| Script | Subcommand | Source | What it does |
|---|---|---|---|
| `biblioteka_nauki.py` | `search-publications` | Biblioteka Nauki | Full-text keyword search (JSON search API) -- titles, abstracts, full text where indexed. **Preferred tool for keyword queries.** |
| `biblioteka_nauki.py` | `search-articles` | Biblioteka Nauki | OAI-PMH `ListRecords` -- harvest by date range and/or OAI set. **NOT a keyword search.** |
| `biblioteka_nauki.py` | `get-article` | Biblioteka Nauki | OAI-PMH `GetRecord` -- single article by numeric ID. |
| `rcin.py` | `search` | RCIN | OAI-PMH `ListRecords` -- harvest by date range and/or OAI setSpec. |
| `rcin.py` | `get` | RCIN | OAI-PMH `GetRecord` -- single object by numeric id or full OAI identifier. |
| `ruj.py` | `search` | RUJ (Jagiellonian University) | DSpace 7 discovery search: full-text + 14 filter fields, faceted, paginated. |
| `ruj.py` | `get` | RUJ | Single item's full metadata by UUID. |
| `agh.py` | `search` | AGH (AGH University of Krakow) | DSpace 7 discovery search over theses, articles, technical reports, dissertations. |
| `agh.py` | `get` | AGH | Single item's full metadata by UUID. |
| `amu.py` | `search` | AMU (Adam Mickiewicz University) | DSpace 7 discovery search. |
| `amu.py` | `get` | AMU | Single item's full metadata by UUID. |
| `uafm.py` | `search` | UAFM / eRIKA | DSpace discovery search. **Backend currently down (HTTP 404) as of the source project's last check -- see Caveats.** |
| `uafm.py` | `get` | UAFM | Single item's full metadata by UUID. Same outage caveat applies. |
| `icm.py` | `search` | ICM Open (University of Warsaw) | DSpace 7 discovery search over open research data and publications. |
| `icm.py` | `get` | ICM | Single item's full metadata by UUID. |
| `rodbuk.py` | `search` | RODBuK | Search datasets/dataverses/files (Harvard Dataverse search API). Use `--query '*'` to browse everything. |
| `repod.py` | `search` | RePOD | Search datasets/dataverses/files (Dataverse search API). |
| `repod.py` | `get-dataset` | RePOD | Dataset metadata by DOI, in one of several export formats. |
| `depot_ceon.py` | `search` | Depot CeON | OAI-PMH `ListRecords` -- harvest by date range and/or OAI setSpec. No keyword query. |
| `depot_ceon.py` | `get` | Depot CeON | OAI-PMH `GetRecord` -- single object by handle suffix or full OAI identifier. |
| `ppm.py` | `identify` | PPM | OAI-PMH `Identify` -- cheap sanity check; run before `search`/`get` since the base URL is unverified (see script docstring). |
| `ppm.py` | `search` | PPM | OAI-PMH `ListRecords` -- harvest by date range and/or OAI setSpec. No keyword query. |
| `ppm.py` | `get` | PPM | OAI-PMH `GetRecord` -- single object by full OAI identifier. |
| `emis.py` | `categories` | EMIS/ELibM | List the 6 fixed top-level categories (no network request). |
| `emis.py` | `browse` | EMIS/ELibM | Fetch one category's index page and list every link on it. Confirmed live: no search/query exists on this site. |
| `search_all.py` | *(n/a)* | all of the above except EMIS | Fans one `--query` out to every free-text source in parallel. See "Search across every source at once" above. |

Full per-parameter reference (all filter fields, default operators,
sort options, metadata formats) is in [`reference/API.md`](reference/API.md)
-- read it before constructing complex filtered queries.

## Usage examples

### Biblioteka Nauki -- full-text keyword search

```bash
python3 scripts/biblioteka_nauki.py search-publications \
  --query "uczenie maszynowe" \
  --page 1 --page-size 5 \
  --sort-field publishedDate --sort-direction DESC \
  --publication-types ARTICLE \
  --published-date-from 2022-01-01
```

Returns the raw JSON search response from `bibliotekanauki.pl/api/search`
(hits, `mainTitleSnippets`, `fullTextSnippets`, `totalResults`), pretty-printed.

### Biblioteka Nauki -- OAI-PMH harvest (dates/set only, no keywords)

```bash
python3 scripts/biblioteka_nauki.py search-articles \
  --from-date 2024-01-01 --until-date 2024-03-31 \
  --metadata-format oai_dc
```

```json
{
  "records": [
    {
      "identifier": "oai:bibliotekanauki.pl:1968869",
      "datestamp": "2024-02-10",
      "set_spec": ["journal:some-journal-id"],
      "deleted": false,
      "metadata": {
        "title": ["Some article title"],
        "creator": ["Kowalski, Jan"],
        "date": ["2024"],
        "subject": ["computer science"],
        "description": [],
        "...": "..."
      }
    }
  ],
  "resumption_token": "abc123...",
  "complete_list_size": 4821,
  "cursor": 0
}
```

Pass `--resumption-token abc123...` on the next call to continue paging (when a
resumption token is present, no other search params are sent, matching the
OAI-PMH spec). Add `--minimize-pii` to redact ORCID/email/phone/PESEL-like
patterns from the output.

### Biblioteka Nauki -- one article by ID

```bash
python3 scripts/biblioteka_nauki.py get-article --article-id 1968869 --metadata-format jats
```

### RCIN -- harvest and fetch

```bash
python3 scripts/rcin.py search --set rcin.org.pl:literature --from-date 2019-01-01
python3 scripts/rcin.py get --id 204728
python3 scripts/rcin.py get --id oai:rcin.org.pl:204728 --metadata-format oai_qdc
```

### RUJ / AGH / AMU / UAFM / ICM -- DSpace discovery search

All five run DSpace 7 (or 8 for UAFM) and share the same search shape:
zero-based `--page`, `--size` (max 50), a `--sort` field/direction pair,
and a set of `--<filter>` options that map to DSpace discovery filters
(`f.<field>=value,<operator>`). Any filter value may embed its own operator
after a trailing comma (e.g. `--author "Kowalski,equals"`); otherwise a
sensible default operator is applied per field (see `reference/API.md`).

```bash
python3 scripts/ruj.py search --query "climate change" --author "Nowak" --language pl --size 5
python3 scripts/agh.py search --query "robotics" --itemtype Thesis --date-issued "[2020-01-01 TO 2023-12-31],query"
python3 scripts/amu.py search --query "linguistics" --entity-type Publication
python3 scripts/icm.py search --query "genomics" --has-full-text true
```

Example (truncated) search output shape, identical across all five DSpace
sources modulo a few source-specific fields (see the table in
`reference/API.md`):

```json
{
  "totalElements": 128,
  "page": { "number": 0, "size": 10, "totalPages": 13 },
  "items": [
    {
      "uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "handle": "123456789/98765",
      "url": "https://ruj.uj.edu.pl/xmlui/handle/123456789/98765",
      "title": "Example publication title",
      "authors": ["Kowalski, Jan", "Nowak, Anna"],
      "type": "Article",
      "language": "en",
      "dateIssued": "2021-06-01",
      "subject": "climate change",
      "abstract": "First 500 characters of the abstract…"
    }
  ]
}
```

Fetch one item's full record:

```bash
python3 scripts/ruj.py get --uuid 3fa85f64-5717-4562-b3fc-2c963f66afa6
```

### RODBuK / RePOD -- research-data search and dataset lookup

```bash
python3 scripts/rodbuk.py search --query "*" --type dataset --per-page 10
python3 scripts/repod.py search --query "socjologia" --per-page 5
python3 scripts/repod.py get-dataset --doi 10.18150/ABCDEF --format schema.org
```

Search output shape (both sources, since RODBuK and RePOD are both
Dataverse-family installations):

```json
{
  "query": "*",
  "total_count": 3421,
  "start": 0,
  "items": [
    {
      "title": "Example dataset",
      "author": "Kowalski, Jan, Nowak, Anna",
      "date": "2022-05-01T00:00:00Z",
      "doi": "10.18150/ABCDEF",
      "url": "https://repod.icm.edu.pl/dataset.xhtml?persistentId=doi:10.18150/ABCDEF",
      "type": "dataset",
      "abstract": "Dataset description...",
      "source_raw": { "...": "the untouched Dataverse item, for anything not surfaced above" }
    }
  ]
}
```

`repod.py get-dataset` fetches the Dataverse metadata exporter
(`datacite`, `dcterms`, `schema.org`, `ddi`, or `dataverse_json`) and
wraps the body as `{"requested_format": ..., "content": ...}` (content is
parsed JSON when the export format is JSON/JSON-LD, or the raw text
string when it is XML). If RePOD's export endpoint returns HTTP 400/404
(known intermittent issue), the tool automatically falls back to the
native Dataverse JSON representation of the latest dataset version and
marks the response with `"fallback_format": "dataverse_json"`.

## Important caveats

- **OAI-PMH vs. free-text search.** Biblioteka Nauki's `search-articles`,
  RCIN's `search`, Depot CeON's `search`, PPM's `search`, and (indirectly)
  the RUJ/AGH/AMU/UAFM/ICM `search` commands' underlying protocols differ:
  `bn_search_articles`/`rcin search`/`depot_ceon search`/`ppm search` are
  **OAI-PMH harvesting** -- they slice by date range
  (`--from-date`/`--until-date`) and/or a named OAI `set`, and do **not**
  accept a keyword query. For keyword search on Biblioteka Nauki, use
  `search-publications` instead. RUJ/AGH/AMU/UAFM/ICM are DSpace
  discovery-search endpoints and do accept a full-text `--query`.
- **PPM's base URL is unverified.** `ppm.py`'s OAI-PMH endpoint was found
  via web search, not live-tested from this environment. Run
  `ppm.py identify` first -- if it fails, see the script's module docstring
  for the alternate URL to try.
- **Pagination.** OAI-PMH sources page via an opaque `resumption_token`
  returned in the previous response -- pass it back verbatim on the next
  call, with no other search parameters (the OAI-PMH spec forbids mixing
  a resumption token with other query params). DSpace sources page via
  zero-based `--page` + `--size` (max 50). Dataverse sources (RODBuK,
  RePOD) page via `--start` (zero-based offset) + `--per-page` (max 100).
- **UUID-based lookups.** RUJ, AGH, AMU, UAFM, and ICM all require an
  item **UUID** for the `get` subcommand -- get it from the `uuid` field
  of a prior `search` call's results, not from a handle or DOI.
- **UAFM is currently down.** As documented in the upstream project (as
  of 2026-07-20), `repozytorium.uafm.edu.pl` returns HTTP 404 for
  `/server/api/*` and HTTP 500 for its Angular UI -- the DSpace backend
  appears unmounted or broken on their end. `uafm.py` is included for
  completeness and will start working again with no code changes once
  the service is restored; until then, expect an `Error: HTTP 404 ...`
  with an explanatory note appended.
- **AGH and ICM filter fallback.** Some AGH/ICM discovery filter
  combinations are known to occasionally return HTTP 400/404 from the
  upstream service. `agh.py search` and `icm.py search` automatically
  retry once with only the core `query`/`page`/`size`/`sort` params (no
  filters) if that happens, so a single bad filter doesn't hard-fail the
  whole search.
- **DSpace filter operators.** Every `--<filter>` value may embed an
  explicit operator after a trailing comma: `equals`, `notequals`,
  `contains`, `notcontains`, `authority`, `notauthority`, `query` (e.g.
  `--date-issued "[2020-01-01 TO 2023-12-31],query"` for a Solr range
  query). If omitted, each field falls back to a sensible default
  operator -- see `reference/API.md` for the full per-field table.
- **`--minimize-pii` (Biblioteka Nauki, RUJ).** Redacts ORCID-like,
  email, phone, and PESEL-like patterns, and for RUJ also drops the
  `authors`/`affiliation` fields entirely. Useful when passing results
  onward to a context where personal data shouldn't linger.
- **No API keys, but be a good citizen.** Every endpoint here is public
  and anonymous. There is no documented rate limit, but these are shared
  academic infrastructure operated by universities and research
  institutes on modest hardware -- avoid tight request loops, cache
  results locally if you need to make many repeated calls, and prefer
  larger `--page-size`/`--size` over many small requests when harvesting.
- **Network behavior.** Every request uses a 30-second timeout and
  retries exactly once on transient network failures (timeouts,
  connection reset/refused). HTTP 4xx/5xx responses are never retried --
  they surface immediately as a clear `Error: HTTP <status> ...` message
  with a short snippet of the response body.
- **Non-Dublin-Core OAI metadata formats.** RCIN and Biblioteka Nauki
  support metadata formats beyond `oai_dc` (e.g. `mets`, `oai_etdms`,
  `dlibra_avs`, `oai_qdc`, `jats`). Only `oai_dc` is parsed into clean
  per-field JSON; for the others, the record's raw `<metadata>` XML
  is preserved verbatim under `metadata.metadata_raw_xml` so no
  information is lost, but you'll need to read the XML yourself for
  format-specific structure (see Judgment calls in reference/API.md).

## Sources

- Biblioteka Nauki: https://bibliotekanauki.pl (OAI-PMH: `/api/oai/articles`, search: `/api/search`)
- RCIN: https://rcin.org.pl/dlibra (OAI-PMH: `/oai-pmh-repository.xml`)
- RUJ: https://ruj.uj.edu.pl (REST: `/server/api`)
- AGH: https://repo.agh.edu.pl (REST: `https://api.repo.agh.edu.pl/server/api`)
- AMU: https://repozytorium.amu.edu.pl (REST: `/server/api`)
- UAFM: https://repozytorium.uafm.edu.pl (REST: `/server/api`, currently down)
- ICM Open: https://open.icm.edu.pl (REST: `/server/api`)
- RODBuK: https://rodbuk.pl (REST: `/api`)
- RePOD: https://repod.icm.edu.pl (REST: `/api`)
- Depot CeON: https://depot.ceon.pl (OAI-PMH: `/oai/request`)
- PPM: https://ppm.edu.pl (OAI-PMH: `ppm.edu.pl:7443/oaicat/`, base URL unverified -- see `ppm.py` docstring)
- EMIS/ELibM: http://emis.icm.edu.pl (static site, confirmed live: no API, no search)

## Attribution

This skill's endpoint URLs, parameters, response-parsing logic, and
known caveats are derived from the open-source
[polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp)
project by [asterixix](https://github.com/asterixix), re-implemented here
as standalone, dependency-free Python scripts that need no MCP server.
