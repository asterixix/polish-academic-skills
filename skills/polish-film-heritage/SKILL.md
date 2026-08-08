---
name: polish-film-heritage
description: Searches and fetches records from Polish film and photography heritage archives (mostly Filmoteka Narodowa / FINA sources) -- Ninateka VOD, Gapla poster gallery, Fototeka photo archive, FilmPolski.pl database, Fototeka Śląska (Silesian photo archive), and the FN digital repository. All HTML-scraped except Ninateka (JSON API). IMPORTANT -- for any broad topic search, run `scripts/search_all.py --query X` first: it fans the query out to all six sources in parallel. Use for Polish film heritage, FINA, Filmoteka Narodowa, film posters, movie posters Poland, FilmPolski, polskie filmy, plakaty filmowe, fotosy filmowe, archiwum filmowe, historia kina polskiego, filmoteka, wyszukiwarka filmów.
---

# Polish Film Heritage

## Overview

Six standalone, dependency-free sources covering Polish film and
photography heritage, mostly tied to Filmoteka Narodowa (FINA) -- the
Polish National Film Archive:

| Source | What it is | Data format |
|---|---|---|
| **Ninateka** (ninateka.pl) | FINA's free VOD platform: films, documentaries, theatre, audio | Real JSON API (undocumented, `platform=BROWSER` required) |
| **Gapla** (gapla.fn.org.pl) | FINA film poster gallery | HTML, no API |
| **Fototeka** (fototeka.fn.org.pl) | FINA/INA photo archive -- ~300k+ Polish cinema stills | HTML, no API |
| **FilmPolski.pl** | Internetowa Baza Filmu Polskiego (PWSFTviT Łódź film database) | HTML, no API -- copying-restricted |
| **Fototeka Śląska** (fototekaslaska.pl) | Muzeum Wsi Opolskiej -- rural Silesia/Opole historical photos | HTML (WordPress), no API |
| **Repozytorium Cyfrowe FN** (repozytorium.fn.org.pl) | FINA digital repository (Drupal 7 + Solr) | HTML, no API |

All scripts are standard-library-only Python 3 (`urllib`, `json`,
`argparse`, `re`) -- no third-party dependencies. No API key is required
for any of the six sources.

**Main fragility risk**: five of six sources have no public API and are
scraped from HTML. If any site changes its page layout, the parsing in
this skill can silently return incomplete or empty results. Two sources
(FilmPolski, Fototeka Śląska) port the *exact* regex parsing logic from the
upstream TypeScript MCP tool it was ported from, so they're as reliable as
that reference implementation. The other three HTML sources (Gapla,
Fototeka, Repozytorium FN) use **new, generic, best-effort extraction**
layered on top of what the original tool did (return raw HTML, unparsed) --
every script for those three always includes a capped `raw_html` field as
a fallback so nothing is lost if the structured fields come back empty or
wrong. See `reference/API.md` for exactly which parsing is a direct port
vs. new best-effort heuristic, and why.

## Search across every source at once

For any broad topic query, don't stop at the first source that answers --
run **`scripts/search_all.py --query "..."`** first. All six sources in
this skill support a plain `--query` search, so it fans out to every one of
them in parallel and returns one combined JSON with a `results` object
keyed by source. Per-source failures (timeouts, layout-change scraping
breakage) never abort the others.

```bash
python3 scripts/search_all.py --query "Wajda"
```

## Scripts

| Script | Subcommand | Description |
|---|---|---|
| `scripts/search_all.py` | *(n/a)* | Fans one `--query` out to all six sources below in parallel. See "Search across every source at once" above. |
| `scripts/ninateka.py` | `search` | Search Ninateka VOD items by keyword. |
| `scripts/ninateka.py` | `get-vod` | Full metadata for one item by numeric id. |
| `scripts/gapla.py` | `search` | Search film posters by title/artist/director. |
| `scripts/gapla.py` | `get-poster` | One poster detail page by numeric id. |
| `scripts/fototeka.py` | `search` | Search cinema stills by title/person/director/keyword. |
| `scripts/fototeka.py` | `get-photo` | One photo detail page by numeric id. |
| `scripts/filmpolski.py` | `search` | Search films/TV/theatre/people (fragment/start/exact match). |
| `scripts/filmpolski.py` | `get-item` | One record's text excerpt by numeric id (film or person). |
| `scripts/fototeka_slaska.py` | `search` | Search Silesian historical photos by title/place/district/description/catalog no. |
| `scripts/fototeka_slaska.py` | `get-photo` | One photo page by URL slug. |
| `scripts/fn_repozytorium.py` | `search` | Solr site search across the FN digital repository. |
| `scripts/fn_repozytorium.py` | `get-node` | One catalog node (film/article/person) by Drupal node id. |
| `scripts/fn_repozytorium.py` | `film-index` | Browse the film title index by first letter (A-Z, INNE). |
| `scripts/fn_repozytorium.py` | `browse-kind` | Browse by production kind (feature/doc/animation/magazine). |

