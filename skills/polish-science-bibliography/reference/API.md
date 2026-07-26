# API reference: polish-science-bibliography

Detailed parameter tables for the scripts in `../scripts/`. See `../SKILL.md`
for overview, quick-start usage, and caveats.

## PBN (`scripts/pbn.py`)

Base URL: `https://pbn.nauka.gov.pl/api/v1`

Auth headers (all PBN requests):

| Header | Source | Required |
| --- | --- | --- |
| `Accept` | fixed `application/json` | yes |
| `X-App-Id` | env `PBN_APP_ID` | yes |
| `X-App-Token` | env `PBN_APP_TOKEN` | yes |
| `X-User-Token` | env `PBN_USER_TOKEN` | no (only if set) |
| `Content-Type` | fixed `application/json` | only for POST bodies (search-publications, search-persons) |

### `search-publications` -> `POST /v1/search/publications`

| CLI flag | JSON body field | Type | Notes |
| --- | --- | --- | --- |
| `--title` | `title` | string | title fragment |
| `--doi` | `doi` | string | |
| `--isbn` | `isbn` | string | |
| `--issn` | `issn` | string | |
| `--year` | `year` | int | single year |
| `--year-from` | `yearFrom` | int | |
| `--year-to` | `yearTo` | int | |
| `--type` | `type` | enum | one of `BOOK`, `EDITED_BOOK`, `CHAPTER`, `ARTICLE`, `PROCEEDINGS` |
| `--authors` (nargs+) | `authors` | string[] | API applies AND across authors |
| `--object-id` | `objectId` | string | known PBN object id |
| `--page` | `page` | int | zero-based, default 0 |
| `--size` | `size` | int | default 20, API max 100 |

Body is pruned of `None`/empty-list fields before sending, matching the
source `prune()` helper.

### `search-persons` -> `POST /v1/search/persons`

| CLI flag | JSON body field | Type | Notes |
| --- | --- | --- | --- |
| `--first-name` | `firstName` | string | |
| `--last-name` | `lastName` | string | |
| `--orcid` | `orcid` | string | |
| `--object-id` | `objectId` | string | |
| `--page` | `page` | int | zero-based, default 0 |
| `--size` | `size` | int | default 20, API max 100 |

### `get-publication` -> `GET /v1/publications/id/{id}`

| CLI flag | Path segment | Notes |
| --- | --- | --- |
| `--id` | `{id}` (URL-encoded) | PBN Mongo object id from a search result |

No JSON body -> no `Content-Type` header sent (matches
`requirePbnHeaders(env, false)` in the source).

### Errors

- Missing `PBN_APP_ID`/`PBN_APP_TOKEN` -> printed to stderr, `exit(1)`,
  **no network call is made**.
- HTTP 401/403 -> reported as an auth error with a pointer to
  https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/
- Any other HTTP error -> status code + up to 1024 chars of response body.

---

## POL-on / RAD-on (`scripts/polon.py`)

Base URL: `https://radon.nauka.gov.pl/opendata/polon`
Header: `Accept: application/json`. No auth.

### `search` -> `GET /opendata/polon/{resource}`

`{resource}` is one of: `institutions`, `employees`, `projects`,
`publications`, `courses`, `branches` (each maps 1:1 to its own URL
segment).

Common query params (all resources):

| CLI flag | Query param | Notes |
| --- | --- | --- |
| `--result-numbers` | `resultNumbers` | default 20, API max 100 |
| `--page-token` | `token` | from a previous response's `pagination.token` |

Per-resource filters (only sent when the resource matches; irrelevant
flags are silently ignored by the script, mirroring the TS `switch`):

| Resource | CLI flag | Query param |
| --- | --- | --- |
| `institutions` | `--city` | `city` |
| `institutions` | `--voivodeship` | `voivodeship` |
| `institutions` | `--institution-name` | `name` |
| `branches` | `--city` | `city` |
| `branches` | `--voivodeship` | `voivodeship` |
| `employees` | `--first-name` | `firstName` |
| `employees` | `--last-name` | `lastName` |
| `employees` | `--discipline-name` | `disciplineName` |
| `projects` | `--project-title-pl` | `projectTitlePl` |
| `projects` | `--project-title-en` | `projectTitleEn` |
| `projects` | `--project-number` | `projectNumber` |
| `projects` | `--keywords` | `keywords` |
| `publications` | `--publication-title` | `title` |
| `publications` | `--last-name` | `lastName` (author surname) |
| `courses` | `--course-name` | `courseName` |

Response shape (raw, passed through): `results[]`,
`pagination.maxCount`, `pagination.token`.

---

## Ludzie Nauki (`scripts/ludzie_nauki.py`)

Base URL: `https://ludzie.nauka.gov.pl/api/profiles-api`
Profile page base: `https://ludzie.nauka.gov.pl/ln/profile`
Header: `Accept: application/json`. No auth.

### `search` -> `GET /v1.1/public/profile/scientistSearchData`

| CLI flag | Query param | Notes |
| --- | --- | --- |
| `--surname` | `surname` | partial match |
| `--first-name` | `firstName` | optional |
| `--domain-code` | `domainCode` | e.g. `DZ0106N` (exact sciences), `DZ0105N` (social sciences) |
| `--page` | `page` | zero-based, default 0 |
| `--size` | `size` | 1-50, default 10 |
| `--include-deceased` | `withTheDead` | `"true"`/`"false"` string, default false |

Output is summarized from the raw API response:
`totalHits`, `page.{number,size,totalInResponse}`,
`isSemanticSearchNeeded`, `filterHint`, and `profiles[]` where each
profile has `profileId`, `name` (joined from `title`+`firstName`+
`secondName`+`surname`), `institution` (`calculatedInstitutionName`),
`domainCode`, `disciplines`, `dead`, and `url`
(`{PROFILE_URL}/{profileId}`).

### `semantic-search` -> `GET /v1.0/public/profile/semanticSearchData`

| CLI flag | Query param | Notes |
| --- | --- | --- |
| `--full-query` / `--query` | `fullQuery` | required; natural-language or keyword phrase |
| `--include-deceased` | `withTheDead` | `"true"`/`"false"` string, default false |
| `--max-profiles` | (client-side truncation only) | 1-100, default 40; caps the summarized list, API may return more |

Output: `totalReturned` (full array length), `showing` (length after
truncation), `truncated` (bool), `profiles[]` (same shape as `search`).

### `get` -> 3 parallel-in-spirit GETs (sequential in this client)

| CLI flag | Endpoint |
| --- | --- |
| `--id` | `{API_BASE}/v1.0/public/profile/{id}/orcid` |
| (same id) | `{API_BASE}/v1.0/public/profile/{id}/degreesAndTitles` |
| (same id) | `{API_BASE}/v1.0/public/profile/{id}/keyWords` |

Output: `{ profileId, profileUrl, orcid, degreesAndTitles, keywords }`,
each of the three fields holding the parsed JSON from its endpoint (or
raw text if the body isn't valid JSON).
