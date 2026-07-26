# Polish Academic Repositories -- API Reference

Detailed per-source parameter tables, endpoint shapes, and judgment calls
made while porting these tools from the original
[polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp)
TypeScript/MCP implementation into standalone Python scripts. See
`../SKILL.md` for the overview, quick-start, and general caveats.

All scripts live in `../scripts/` and share `_http.py` (HTTP fetch with a
30s timeout and one retry on transient network errors only, DSpace filter
helpers, OAI-PMH XML parsing, Dublin Core accessors, and PII scrubbing).

---

## Biblioteka Nauki (`scripts/biblioteka_nauki.py`)

Base URLs:
- OAI-PMH: `https://bibliotekanauki.pl/api/oai/articles`
- Search API (JSON): `https://bibliotekanauki.pl/api/search`

### `search-publications` (full-text, JSON search API)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--query` | string | required | Search phrase (PL/EN). Maps to `generalSearchString`. |
| `--page` | int | 1 | 1-based page number. |
| `--page-size` | int | 10 | Max 50. |
| `--sort-field` | `score` \| `publishedDate` | `score` | |
| `--sort-direction` | `ASC` \| `DESC` | `DESC` | |
| `--publication-types` | one or more of `ARTICLE`, `SIMPLE_BOOK`, `COLLECTIVE_WORK`, `CHAPTER` | none | Omit to search all types. |
| `--published-date-from` / `--published-date-to` | `YYYY-MM-DD` | none | Inclusive bounds. |
| `--open-resources` | flag | off | Prefer open/diamond-open-access resources. |

Sends a POST with body `{"searchCriteria": {...}, "paginationCriteria": {...}}`
identical in shape to the public web UI's own search call. Response is the
raw JSON from the search API, pretty-printed (hits, `mainTitleSnippets`,
`fullTextSnippets`, `totalResults`).

### `search-articles` (OAI-PMH ListRecords -- harvesting, not keyword search)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--from-date` / `--until-date` | `YYYY-MM-DD` | none | OAI datestamp bounds. |
| `--set` | string | none | OAI setSpec (journal/discipline identifier). |
| `--metadata-format` | `oai_dc` \| `jats` | `oai_dc` | `jats` includes abstracts/keywords/references but is not Dublin Core -- parsed output falls back to `metadata.metadata_raw_xml`. |
| `--resumption-token` | string | none | From a previous response, to continue paging. When set, no other params are sent (per the OAI-PMH spec). |
| `--minimize-pii` | flag | off | Redacts ORCID/email/phone/PESEL-like patterns from the final JSON. |

**Robustness fallback** (ported as-is): if a `--set` filter combined with a
date range yields `noRecordsMatch`, the tool retries once automatically
without the `set` param, so an overly narrow set doesn't silently return
nothing when the date range alone would have hits.

### `get-article` (OAI-PMH GetRecord by numeric ID)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--article-id` | string | required | Numeric ID from search results, e.g. `1968869`. |
| `--metadata-format` | `jats` \| `oai_dc` | `jats` | `jats` recommended -- fuller structured metadata. |

Identifier sent to OAI-PMH is built as `oai:bibliotekanauki.pl:<article_id>`.

---

## RCIN (`scripts/rcin.py`)

Base URL: `https://rcin.org.pl/oai-pmh-repository.xml` (OAI-PMH 2.0).
This is metadata harvesting only -- the interactive full-text search UI at
`https://rcin.org.pl/dlibra/` has no public API.

### `search` (ListRecords)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--from-date` / `--until-date` | `YYYY-MM-DD` | none | |
| `--set` | string | none | e.g. `rcin.org.pl:literature`. Omit for all sets. |
| `--metadata-format` | `oai_dc` \| `oai_qdc` \| `mets` \| `oai_etdms` \| `dlibra_avs` | `oai_dc` | Only `oai_dc` is parsed into per-field JSON; others fall back to raw XML under `metadata.metadata_raw_xml` (`oai_qdc` = qualified Dublin Core, `mets` = METS, `oai_etdms` = theses/dissertations schema, `dlibra_avs` = dLibra attribute schema). |
| `--resumption-token` | string | none | Continue a previous harvest. |