`scripts/_http.py` is a shared internal helper (30s timeout, one retry on
transient network errors only, never on HTTP 4xx/5xx, plus shared HTML
text-extraction helpers) -- not invoked directly.

## Usage

### Ninateka (VOD, real JSON API)

```bash
python3 scripts/ninateka.py search --query "Wajda" --limit 10
python3 scripts/ninateka.py get-vod --id 123456
```

`platform=BROWSER` is sent automatically (required by the upstream API;
omitting it returns a `PLATFORM_UNDEFINED` error). Metadata only -- no
streaming URLs or DRM.

### Gapla (film posters)

```bash
python3 scripts/gapla.py search --query "Popiół i diament" --typ tytul
python3 scripts/gapla.py search --query "Wojciech Fangor" --typ autor --sort chronologicznie_asc
python3 scripts/gapla.py get-poster --id 4821
```

`--typ`: `tytul` (title, default), `autor` (artist), `rezyseria` (director).

### Fototeka (cinema stills / production photos)

```bash
python3 scripts/fototeka.py search --query "Andrzej Wajda" --search-type rezyseria
python3 scripts/fototeka.py get-photo --id 98765
```

`--search-type`: `tytul`, `osoba`, `rezyseria`, `slowo_kluczowe` (default).

### FilmPolski.pl (Polish Film Database)

```bash
python3 scripts/filmpolski.py search --query "Kieślowski" --mode fragment
python3 scripts/filmpolski.py search --query "Kowalski, Jan" --mode exact
python3 scripts/filmpolski.py get-item --id 12345
```

`--mode`: `fragment` (substring, default), `start` (title/surname prefix,
Polish: *początek*), `exact` (exact match, Polish: *dokładnie* -- for
people use `"Surname, Firstname"` with a comma). **Copying restriction**:
filmpolski.pl's terms limit bulk copying of database content --
`get-item` only ever returns a short, truncated text excerpt (never the
full page) and both subcommands print a one-line reminder to stderr to
cite filmpolski.pl as the source.

### Fototeka Śląska (rural Silesia / Opole historical photos)

```bash
python3 scripts/fototeka_slaska.py search --query "Opole" --field place --period 1918-1939
python3 scripts/fototeka_slaska.py get-photo --slug dzieci-przed-domem
```

`--field`: `title` (default), `place`, `district`, `description`,
`catalog_n`. `--period` (optional): `do1900`, `1900-1918`, `1918-1939`,
`1939-1945`. Search results are parsed strictly from the page's
`.search-list` block so the site's "recently added" section is never
mixed into results (see `reference/API.md`). Respect the museum's
copyright -- do not bulk-download image files.

### Repozytorium Cyfrowe FN (digital repository)

```bash
python3 scripts/fn_repozytorium.py search --query "Warszawa" --facet bundle:doc
python3 scripts/fn_repozytorium.py get-node --id 8937
python3 scripts/fn_repozytorium.py film-index --letter A
python3 scripts/fn_repozytorium.py browse-kind --kind fabularne 2>/dev/null || \
python3 scripts/fn_repozytorium.py browse-kind --kind feature
```

`--kind`: `feature` (fabularne), `doc` (dokumentalne), `animation`
(animacje), `magazine` (magazyn filmowy). `--facet` may be repeated
(`field:value`, e.g. `bundle:person`, `sm_field_year:1964`).

Every command prints pretty-printed JSON
(`json.dumps(..., ensure_ascii=False, indent=2)`) to stdout. On failure, a
clear error goes to stderr and the process exits with status 1.

## Caveats

- **HTML-scraping fragility is the main risk of this whole skill.** Five
  of six sources have no public API; parsing breaks silently if a site's
  markup changes. FilmPolski and Fototeka Śląska port the exact TS regex
  logic (reliable, matches the reference implementation field-for-field).
  Gapla, Fototeka, and Repozytorium FN use new generic best-effort
  extraction (the original TS tools for these three returned raw HTML
  unparsed) -- every response from those three always includes a capped
  `raw_html` fallback field. See `reference/API.md` for full details.
- **FilmPolski.pl copying restriction**: use short excerpts only, always
  cite filmpolski.pl as the source; `get-item` truncates at 25,000
  characters and never returns the full page.
- **Fototeka Śląska**: search results must come only from the page's
  `.search-list` block (up to the `<h3 class="serch-recently-added">`
  marker) -- mixing in the "recently added" section would misrepresent
  search results. Respect museum copyright; no bulk image downloads.
- No API keys or registration required for any of the six sources.
- No response caching in this standalone port (the source MCP project
  caches responses in Cloudflare KV; every call here hits the network
  directly).

## Source links

- https://ninateka.pl/
- https://gapla.fn.org.pl/
- https://fototeka.fn.org.pl/
- https://www.filmpolski.pl/fp/
- https://fototekaslaska.pl/
- https://repozytorium.fn.org.pl/

## Attribution

Ported from the `ninateka_*`, `gapla_*`, `fototeka_*`, `filmpolski_*`,
`fototekaslaska_*`, and `fn_repo_*` tools in
[polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp) by
asterixix.
