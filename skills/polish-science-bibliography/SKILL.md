---
name: polish-science-bibliography
description: Query Polish science-bureaucracy and bibliography data - publication and researcher records in PBN (Polska Bibliografia Naukowa), open higher-education/institution datasets from POL-on / RAD-on, and researcher profiles from Ludzie Nauki (ORCID, degrees, keywords) -- Ludzie Nauki is the successor to nauka-polska.pl, which now redirects here. IMPORTANT -- for any broad "find this publication or researcher" search, run `scripts/search_all.py --query X` first: it fans the query out to PBN and Ludzie Nauki in parallel. Use when the user asks about Polish scientific publications, PBN, POL-on, RAD-on, nauka-polska, uczelnie, pracownicy naukowi, granty/projekty naukowe, naukowcy, badacze, ORCID, publikacje naukowe, or scientist/institution lookups tied to Polish public science registries. PBN tools require registered API credentials; POL-on/RAD-on and Ludzie Nauki are open, no key needed.
---

# Polish Science Bibliography

Standalone, dependency-free Python 3 scripts (standard library only) for
three Polish public/science-bureaucracy data sources:

1. **PBN** (Polska Bibliografia Naukowa) - the national scientific
   bibliography: search publications and person/author records. **Requires
   registered API credentials.**
2. **POL-on / RAD-on** - open dataset registry of higher-education and
   science institutions, staff, projects, publications, and courses. No key
   needed.
3. **Ludzie Nauki** (ludzie.nauka.gov.pl) - public registry of researcher
   profiles (name, institution, ORCID, degrees/titles, keywords). No key
   needed.

No MCP server, no pip installs. Run the scripts directly with `python3`.

**Note on nauka-polska.pl:** the historic Nauka Polska portal now redirects
to `ludzie.nauka.gov.pl` and is archival-only -- `ludzie_nauki.py` already
covers it, no separate script is needed.

## Search across every source at once

For any broad "find this publication or researcher" query, run
**`scripts/search_all.py --query "..."`** first. It fans the query out in
parallel to `pbn.py search-publications --title` and `ludzie_nauki.py
semantic-search --full-query`, returning one combined JSON. PBN errors
cleanly (and search_all reports it as a per-source failure) if
`PBN_APP_ID`/`PBN_APP_TOKEN` aren't set. POL-on/RAD-on is structured-filter
only (institution/employee/project/publication fields, no free text) --
call `polon.py` directly instead.

```bash
python3 scripts/search_all.py --query "Magdalena Wójcik"
```

## Scripts and subcommands

| Script | Subcommand | Mirrors original tool | Endpoint |
| --- | --- | --- | --- |
| `scripts/search_all.py` | `--query` | *(new -- not from the MCP port)* | Fans out to PBN + Ludzie Nauki in parallel |
| `scripts/pbn.py` | `search-publications` | `pbn_search_publications` | `POST /v1/search/publications` |
| `scripts/pbn.py` | `search-persons` | `pbn_search_persons` | `POST /v1/search/persons` |
| `scripts/pbn.py` | `get-publication` | `pbn_get_publication` | `GET /v1/publications/id/{id}` |
| `scripts/polon.py` | `search` | `polon_search` | `GET /opendata/polon/{resource}` |
| `scripts/ludzie_nauki.py` | `search` | `ludzie_search` | `GET /v1.1/public/profile/scientistSearchData` |
| `scripts/ludzie_nauki.py` | `semantic-search` | `ludzie_semantic_search` | `GET /v1.0/public/profile/semanticSearchData` |
| `scripts/ludzie_nauki.py` | `get` | `ludzie_get_scientist` | ORCID + degreesAndTitles + keyWords (3 GETs) |

All scripts print the final result as pretty JSON on stdout
(`json.dumps(..., ensure_ascii=False, indent=2)`) and exit 0 on success, or
print a clear error to stderr and `exit(1)` on failure. Full parameter
tables are in `reference/API.md`.

## PBN usage (requires credentials)

