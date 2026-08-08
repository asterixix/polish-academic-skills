---
name: polish-open-data-statistics
description: Search and fetch Polish government open data and official regional statistics without an MCP server. Covers dane.gov.pl (dane otwarte, the national open data portal) and GUS's Bank Danych Lokalnych / BDL (statystyka publiczna, TERYT territorial units, województwa, wskaźniki statystyczne, demografia, ludność) -- BDL is the machine-readable API behind stat.gov.pl's own published figures. IMPORTANT -- for any broad topic search, run `scripts/search_all.py --query X` first: it fans the query out to both sources in parallel. Use for "open data Poland", "GUS statistics", "local data bank", "dane.gov.pl", "BDL", "stat.gov.pl", "statystyka regionalna".
---

# Polish Open Data & Statistics

Standalone, dependency-free scripts for two Polish public-data sources, ported
from the `polish-academic-mcp` MCP server's `dane.ts` and `bdl.ts` tools. No
MCP server, API keys, or third-party Python packages required -- everything
runs with the Python 3 standard library (`urllib`, `json`, `argparse`).

## Sources

| Source | What it is | Base URL |
|---|---|---|
| **dane.gov.pl** | Poland's national open data portal: 43,000+ datasets from 500+ public institutions (ministries, local government, agencies). No API key. | `https://api.dane.gov.pl/1.4` |
| **BDL (Bank Danych Lokalnych)** | GUS (Statistics Poland) regional/national statistics database: subjects, variables, territorial units (TERYT), and time-series data values. Works anonymously; optional client id for higher rate limits. This is the machine-readable API behind the figures published on the main **stat.gov.pl** site -- there is no separate general-purpose API for stat.gov.pl itself. | `https://bdl.stat.gov.pl/api/v1` |

## Search across every source at once

For any broad topic query, run **`scripts/search_all.py --query "..."`**
first. It fans the query out in parallel to dane.gov.pl (full-text dataset
search) and BDL (subject-tree name match), returning one combined JSON.
BDL's result is only the first hop -- a matching subject id -- drill into
`bdl.py search-variables --subject-id <id>` and then `data-by-variable` to
get actual statistics.

```bash
python3 scripts/search_all.py --query "ludność"
```

## Scripts

### `scripts/search_all.py` -- cross-source fan-out *(new -- not from the MCP port)*

Runs `dane_gov_pl.py search` and `bdl.py search-subjects` as parallel
subprocesses and merges their JSON output. See "Search across every source
at once" above.

### `scripts/dane_gov_pl.py`

| Subcommand | Original tool | Description |
|---|---|---|
| `search` | `dane_search` | Full-text search across all dane.gov.pl datasets. |
| `get` | `dane_get_dataset` | Fetch a dataset's full detail plus its downloadable resources (CSV, XLSX, JSON, API links, etc.), merged into one JSON object. |

### `scripts/bdl.py`

| Subcommand | Original tool | Description |
|---|---|---|
| `search-subjects` | `bdl_search_subjects` | Search the BDL thematic subject tree by name fragment. |
| `search-variables` | `bdl_search_variables` | Search statistical variables by name text, subject id, level, and/or years. |
| `search-units` | `bdl_search_units` | Search territorial units (województwa, powiaty, gminy) by name, level, year. |
| `get-variable` | `bdl_get_variable` | Fetch metadata for one variable by its numeric id. |
| `get-data-by-variable` | `bdl_get_data_by_variable` | Fetch values for one variable across a set of territorial units (e.g. all voivodeships). |
| `get-data-by-unit` | `bdl_get_data_by_unit` | Fetch values for one territorial unit across one or more variables. |

Both scripts print the final JSON result via
`json.dumps(result, ensure_ascii=False, indent=2)` on success, and on failure
print `Error: ...` to stderr and exit with status 1.

## Usage examples

Search dane.gov.pl for datasets about air quality:

```bash
python3 scripts/dane_gov_pl.py search --query "jakość powietrza" --per-page 10
```

Search with a category filter (falls back automatically to an unfiltered
search if the category value causes an HTTP 400, since category can be a
label or an id depending on the dataset):

```bash
python3 scripts/dane_gov_pl.py search --query "edukacja" --category "Edukacja" --sort -date
```

Fetch a specific dataset's detail and resources by numeric id (the `id`
field from a `search` result):

```bash
python3 scripts/dane_gov_pl.py get --id 12345
```

Find the BDL subject id for population statistics ("ludność"):

```bash
python3 scripts/bdl.py search-subjects --name "ludność" --page-size 10
```

Find a statistical variable under that subject, e.g. population count:

```bash
python3 scripts/bdl.py search-variables --name "ludność" --subject-id P1312
```

Look up the unit id for a voivodeship (e.g. Mazowieckie), then pull that
variable's value for it and every other voivodeship (unit level 2):

```bash
python3 scripts/bdl.py search-units --name "mazowieckie" --levels 2
python3 scripts/bdl.py get-data-by-variable --variable-id 72305 --unit-level 2 --years 2022 2023
```

Get several variables at once for one specific unit (by TERYT-style id):

```bash
python3 scripts/bdl.py get-data-by-unit --unit-id "020000000000" --variable-ids 72305 72306 --years 2023
```

Get metadata for a variable (units, source, category path):

```bash
python3 scripts/bdl.py get-variable --id 72305
```

## Notes

- **`BDL_CLIENT_ID` (optional env var).** BDL works anonymously out of the
  box. If you have a client id, export it and `bdl.py` will automatically
  send it as the `X-ClientId` header for higher rate limits:

  ```bash
  export BDL_CLIENT_ID="your-client-id"
  python3 scripts/bdl.py search-subjects --name "ludność"
  ```

  Register a client id at <https://api.stat.gov.pl/home/bdlapi>. Full BDL
  REST docs: <https://bdl.stat.gov.pl/api/v1/> (OpenAPI spec at
  `.../swagger/doc/swagger.json`).

- **Pagination differs between the two sources.** dane.gov.pl's `search` is
  1-based (`--page 1` is the first page); BDL's subcommands are all
  0-based (`--page 0` is the first page). This matches each upstream API.

- **BDL query param quirk.** The upstream BDL API expects `aggregate_id`
  with an underscore, while most other multi-word BDL params (`page-size`,
  `unit-level`, `var-id`, `unit-parent-id`) use hyphens. `bdl.py` reproduces
  this exactly, verified against the source TypeScript implementation.

- **Network policy.** Both scripts use a 30-second timeout per request and
  retry once on transient network errors only (timeouts, connection
  reset/refused, unreachable network). HTTP 4xx/5xx responses are never
  retried and surface as a clear `RuntimeError` with the status code and a
  response body snippet.

- **No caching.** Unlike the original MCP server (which cached responses for
  1 hour via Cloudflare KV), these standalone scripts always hit the network
  live. Cache results yourself if you're calling repeatedly in a loop.

- See `reference/API.md` for the full parameter reference (levels, sort
  enums, TERYT notes) if you need more detail than the examples above.

## Attribution

Ported from the `dane.ts` and `bdl.ts` tools in
[asterixix/polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp),
an MCP server for Polish academic and public data sources, by asterixix.
