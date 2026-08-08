---
name: polish-culture-archives
description: Query Polish cultural heritage, archives, and reference catalogs - Baza Legalnych Zrodel (legal digital-culture sources directory), BazTOL (technical-science web gateway, stale since 2022), NAC / Narodowe Archiwum Cyfrowe (National Digital Archive news + WordPress content), Katalog Biblioteki SUM (medical-university Aleph library catalog), PAUart (PAU fine-arts catalog), Wolne Lektury (free ebook library of Polish literature), Dokumenty Slaska (static historical-documents site), Centrum Informacji o Ofiarach II Wojny Swiatowej / IPN (WWII victims database), and EDUKATOR (Pedagogical University of Krakow staff bibliography). IMPORTANT -- for any broad topic search, run `scripts/search_all.py --query X` first: it fans the query out to every free-text-searchable source in this skill in parallel. Use when the user asks about Polish cultural heritage, digital archives, archiwa cyfrowe, dziedzictwo kulturowe, legalne zrodla kultury, BazTOL, NAC, National Digital Archive, katalog biblioteczny Aleph, PAUart, dziela sztuki, Wolne Lektury, wolne lektury, free ebooks Polish literature, biblioteka cyfrowa, medieval Silesian documents, ofiary wojny, IPN, druga wojna swiatowa, or bibliografia pracownikow uczelni. No API keys needed for any of these sources.
---

# Polish Culture Archives

Standalone, dependency-free Python 3 scripts (standard library only) for
nine Polish cultural-heritage and reference sources. No API keys are
needed anywhere in this skill. Seven were ported from the
`polish-academic-mcp` MCP server's tools of the same names, with the MCP
layer and Cloudflare KV caching stripped out so each script runs as a plain
CLI; two (`ofiary_ipn.py`, `bgbase_edu.py`) were added directly to this
skill based on live-verified HTML form dumps (see their docstrings for what
was actually confirmed against the real server vs. best-effort).

## The 9 sources at a glance

| Source | What it is | Format | Notes |
|---|---|---|---|
| **BLZ** (Baza Legalnych Zrodel) | Directory of legal digital-culture sources (Fundacja Legalna Kultura) | JSON (WordPress REST) | Clean, actively maintained |
| **BazTOL** | Subject gateway for Polish technical-science web resources (Biblioteka PUT) | HTML (scraped form POST) | **Not updated since 2022-01-01** -- treat as historical snapshot |
| **NAC** | Narodowe Archiwum Cyfrowe (National Digital Archive) institutional site | RSS/XML + JSON (WordPress REST) | Only the institutional site; digitized holdings live elsewhere (see Caveats) |
| **Katalog SUM** | Library catalog of the Silesian Medical University (Aleph/Ex Libris) | XML (Aleph X-Services) | Search (`find`) may be broken server-side (see Caveats) |
| **PAUart** | Fine-arts catalog of the Polish Academy of Arts and Sciences (PAU) | JSON (Collectio/Elasticsearch) | |
| **Wolne Lektury** | Free ebook library of (mostly public-domain) Polish literature | JSON (official API) | No full-text search; filter by taxonomy instead |
| **Dokumenty Slaska** | Static site of medieval Silesian documents, regesty, heraldry | HTML (static pages) | No API, no search; fixed navigation list only |
| **Centrum Informacji o Ofiarach II WS** (IPN) | WWII victims/records database, `ofiary.ipn.gov.pl` | HTML (POSTs the real search form) | Field names confirmed live; the shape of a *populated* results page is not yet confirmed (see script docstring) |
| **EDUKATOR** (bgbase.up.krakow.pl) | Staff/doctoral-student publication bibliography, Pedagogical University of Krakow | HTML (Expertus CGI, iso-8859-2) | Query confirmed working live (verified "no results" response); populated-results shape not yet confirmed |

## Search across every source at once

For any broad topic query, don't stop at the first source that answers --
run **`scripts/search_all.py --query "..."`** first. It fans the query out
in parallel to BazTOL, BLZ, NAC, PAUart, Katalog SUM, Centrum Informacji o
Ofiarach II WS (IPN), and EDUKATOR (everything with a real free-text
search) and returns one combined JSON with a `results` object keyed by
source. Per-source failures (including Katalog SUM's known SRU-gate
outage) never abort the others. Wolne Lektury and Dokumenty Slaska are
taxonomy/path-browsing only (no keyword query) and are listed separately
in the aggregator's output -- call them directly instead.

