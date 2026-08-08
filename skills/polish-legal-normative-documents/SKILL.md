---
name: polish-legal-normative-documents
description: Search and fetch Polish legal acts, parliamentary library catalog records, court judgments, and technical/industry standards without an MCP server. Covers ISAP/ELI (akty prawne, Dziennik Ustaw, Monitor Polski, ustawy, rozporządzenia), Biblioteka Sejmowa OPAC catalog, SAOS (orzeczenia sądowe, court judgments), PKN website search, and WIEDZA-PKN Polish Standards (normy, PN-EN ISO). IMPORTANT -- for any broad topic search, run `scripts/search_all.py --query X` first: it fans the query out to all five sources in parallel. Use for "Polish legal acts", "ISAP", "ELI", "Dziennik Ustaw", "akty prawne", "court judgments", "SAOS", "orzeczenia sądowe", "Biblioteka Sejmowa", "PKN", "normy", "Polish Standards".
---

# Polish Legal & Normative Documents

Standalone, dependency-free scripts for five Polish legal/normative data
sources, ported from the `polish-academic-mcp` MCP server's `isap.ts`,
`sejm-bs.ts`, `saos.ts`, `pkn.ts`, and `wiedza.ts` tools. No MCP server, API
keys, or third-party Python packages required -- everything runs with the
Python 3 standard library (`urllib`, `http.cookiejar`, `html.parser`,
`json`, `argparse`).

## Sources -- read this before picking a script

Two pairs of these sources sound similar but are **not** the same thing:

| Source | What it is | Backend | JSON or HTML? |
|---|---|---|---|
| **ISAP / ELI API** (`isap.py`) | Sejm's official legal-act database (Dziennik Ustaw, Monitor Polski, ustawy, rozporządzenia...) at `api.sejm.gov.pl` | Real JSON API | JSON |
| **Biblioteka Sejmowa OPAC** (`biblioteka_sejmowa.py`) | The Sejm *library's* book/journal/media catalog at `bs.sejm.gov.pl` -- a completely different service, despite both being "Sejm" | Aleph (Ex Libris) | HTML only |
| **SAOS** (`saos.py`) | Court judgments (System Analizy Orzeczeń Sądowych) -- search API + a separate bulk "dump" API | Custom JSON API | JSON |
| **PKN website search** (`pkn.py`) | General full-text search of the pkn.pl *website* (news, sections) | Drupal + Solr | HTML only |
| **WIEDZA-PKN norms catalog** (`wiedza.py`) | The actual Polish Standards (PN) catalog at `wiedza.pkn.pl` -- a different subdomain/backend from `pkn.py`, despite both being "PKN" | Liferay 6.1 portlet | HTML only |

**ISAP vs. Biblioteka Sejmowa:** ISAP is a real JSON API for *legal acts*.
Biblioteka Sejmowa is an HTML-only *library catalog* (books, journal
articles, session recordings) with no JSON API at all. If you want a statute
or regulation, use `isap.py`. If you want a book or article held by the
Sejm library, use `biblioteka_sejmowa.py`.

**PKN website vs. WIEDZA:** `pkn_search`/`pkn.py` searches pkn.pl's general
website content. It does **not** search Polish Standards -- for that you
need `wiedza.py` (the WIEDZA norms catalog, a different subdomain/backend
entirely).

## Search across every source at once

For any broad topic query, don't stop at the first source that answers --
run **`scripts/search_all.py --query "..."`** first. It fans the query out
in parallel to Biblioteka Sejmowa, ISAP, PKN, SAOS, and WIEDZA-PKN (mapped
to each source's closest free-text-equivalent field -- see the script's
docstring) and returns one combined JSON with a `results` object keyed by
source. Use the individual scripts directly when you need a filter this
aggregator doesn't expose (SAOS court/date filters, ISAP publisher/year,
WIEDZA ICS code, etc.).

```bash
python3 scripts/search_all.py --query "ochrona danych osobowych"
```

## Scripts

### `scripts/search_all.py` -- cross-source fan-out *(new -- not from the MCP port)*

Runs the five scripts below as parallel subprocesses and merges their JSON
output. See "Search across every source at once" above.

### `scripts/isap.py` -- ISAP / ELI API (JSON, no key)

| Subcommand | Original tool | Description |
|---|---|---|
| `search-acts` | `isap_search_acts` | Search legal acts by title, ISAP keyword tags, year, publisher (DU/MP/...), type, dates, in-force status. |
| `get-act` | `isap_get_act` | Fetch one act by ELI id, e.g. `DU/2026/370` (publisher/year/position). |

### `scripts/biblioteka_sejmowa.py` -- Biblioteka Sejmowa OPAC (HTML, Aleph)

| Subcommand | Original tool | Description |
|---|---|---|
| `search` | `bs_sejm_search` | Word search against a chosen Aleph local base (e.g. `bis01`, `pos01`). Returns raw HTML plus a best-effort `hits` list of `doc_library`/`doc_number` extracted from result links. |
| `get-item` | `bs_sejm_get_item` | Fetch one bibliographic record by `doc_library` + `doc_number` (taken from a `search` hit). |

### `scripts/saos.py` -- SAOS court judgments (JSON, no key)

| Subcommand | Original tool | Description |
|---|---|---|
| `search-judgments` | `saos_search_judgments` | Search judgments by free text, dates, case number, court, judgment type, etc. |
| `get-judgment` | `saos_get_judgment` | Fetch one full judgment by numeric id. |
| `dump-services` | `saos_dump_services` | List bulk-dump sub-service links. |
| `dump-common-courts` | `saos_dump_common_courts` | Paginated dump of common courts. |
| `dump-sc-chambers` | `saos_dump_sc_chambers` | Paginated dump of Supreme Court chambers. |
| `dump-judgments` | `saos_dump_judgments` | Bulk judgment dump -- **can return very large responses**; use a narrow date range and small page size. |
| `dump-enrichments` | `saos_dump_enrichments` | Paginated dump of enrichment tags. |