PBN endpoints need institutional credentials, sent as headers `X-App-Id`
and `X-App-Token` (matching the original TS server's `requirePbnHeaders`).
An optional user-context header `X-User-Token` is added when present.

Environment variables (read via `os.environ`, never hardcoded):

- `PBN_APP_ID` (required)
- `PBN_APP_TOKEN` (required)
- `PBN_USER_TOKEN` (optional)

If `PBN_APP_ID` or `PBN_APP_TOKEN` is missing, the script prints a
help message and **exits 1 before making any network call**:

```
$ python3 scripts/pbn.py get-publication --id 5e70999e878c28a04737dd5f
PBN API requires PBN_APP_ID and PBN_APP_TOKEN environment variables
(optionally PBN_USER_TOKEN for user-context operations).
Get access: https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/
Details: https://pbn.nauka.gov.pl/centrum-pomocy/baza-wiedzy/sposob-uzyskania-dostepu-do-api-w-wersji-produkcyjnej/
```

With credentials set:

```bash
export PBN_APP_ID="your-app-id"
export PBN_APP_TOKEN="your-app-token"
# optional: export PBN_USER_TOKEN="your-user-token"

python3 scripts/pbn.py search-publications --title "grafen" --year-from 2018 --year-to 2023 --type ARTICLE --size 20
python3 scripts/pbn.py search-persons --last-name "Kowalski" --orcid "0000-0002-1234-5678"
python3 scripts/pbn.py get-publication --id 5e70999e878c28a04737dd5f
```

A 401/403 response from PBN is reported as an authentication/authorization
error with a pointer back to the credential-registration docs.

## POL-on / RAD-on usage (open, no key)

```bash
python3 scripts/polon.py search --resource institutions --city Kraków --result-numbers 20
python3 scripts/polon.py search --resource employees --last-name Nowak --discipline-name astronomia
python3 scripts/polon.py search --resource projects --project-title-pl "sztuczna inteligencja"
python3 scripts/polon.py search --resource publications --publication-title "uczenie maszynowe"
python3 scripts/polon.py search --resource courses --course-name informatyka
python3 scripts/polon.py search --resource branches --voivodeship mazowieckie
```

The response is raw JSON with `results[]` and `pagination.{maxCount,token}`.
To fetch the next page, pass the previous response's `pagination.token`
back in as `--page-token`:

```bash
python3 scripts/polon.py search --resource institutions --city Kraków --page-token "<token from previous response>"
```

`--result-numbers` (maps to the API's `resultNumbers`) caps out at 100 per
request, matching the source tool's limit.

## Ludzie Nauki usage (open, no key)

```bash
# Browse/filter profiles (page/size are zero-based / 1-50)
python3 scripts/ludzie_nauki.py search --surname Kowalski --domain-code DZ0106N --page 0 --size 10

# Free-text / semantic search over research topics
python3 scripts/ludzie_nauki.py semantic-search --query "uczenie maszynowe" --max-profiles 20

# Fetch one profile's ORCID, degrees/titles, and keywords
python3 scripts/ludzie_nauki.py get --id jhMVc1vG5Yz
```

`search` and `semantic-search` results are summarized (not the full raw
API payload) to keep output compact, matching the original tool's
behavior: `profileId`, `name`, `institution`, `domainCode`, `disciplines`,
`dead`, and a direct `url` to `https://ludzie.nauka.gov.pl/ln/profile/{id}`
for each profile. Use `--include-deceased` to include profiles marked as
deceased (`withTheDead=true`).

## Caveats

- **PBN requires registered API access.** Search and metadata endpoints
  need `PBN_APP_ID` + `PBN_APP_TOKEN` issued after registering an
  application with PBN Helpdesk. See:
  https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/
  and https://pbn.nauka.gov.pl/centrum-pomocy/kategoria/api/. Without
  valid credentials, every PBN subcommand fails fast with a clear message
  and no network call is made.
- **POL-on / RAD-on and Ludzie Nauki are fully open** - no API key,
  registration, or auth headers required.
- Network policy for all scripts: 30-second timeout per attempt, one
  automatic retry only on transient network errors (connection reset,
  timeout, DNS hiccups); HTTP 4xx/5xx responses are never retried and are
  surfaced immediately with the status code and a short body snippet.
- Ludzie Nauki registry data is refreshed periodically; treat results as
  a snapshot, not real-time.
- PBN and POL-on/RAD-on server-side filters expect accurate Polish
  strings (diacritics matter for exact matches in some fields).

## Sources

- PBN Swagger: https://pbn.nauka.gov.pl/api/
- PBN help center: https://pbn.nauka.gov.pl/centrum-pomocy/kategoria/api/
- POL-on / RAD-on Open Data: https://radon.nauka.gov.pl/opendata/polon
- POL-on / RAD-on data catalog: https://radon.nauka.gov.pl/pomoc/knowledge-base/katalog-udostepnianych-danych-api/
- Ludzie Nauki: https://ludzie.nauka.gov.pl

## Attribution

Content and logic derived from
[polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp) by
asterixix (`src/tools/pbn.ts`, `src/tools/polon.ts`,
`src/tools/ludzie-nauki.ts`), re-implemented here as standalone,
dependency-free scripts with no MCP server required.