```bash
python3 scripts/search_all.py --query "Śląsk"
```

## Scripts and subcommands

All scripts live in `scripts/` and share `scripts/_http.py` (30s timeout,
one retry on transient network errors only, never on HTTP 4xx/5xx,
`User-Agent: polish-academic-skills/1.0
(+https://github.com/asterixix/polish-academic-skills)`). Every subcommand
prints a JSON document to stdout (`json.dumps(..., ensure_ascii=False,
indent=2)`); on failure it prints `Error calling <tool_name>: ...` to
stderr and exits 1.

| Script | Subcommand | Original MCP tool |
|---|---|---|
| `blz.py` | `search --query --listing-cat --page --per-page --orderby --order` | `blz_search` |
| `blz.py` | `get-listing --id` | `blz_get_listing` |
| `blz.py` | `list-categories --page --per-page --parent` | `blz_listing_categories` |
| `baztol.py` | `search --query --page` | `baztol_search` |
| `baztol.py` | `browse-domain --domain-id --page` | `baztol_browse_domain` |
| `baztol.py` | `get-resource --id` | `baztol_get_resource` |
| `nac.py` | `news-rss` | `nac_news_rss` |
| `nac.py` | `site-search --query --per-page --subtypes` | `nac_site_search` |
| `nac.py` | `get-post --id` | `nac_get_post` |
| `nac.py` | `get-page --id` | `nac_get_page` |
| `sum_aleph.py` | `find --base --request` | `sum_aleph_find` |
| `sum_aleph.py` | `present --set-no --set-entry --format` | `sum_aleph_present` |
| `pauart.py` | `search --query --page --size --artworks-only/--no-artworks-only` | `pauart_search` |
| `pauart.py` | `get-artwork --id` | `pauart_get_artwork` |
| `wolne_lektury.py` | `list-taxonomy --kind` | `wolnelektury_list_taxonomy` |
| `wolne_lektury.py` | `filter-books --author --epoch --genre --kind --parent-only` | `wolnelektury_filter_books` |
| `wolne_lektury.py` | `get-book --slug` | `wolnelektury_get_book` |
| `wolne_lektury.py` | `get-collection --slug` | `wolnelektury_get_collection` |
| `dokumenty_slaska.py` | `get-page --path` | `dokumenty_slaska_get_page` |
| `dokumenty_slaska.py` | `medieval-catalog` | `dokumenty_slaska_medieval_catalog` |
| `ofiary_ipn.py` | `search --query --scope --exact-phrase --exclude-words --or-term1/2/3 --date-from --date-to --category` | *(new -- not from the MCP port)* POSTs the real search form on ofiary.ipn.gov.pl. |
| `bgbase_edu.py` | `search --query1 --field1 --query2 --field2 --query3 --field3 --combine --sort --format --page-size` | *(new -- not from the MCP port)* GETs the EDUKATOR Expertus CGI (Uniwersytet Pedagogiczny w Krakowie). |
| `search_all.py` | `--query --sum-base` | *(new -- not from the MCP port)* Fans one query out to BazTOL, BLZ, NAC, PAUart, Katalog SUM, ofiary_ipn, and bgbase_edu in parallel. |

Gnarly per-source parsing/parameter details (exact request bodies, XML
shapes, domain id tables, path-validation algorithm) are in
`reference/API.md` -- read it before making non-trivial changes to any one
script.

## Usage examples