### `get` (GetRecord)

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--id` | string | required | Numeric id (e.g. `204728`) or full OAI identifier (`oai:rcin.org.pl:204728`). Bare numeric ids are normalized to the full OAI form automatically. |
| `--metadata-format` | same 5 choices as above | `oai_dc` | |

---

## RUJ -- Jagiellonian University Repository (`scripts/ruj.py`)

Base URL: `https://ruj.uj.edu.pl/server/api` (DSpace 7, HAL+JSON, anonymous
read). Search always goes through `/discover/search/objects` --
`/core/items` (list-all) is admin-only and never used here.

### `search`

| Flag | Default op | Notes |
|---|---|---|
| `--query` (required) | -- | Full-text expression. |
| `--page` (default 0) / `--size` (default 10, max 50) | -- | Zero-based page. |
| `--sort` | -- | One of `score,desc`, `dc.title,asc/desc`, `dc.date.issued,asc/desc`, `dc.date.accessioned,asc/desc`. Default `score,desc`. |
| `--itemtype` | `equals` | E.g. `JournalArticle`, `Book`, `BookSection`, `JournalEditorship`. |
| `--author` | `contains` | |
| `--subject` | `equals` | |
| `--language` | `equals` | e.g. `pl`, `en`. |
| `--affiliation` | `contains` | Author institutional affiliation. |
| `--affiliation-em` | `contains` | Corresponding-author affiliation (`affiliationEm`). |
| `--journal-title` | `contains` | |
| `--subtype` | `equals` | |
| `--entity-type` | `equals` | DSpace `entityType`. |
| `--pbn-discipline` | `equals` | PBN scientific discipline (`pbndiscipline`). |
| `--has-full-text` | -- | `true`/`false`. Maps to `f.has_content_in_original_bundle`. |
| `--date-issued` | `equals` | For ranges use the `query` operator with Solr notation: `"[2020-01-01 TO 2023-12-31],query"`. |
| `--date-accessioned` | `equals` | |
| `--date-submitted` | `equals` | |
| `--minimize-pii` | -- | Drops `authors`/`affiliation` fields and scrubs PII patterns. |

Every filter value may embed its own operator after a trailing comma
(`equals`, `notequals`, `contains`, `notcontains`, `authority`,
`notauthority`, `query`) -- if present, it overrides the default op shown
above.

Output item fields: `uuid`, `handle`, `url`, `title`, `titleAlt`, `authors`,
`type`, `language`, `dateIssued`, `dateSubmitted`, `affiliation`, `subject`,
`abstract` (truncated to 500 chars, preferring English then Polish
`dc.abstract.*`).

### `get`

| Flag | Notes |
|---|---|
| `--uuid` (required) | From a prior `search` result's `uuid` field. |

Output fields: `uuid`, `handle`, `url`, `title`, `titleAlt`, `authors`,
`advisors`, `reviewers`, `type`, `language`, `dateIssued`, `dateSubmitted`,
`dateAccessioned`, `affiliation`, `fieldOfStudy`, `area`, `subjectEN`,
`subjectPL`, `doi`, `identifierURI`, `entityType`, `inArchive`,
`lastModified`, `abstractEN`, `abstractPL`.

---

## AGH -- AGH University of Krakow Repository (`scripts/agh.py`)