### `scripts/pkn.py` -- PKN website search (HTML, Drupal/Solr)

| Subcommand | Original tool | Description |
|---|---|---|
| `search` | `pkn_search` | Full-text search of pkn.pl site content (pl/en/ru). Not the norms catalog. |

### `scripts/wiedza.py` -- WIEDZA-PKN norms catalog (HTML, Liferay, session-based)

| Subcommand | Original tool | Description |
|---|---|---|
| `search-norms` | `wiedza_search_norms` | Search Polish Standards by number, title, content, ICS, sector, technical committee, directive, dates. Requires at least one criterion. |
| `get-standard` | `wiedza_get_standard` | Fetch one standard's detail page by its exact catalog number (from a `search-norms` result). |

All scripts print the final JSON result via
`json.dumps(result, ensure_ascii=False, indent=2)` on success, and on
failure print `Error: ...` to stderr and exit with status 1.

## Usage examples

Look up a specific act by its ELI id:

```bash
python3 scripts/isap.py get-act --eli "DU/2026/370"
```

Search ISAP for currently-in-force acts about a topic:

```bash
python3 scripts/isap.py search-acts --title "ochrona danych" --in-force --limit 10
```

Search the Biblioteka Sejmowa main catalog, then fetch a hit's full record:

```bash
python3 scripts/biblioteka_sejmowa.py search --query "prawo konstytucyjne" --local-base bis01
# from a hit's doc_library/doc_number:
python3 scripts/biblioteka_sejmowa.py get-item --doc-library BIS01 --doc-number 000179010
```

Search SAOS judgments by case number and date range, then fetch one in full:

```bash
python3 scripts/saos.py search-judgments --case-number "II CSK 123/20" --page-size 10
python3 scripts/saos.py get-judgment --id 123456
```

If SAOS search is unavailable ("Przerwa techniczna" maintenance mode), fall
back to a narrow bulk dump instead:

```bash
python3 scripts/saos.py dump-judgments --judgment-start-date 2024-01-01 \
  --judgment-end-date 2024-01-31 --page-size 10
```

Search pkn.pl's general website:

```bash
python3 scripts/pkn.py search --query "certyfikacja"
```

Search WIEDZA for a Polish Standard and fetch its detail page:

```bash
python3 scripts/wiedza.py search-norms --standard-number "PN-EN ISO 9001"
# using the exact number string from a result:
python3 scripts/wiedza.py get-standard --number "PN-EN ISO 9001:2015-10F"
```

## Notes / caveats

- **HTML scraping is inherently fragile.** `biblioteka_sejmowa.py`,
  `pkn.py`, and `wiedza.py` all depend on upstream markup that can change
  without notice. Every HTML-returning subcommand always includes the full
  raw `html` in its output alongside any best-effort extracted fields
  (`hits`, `links`) -- fall back to reading `html` yourself if extraction
  looks wrong. See `reference/API.md` for exactly what each parser targets
  and why.
- **WIEDZA needs a fresh session per call, and is never cached.** Every
  `wiedza.py` invocation does its own two-step Liferay session bootstrap
  (GET a landing page for a session cookie + auth token, then POST/GET the
  real request) -- there is no session reuse across invocations, and the
  original MCP server explicitly excludes these responses from its cache
  (session/token are short-lived by design). Expect 2 HTTP round-trips
  minimum per `wiedza.py` call.
- **SAOS has two distinct APIs under one base URL:** `search-judgments` /
  `get-judgment` for normal lookups, versus the bulk `dump-*` subcommands
  for wholesale mirroring/syncing. **`dump-judgments` can return very
  large responses** (full judgment records per row) -- always pass a
  narrow `--judgment-start-date`/`--judgment-end-date` window and a small
  `--page-size` (10-20); it is not a substitute for `search-judgments`.
- **Biblioteka Sejmowa `local_base` codes** vary by collection: `bis01`
  (main catalog), `bis05` (journal articles), `pos01` (session recordings),
  `tek01` (constitutional texts), `sta01` (old prints), `ars01`, and more --
  see `reference/API.md`.
- **Network policy.** All scripts use a 30-second timeout per request and
  retry once on transient network errors only (timeouts, connection
  reset/refused, unreachable network). HTTP 4xx/5xx responses are never
  retried and surface as a clear `RuntimeError` with the status code and a
  response body snippet.
- **No caching anywhere in this skill.** Unlike the original MCP server
  (which cached JSON/HTML responses for 1-24h via Cloudflare KV, except
  WIEDZA), these standalone scripts always hit the network live.
- See `reference/API.md` for the full parameter reference, exact endpoints,
  and a detailed account of what each HTML parser does and doesn't cover.

## Sources

- ISAP / ELI API: <https://api.sejm.gov.pl/eli/openapi/>
- Biblioteka Sejmowa OPAC: <https://bs.sejm.gov.pl/F>
- SAOS: <https://www.saos.org.pl/help/index.php/dokumentacja-api/api-przeszukiwania-danych> (search), <https://www.saos.org.pl/help/index.php/dokumentacja-api/api-pobierania-danych> (dump)
- PKN: <https://www.pkn.pl>
- WIEDZA-PKN: <https://wiedza.pkn.pl>

## Attribution

Ported from the `isap.ts`, `sejm-bs.ts`, `saos.ts`, `pkn.ts`, and
`wiedza.ts` tools in
[asterixix/polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp),
an MCP server for Polish academic and public data sources, by asterixix.