```bash
# BLZ -- legal digital-culture sources
python3 scripts/blz.py list-categories
python3 scripts/blz.py search --query "muzeum" --listing-cat 82 --page 1
python3 scripts/blz.py get-listing --id 1234

# BazTOL -- technical-science gateway (HTML, stale since 2022)
python3 scripts/baztol.py search --query "informatyka"
python3 scripts/baztol.py browse-domain --domain-id 34
python3 scripts/baztol.py get-resource --id 5678

# NAC -- National Digital Archive institutional site
python3 scripts/nac.py news-rss
python3 scripts/nac.py site-search --query "fotografia" --per-page 10
python3 scripts/nac.py get-post --id 4321

# Katalog SUM -- Aleph X-Services
python3 scripts/sum_aleph.py find --base SUM01 --request "wrd=kardiologia"
python3 scripts/sum_aleph.py present --set-no 000001 --set-entry 000000001

# PAUart -- fine-arts catalog
python3 scripts/pauart.py search --query "portret" --size 10
python3 scripts/pauart.py get-artwork --id AN_KIII_150_16476

# Wolne Lektury -- free Polish-literature ebooks
python3 scripts/wolne_lektury.py list-taxonomy --kind authors
python3 scripts/wolne_lektury.py filter-books --author boleslaw-prus --epoch pozytywizm
python3 scripts/wolne_lektury.py get-book --slug lalka

# Dokumenty Slaska -- static medieval-documents site
python3 scripts/dokumenty_slaska.py medieval-catalog
python3 scripts/dokumenty_slaska.py get-page --path "indeks 1200.html"
```

## Caveats

- **BazTOL is likely stale.** The portal carries its own notice that it
  has not been actively updated since 2022-01-01. Every `baztol.py`
  response includes a `note` field repeating this; present BazTOL results
  to users as a historical snapshot, not current holdings.
- **SUM Aleph `find` may be broken server-side.** As observed in 2026-03
  testing, `op=find` on `katalog.sum.edu.pl` can respond with an XML
  `<error>` about a missing SRU gate configuration -- a library-side
  misconfiguration, not a bug in this script. `sum_aleph.py find` detects
  this pattern and adds a `known_upstream_limitation` field explaining it.
  `sum_aleph.py present` (fetching a record by `set_no`/`set_entry`) is
  unaffected.
- **NAC covers the institutional site only.** `nac.py` talks to
  `www.nac.gov.pl` (news + WordPress pages/posts), using the
  `?rest_route=/wp/v2/...` query-string form of the REST API rather than
  `/wp-json/wp/v2/...` because it is more resistant to the origin's WAF.
  The actual digitized archival holdings are published separately on
  `szukajwarchiwach.gov.pl`, which has no documented public API and is
  out of scope here.
- **Dokumenty Slaska has no search.** It is a static HTML site with no API
  and no full-text index. `dokumenty_slaska.py` only offers a validated
  single-page fetch (`get-page`) plus a fixed JSON list of paths for the
  main medieval document series up to 1333 (`medieval-catalog`) -- this is
  a navigation aid, not a query engine. Other collections on the site use
  different folders and must be discovered by following links in fetched
  HTML.
- **Wolne Lektury has no full-text search.** The API only supports
  filtering by taxonomy (author/epoch/genre/kind); `filter-books` requires
  at least one of these. The flat `/api/books/` endpoint is deliberately
  not exposed since it returns a multi-megabyte JSON array.
- **PAUart's UI and API are served over plain HTTP** (no TLS) at
  `pauart.pl` -- this is upstream's own configuration, not a mistake here.

## Sources

- BLZ: https://bazalegalnychzrodel.pl/
- BazTOL: http://baztol.library.put.poznan.pl/
- NAC: https://www.nac.gov.pl/
- Katalog Biblioteki SUM: https://katalog.sum.edu.pl/ (Aleph X-Services docs: https://developers.exlibrisgroup.com/aleph/apis/aleph-x-services/)
- PAUart: http://www.pauart.pl/app
- Wolne Lektury: https://wolnelektury.pl/api/
- Dokumenty Slaska: https://www.dokumentyslaska.pl/
- Centrum Informacji o Ofiarach II WS (IPN): https://ofiary.ipn.gov.pl/ofi/search
- EDUKATOR (bgbase.up.krakow.pl): http://bgbase.up.krakow.pl/biblio/bibliografia/index.php?base=edu

## Attribution

Ported from the tool definitions in
[asterixix/polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp)
(MCP server by asterixix). This skill reimplements the same request
shapes and response handling as standalone scripts, without any MCP
server, SDK, or caching layer.