Base URL: `https://api.repo.agh.edu.pl/server/api` (note: the JSON HAL API
is on the `api.` subdomain -- `repo.agh.edu.pl/server/api` serves the
Angular SPA's HTML, not REST).

### `search`

| Flag | Default op |
|---|---|
| `--query` (required), `--page` (0), `--size` (10, max 50), `--sort` | -- |
| `--author` | `contains` |
| `--subject` | `equals` |
| `--language` | `equals` |
| `--itemtype` | `equals` -- common values: `Thesis`, `Article`, `Book`, `Technical Report`. |
| `--date-issued` | `equals` (or `query` op for Solr ranges) |
| `--date-accessioned` | `equals` |
| `--has-full-text` | `true`/`false` -> `f.has_content_in_original_bundle` |

**Filter-combo fallback:** if the filtered request returns HTTP 400 or 404
(some AGH discovery filter combinations are known to error), the tool
automatically retries once with only `query`/`page`/`size`/`sort` (no
filters at all) so the search stays usable.

Output item fields: `uuid`, `handle`, `url`, `title`, `titleAlt`, `authors`,
`type`, `language`, `dateIssued`, `dateSubmitted`, `publisher`, `subject`,
`abstract` (truncated to 500 chars from `dc.description.abstract`).

### `get`

Same `--uuid` pattern. Output adds: `advisors`, `dateAccessioned`, `doi`,
`identifierURI`, `subjects` (all values), `description`, `entityType`,
`inArchive`, `lastModified`, `abstract`.

---

## AMU -- Adam Mickiewicz University Repository (`scripts/amu.py`)

Base URL: `https://repozytorium.amu.edu.pl/server/api`.

### `search`

| Flag | Default op |
|---|---|
| `--query` (required), `--page` (0), `--size` (10, max 50), `--sort` | -- |
| `--author` | `contains` |
| `--subject` | `equals` |
| `--title` | `contains` |
| `--date-issued` | `equals` (or `query` for Solr ranges) |
| `--entity-type` | `equals` -- e.g. `Item`, `Publication`. |
| `--has-full-text` | `true`/`false` |

No filter-combo fallback (unlike AGH/ICM) -- AMU's discovery endpoint
doesn't exhibit the same known issue in the source project.

Output item fields: `uuid`, `handle`, `url` (falls back to `/items/<uuid>`
if no handle is assigned yet), `title`, `authors`, `type`, `language`,
`dateIssued`, `subject`, `abstract` (truncated 500 chars).

### `get`

Adds: `subject` (all values), `doi`, `uri`, `publisher`, `entityType`,
`lastModified`, `abstract`.

---

## UAFM -- Repozytorium eRIKA (`scripts/uafm.py`)

Base URL: `https://repozytorium.uafm.edu.pl/server/api` (DSpace 8).

**Known outage:** as documented in the source TypeScript file (dated
2026-07-20), this backend returns HTTP 404 for all `/server/api/*` paths
and HTTP 500 for its Angular UI. The tool is preserved as-is -- once the
service is restored, no code changes are needed. Every error from this
script appends an explanatory note about the outage (mirroring the
upstream tool's behavior of always attaching that context, regardless of
the specific HTTP status returned).

### `search`

| Flag | Default op |
|---|---|
| `--query` (required), `--page` (0), `--size` (10, max 50), `--sort` | -- |
| `--author` | `contains` |
| `--title` | `contains` |
| `--subject` | `equals` |
| `--keyword` | `equals` |
| `--itemtype` | `equals` -- e.g. `article`, `book`. |
| `--date-issued` | `equals` (or `query` for Solr ranges) |
| `--date-accessioned` | `equals` |
| `--license` | `contains` -- e.g. `CC BY`. |
| `--has-full-text` | `true`/`false` |

Output item fields: `uuid`, `handle`, `url`, `title`, `authors`, `type`,
`language`, `dateIssued`, `subject`, `abstract`.

### `get`

Adds: `dateAccessioned`, `subject` (all values), `doi`, `uri`, `publisher`,
`license` (from `dc.rights`), `lastModified`, `abstract`.

---

## ICM -- Open Research Data Repository (`scripts/icm.py`)

Base URL: `https://open.icm.edu.pl/server/api` (University of Warsaw).

### `search`

| Flag | Default op |
|---|---|
| `--query` (required), `--page` (0), `--size` (10, max 50), `--sort` | -- |
| `--author` | `contains` |
| `--title` | `contains` |
| `--subject` | `equals` |
| `--publisher` | `contains` |
| `--affiliation` | `contains` |
| `--license` | `contains` -- e.g. `CC BY`. |
| `--date-issued` | `equals` (or `query` for Solr ranges) |
| `--has-full-text` | `true`/`false` |

**Filter-combo fallback:** identical to AGH -- HTTP 400/404 on a filtered
query triggers one automatic retry with filters stripped.

Output item fields: `uuid`, `handle`, `url`, `title`, `authors`, `type`,
`language`, `dateIssued`, `publisher`, `subject`, `license`, `abstract`.

### `get`

Adds: `publisher`, `affiliation`, `subject` (all values), `doi`, `uri`,
`license`, `entityType`, `lastModified`, `abstract`.

---

## RODBuK (`scripts/rodbuk.py`)

Base URL: `https://rodbuk.pl/api` -- Harvard Dataverse-powered, six member
universities (AGH, UEK, UP, UR, UJ, PK). All read endpoints anonymous.

### `search`

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--query` | string | required | Use `*` to browse all available collections. |
| `--type` | `dataset` \| `dataverse` \| `file` | none | Restrict to one content type. |
| `--per-page` | int | 10 | Max 100. |
| `--start` | int | 0 | Zero-based offset. |

Output: `{query, total_count, start, items: [{title, author, date, doi,
url, type, abstract, source_raw}]}`. `doi` has the `doi:` prefix stripped
if present; `source_raw` preserves the untouched Dataverse item for
anything not surfaced in the flattened fields.

---

## RePOD (`scripts/repod.py`)

Base URL: `https://repod.icm.edu.pl/api` -- a CeON fork of Dataverse
(branched from v4.11), ~3,737 datasets, all DOIs under the `10.18150/`
prefix. Some Dataverse v5+/v6+ features (geo_point search, Croissant
metadata) may be unavailable due to the fork's age.

### `search`

Same shape as RODBuK's `search` (identical flags and output shape).

### `get-dataset`

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--doi` | string | required | DOI without the `doi:` prefix, e.g. `10.18150/ABCDEF`. |
| `--format` | `datacite` \| `dcterms` \| `schema.org` \| `ddi` \| `dataverse_json` | `datacite` | Metadata export format. |

Fetches `GET /api/datasets/export?exporter=<format>&persistentId=doi:<doi>`.
Output wraps the body as `{"requested_format": ..., "content": ...}` --
`content` is parsed JSON when the body is JSON/JSON-LD (`schema.org`,
`dataverse_json`), or left as a raw XML string otherwise (`datacite`,
`dcterms`, `ddi` are XML/RDF formats).

**Fallback:** if the export endpoint returns HTTP 400/404 (an
intermittent known issue for otherwise-valid datasets), the tool
automatically fetches `GET /api/datasets/:persistentId/versions/:latest`
instead and returns `{"requested_format", "fallback_format":
"dataverse_json", "note": "...", "dataset": {...}}`.

---

## Judgment calls made while porting

The original MCP tools for the OAI-PMH sources (Biblioteka Nauki's
`search-articles`/`get-article`, and both RCIN tools) return **raw,
unparsed XML** as their text output -- the TypeScript Worker deliberately
avoids DOM/XML parsing to stay lightweight. This port instead parses the
OAI-PMH envelope and `oai_dc` Dublin Core metadata into clean per-field
JSON dictionaries (see `_http.parse_oai_pmh` in `scripts/_http.py`), since
plain Python scripts run locally have no such constraint and structured
JSON is far more useful to a calling model than an XML blob dumped as a
JSON string. The *set of information exposed* is preserved -- nothing
from the original OAI-PMH response is dropped:

- All Dublin Core fields are extracted for `oai_dc` (the default and by
  far the most common format requested).
- For every *other* metadata format (`jats`, `mets`, `oai_etdms`,
  `dlibra_avs`, `oai_qdc`) -- none of which are Dublin Core, and each of
  which has its own non-trivial XML schema -- full structural parsing was
  judged out of scope for a faithful, low-risk port. Instead, the raw
  `<metadata>` XML for that record is preserved verbatim under
  `metadata.metadata_raw_xml`, so no information is lost; only the
  convenience of flat JSON fields is unavailable for those formats.
- OAI-PMH `<error>` responses (e.g. `noRecordsMatch`, `idDoesNotExist`,
  `badArgument`) are surfaced as `{"error": "<code>", "message": "..."}`
  rather than raising, matching the informational (non-fatal) nature of
  `noRecordsMatch` in particular.

`repod.py get-dataset`'s wrapping of non-JSON export formats
(`datacite`/`dcterms`/`ddi` are XML) as a JSON string value, rather than
attempting to parse those XML schemas too, follows the same reasoning --
it keeps the port simple and low-risk while still always emitting valid
JSON on stdout as required.
