# API Reference

Detailed parameter reference for `scripts/dane_gov_pl.py` and `scripts/bdl.py`.
See `SKILL.md` for quick-start usage examples.

## dane.gov.pl (`dane_gov_pl.py`)

Base URL: `https://api.dane.gov.pl/1.4`. No API key required. API docs:
<https://api.dane.gov.pl/doc> (Swagger UI).

### `search` (dane_search) -> `GET /datasets`

| Flag | Type | Required | Default | Notes |
|---|---|---|---|---|
| `--query` | string | yes | -- | Full-text search phrase (`q` param). |
| `--category` | string | no | none | DCAT category name or id, e.g. "Nauka i technika", "Edukacja", "Zdrowie", "Transport". If the value causes an HTTP 400 (label vs. id mismatch), the script automatically retries once without the category filter. |
| `--per-page` | int | no | 20 | 1-100 results per page. |
| `--page` | int | no | 1 | **1-based** page number. |
| `--sort` | enum | no | `relevance` | One of `relevance`, `date`, `-date` (newest first), `title`, `views_count`. |

Response includes dataset title, category, license (mostly CC0), owning
institution, and download/view stats. Datasets flagged `has_research_data:
true` are specifically academic in nature.

### `get` (dane_get_dataset) -> `GET /datasets/{id}` + `GET /datasets/{id}/resources`

| Flag | Type | Required | Notes |
|---|---|---|---|
| `--id` | int | yes | Numeric dataset id, taken from the `id` field of a `search` result. |

Fetches both the dataset detail and its resources list, then merges them
into a single JSON object: `{"dataset": {...}, "resources": {...}}`.
Resources include downloadable formats (CSV, XLSX, JSON) and any API links.

## BDL -- Bank Danych Lokalnych (`bdl.py`)

Base URL: `https://bdl.stat.gov.pl/api/v1`. REST docs:
<https://bdl.stat.gov.pl/api/v1/> . OpenAPI/Swagger spec:
`https://bdl.stat.gov.pl/api/v1/swagger/doc/swagger.json`. All list
endpoints use **0-based** pagination. Anonymous access works; set
`BDL_CLIENT_ID` env var for the `X-ClientId` header (higher rate limit,
register at <https://api.stat.gov.pl/home/bdlapi>).

Common flags across all BDL subcommands:

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--lang` | `pl` \| `en` | `pl` | Response language. |
| `--page` | int | 0 | Zero-based page index. |
| `--page-size` | int | 20 | 1-100 results per page. |

### `search-subjects` (bdl_search_subjects) -> `GET /subjects/search`

| Flag | Type | Required | Notes |
|---|---|---|---|
| `--name` | string | yes | Subject name fragment (in the language given by `--lang`). |
| `--sort` | string | no | One of: `Id`, `-Id`, `Id,Name`, `Id,-Name`, `-Id,Name`, `-Id,-Name`, `Name`, `-Name`, `Name,Id`, `Name,-Id`, `-Name,Id`, `-Name,-Id`. |

Returns subject id, name, child subject ids, and levels. Use this to
discover subject ids (e.g. `P1312` for demographic subjects) before
searching variables.

### `search-variables` (bdl_search_variables) -> `GET /variables/search`

| Flag | Type | Required | Notes |
|---|---|---|---|
| `--name` | string | no | Text matched in the variable's N1..N5 label fields. |
| `--subject-id` | string | no | Parent subject id from `search-subjects` (e.g. `P1312`). |
| `--level` | int | no | Territorial or variable level filter, when applicable. |
| `--years` | int list | no | Space-separated years, e.g. `--years 2020 2021 2022`. Sent as repeated `year=` query params. |
| `--sort` | string | no | One of: `Id`, `-Id`, `Id,SubjectId`, `Id,-SubjectId`, `-Id,SubjectId`, `-Id,-SubjectId`, `SubjectId`, `-SubjectId`, `SubjectId,Id`, `SubjectId,-Id`, `-SubjectId,Id`, `-SubjectId,-Id`. |

Returns a numeric variable id used by `get-variable`,
`get-data-by-variable`, and `get-data-by-unit`.

### `search-units` (bdl_search_units) -> `GET /units/search`

| Flag | Type | Required | Notes |
|---|---|---|---|
| `--name` | string | no | Unit name fragment (city, powiat, or województwo name). |
| `--levels` | int list | no | TERYT level filters, space-separated. Common levels: `0` = country, `1` = region (makroregion), `2` = województwo, `3` = podregion, `4` = powiat, `5` = gmina. Check the BDL `/levels` endpoint if unsure. |
| `--years` | int list | no | Years for which the unit definition should exist (unit boundaries/codes change over time). |
| `--sort` | string | no | Same enum as `search-subjects --sort`. |

Returns unit id (a TERYT-style code string), name, and level -- used as
`--unit-id` in `get-data-by-unit`.

### `get-variable` (bdl_get_variable) -> `GET /variables/{id}`

| Flag | Type | Required | Notes |
|---|---|---|---|
| `--id` | int | yes | Variable id (from `search-variables`). Maps to `--variable-id` internally. |

Returns full variable metadata: measure unit, subject path, source,
available levels/years.

### `get-data-by-variable` (bdl_get_data_by_variable) -> `GET /data/by-variable/{var-id}`

| Flag | Type | Required | Default | Notes |
|---|---|---|---|---|
| `--variable-id` | int | yes | -- | Variable id. |
| `--years` | int list | no | all available | Space-separated calendar years. |
| `--unit-level` | int | no | none | BDL territorial level (e.g. `2` = województwo). |
| `--unit-parent-id` | string | no | none | Restrict to descendants of this parent unit id (e.g. a województwo code, to get its powiats). |
| `--aggregate-id` | int | no | 1 | Aggregation level id. |

Use `--unit-level 2` with no `--unit-parent-id` to get every voivodeship's
value for a variable in one call.

### `get-data-by-unit` (bdl_get_data_by_unit) -> `GET /data/by-unit/{unit-id}`

| Flag | Type | Required | Default | Notes |
|---|---|---|---|---|
| `--unit-id` | string | yes | -- | Territorial unit id from `search-units`. |
| `--variable-ids` | int list | yes (min 1) | -- | One or more variable ids, space-separated. Sent as repeated `var-id=` query params. |
| `--years` | int list | no | all available | Space-separated calendar years. |
| `--aggregate-id` | int | no | 1 | Aggregation level id. |

### Query parameter naming quirk

The upstream BDL API is inconsistent in its own param naming: most
multi-word params use hyphens (`page-size`, `unit-level`, `unit-parent-id`,
`var-id`), but the aggregation parameter is `aggregate_id` with an
underscore. `bdl.py` reproduces this exactly (verified against the
`aggregate_id` key built via `URLSearchParams` in the original `bdl.ts`
source) so requests match what the API actually expects.

## Error handling

Both scripts share `scripts/_http.py`:

- 30-second timeout per request (`urlopen(req, timeout=30)`).
- One automatic retry, but only for transient network failures (timeouts,
  connection reset/refused, unreachable network) -- never for HTTP 4xx/5xx.
- On any unrecoverable failure, the script prints `Error: <message>` to
  stderr (including HTTP status and a response-body snippet when available)
  and exits with status `1`.
- On success, prints the parsed JSON result via
  `json.dumps(result, ensure_ascii=False, indent=2)` to stdout.
