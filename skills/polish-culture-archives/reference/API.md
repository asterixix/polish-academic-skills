# polish-culture-archives -- API reference notes

Detailed, per-source parsing/parameter notes that are too gnarly for
SKILL.md. All scripts live in `scripts/`, are Python 3 standard-library
only, and print `json.dumps(result, ensure_ascii=False, indent=2)` to
stdout. Errors go to stderr with a clear `Error calling <tool_name>: ...`
message and `exit(1)`.

Common HTTP policy (`scripts/_http.py`): `User-Agent:
polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)`,
30s timeout, single retry on transient network errors only (never on HTTP
4xx/5xx).

---

## BLZ -- Baza Legalnych Zrodel (`blz.py`)

WordPress REST, custom post type `listing` ("Zrodla"), no key. Base:
`https://bazalegalnychzrodel.pl/wp-json/wp/v2`.

- `search`: `GET /listings?search=&listing_cat=&page=&per_page=&orderby=&order=`.
  `orderby=relevance` requires a non-empty `search`; if the query is empty,
  the script silently falls back `orderby` to `date` (WordPress returns
  HTTP 400 for `orderby=relevance` with no search string otherwise).
- `get-listing`: `GET /listings/{id}`.
- `list-categories`: `GET /listing_cat?page=&per_page=&parent=` -- the
  taxonomy for `listing_cat` term ids. Known term ids include 78
  (Biblioteki) and 82 (Muzea), but always call `list-categories` to
  confirm current ids rather than hardcoding them.

All three return raw WordPress REST JSON (arrays of post/term objects),
printed as-is.

---

## BazTOL (`baztol.py`)

**Not updated since 2022-01-01** (site's own notice) -- treat every result
as a historical snapshot. No JSON API: an HTML form POST is replayed
against `http://baztol.library.put.poznan.pl/baztol_czytelnik/baztol`
(Apache + Perl CGI, `Content-Type:
application/x-www-form-urlencoded; charset=UTF-8`).

- `search`: POST body `akcja=szukanie_proste&dziedzina_id=&wyr_wysz=<query>&button_proste=Szukaj`.
  For `page > 1`, add `offset=(page-1)*20&kierunek=przod`. 20 results/page,
  server-side.
- `browse-domain`: POST body `akcja=przegladanie&dziedzina_id=<id>`, same
  paging as above. Domain ids (sidebar, 24-42):
  24 Architektura, 25 Automatyka, 26 Biotechnologia, 27 Budownictwo,
  28 Chemia, 29 Elektronika i Telekomunikacja, 30 Elektrotechnika i
  Energetyka, 31 Fizyka i Astronomia, 32 Geodezja i Kartografia,
  33 Gornictwo i Geologia, 34 Informatyka, 35 Inzynieria i Ochrona
  Srodowiska, 36 Inzynieria Materialowa, 37 Matematyka, 38 Mechanika,
  39 Oceanologia i Oceanotechnika, 40 Transport, 41 Zarzadzanie,
  42 Zrodla ogolne.
- `get-resource`: `GET /baztol_czytelnik/baztol?id=<id>`.

All three return `{"...params..., "note": "<staleness note>", "html":
"<raw HTML>"}` since there is no structured JSON to parse server-side; the
caller/model should extract titles, links, and descriptions from the HTML
itself (e.g. by grep-ing for `<a href=...id=`).

---

## NAC -- Narodowe Archiwum Cyfrowe (`nac.py`)

Institutional WordPress site only (`www.nac.gov.pl`) -- the digitized
archival holdings live on `szukajwarchiwach.gov.pl`, which has no
documented public API and is commonly behind bot/WAF protection, so it is
intentionally out of scope for this skill.

- `news-rss`: `GET https://www.nac.gov.pl/feed/` -- RSS 2.0 XML, wrapped as
  `{"url":..., "note":..., "rss_xml": "<raw RSS XML>"}`.
- `site-search` / `get-post` / `get-page`: use the **`?rest_route=/wp/v2/...`**
  query-string form of the WordPress REST API rather than the prettier
  `/wp-json/wp/v2/...` path form. This is deliberate: the origin's WAF is
  more likely to block the pretty-permalink `/wp-json/` path than the
  `?rest_route=` query form. Because the base URL already contains a `?`
  (`?rest_route=/wp/v2`), any additional query parameters MUST be appended
  with `&`, never a second `?` -- see `build_wp_rest_url()` in `nac.py`.
  - `site-search`: `GET ?rest_route=/wp/v2/search&search=&per_page=&subtype=post&subtype=page`.
    A `403` response typically means the WAF is blocking the request; the
    script surfaces this as a specific hint in the error message.
  - `get-post`: `GET ?rest_route=/wp/v2/posts/{id}`.
  - `get-page`: `GET ?rest_route=/wp/v2/pages/{id}`.

These three return parsed JSON printed as-is (WordPress REST objects/arrays).

---

## Katalog Biblioteki SUM -- Aleph X-Services (`sum_aleph.py`)

OPAC: `https://katalog.sum.edu.pl/` ; machine interface: Aleph **X-Server**
at `https://katalog.sum.edu.pl/X` (XML). See Ex Libris docs:
https://developers.exlibrisgroup.com/aleph/apis/aleph-x-services/

- `find`: `GET /X?op=find&base=<local_base>&request=<query>`. `request`
  uses Aleph WWW index prefixes, e.g. `wrd=kardiologia` (any word),
  `wti=<title words>`, `wau=<author>`. `local_base` defaults to `SUM01`.
- `present`: `GET /X?op=present&set_no=<set_no>&set_entry=<set_entry>&format=<format>`.
  `set_entry` can be a single zero-padded index (e.g. `000000001`) or a
  range (`000000001,000000005`). `format` defaults to `marc`.

**Known upstream limitation**: as observed in 2026-03 testing, `op=find` on
this installation answers with an XML `<error>` element reading `SRU gate
configuration file is missing.` (or similarly worded) -- the library's SRU
gateway is not configured server-side. This is *not* a bug in the script.
`sum_aleph.py find` detects this and adds a `known_upstream_limitation`
field to the JSON output explaining it; `sum_aleph.py present` is
unaffected and has worked in tests when given a valid `set_no`/`set_entry`
pair from another source (e.g. the OPAC web UI).

Both subcommands parse the XML response generically with
`xml.etree.ElementTree` into a nested `parsed` object (tag -> text or
nested children; Aleph X-Server response shapes vary by installation and
operation, so no fixed schema is assumed) and always include the
`raw_xml` alongside it so nothing is lost if the generic parse misses a
field of interest.

---

## PAUart (`pauart.py`)

UI: `http://www.pauart.pl/app` (note: plain HTTP, no TLS). API:
`POST http://www.pauart.pl/api/search` (Collectio / Elasticsearch-style
JSON body, no key).

Request body shape for both subcommands:
```json
{
  "query": { "multi_match": { "query": "<text>", "fields": ["_all"] } },
  "options": { "trash": "NOT_REMOVED" },
  "pageRequest": { "pageSize": <size>, "pageNumber": <page> }
}
```
`get-artwork` instead uses `"query": {"ids": {"values": ["<id>"]}}` with
`pageNumber=0, pageSize=1`.

The raw Elasticsearch-shaped response (`content: [...]`, mixing `_type:
"artwork"` rows with dictionary/other rows) is summarized into a compact
form before printing:
- `search`: `{totalElements, totalPages, page, pageSize, artworksOnly,
  items: [...]}` where each artwork item is `{id, title, inventoryNumber,
  copyright, objectType, tags, dimensions, previewPath, ui}` (`ui` is
  always the PAUart app URL, since there is no direct public detail page
  URL scheme documented). Non-artwork rows (when `--no-artworks-only`) are
  reduced to `{_type, id, label}`.
- `get-artwork`: the first `_type=="artwork"` entry from the response,
  compacted the same way, or `{"error": "not_found", "raw": <response>}`
  if no artwork entry is present (e.g. unknown id).

---

## Wolne Lektury (`wolne_lektury.py`)

Public JSON API, no key: `https://wolnelektury.pl/api/`. **Never** call
the flat `/api/books/` endpoint directly (multi-megabyte JSON) -- this
skill deliberately has no subcommand for it.

- `list-taxonomy --kind {authors,epochs,genres,kinds,themes,collections}`:
  `GET /api/{kind}/` -- names, slugs, hrefs for discovery. Responses are
  relatively large for `themes`/`collections` (~100KB); that's expected.
- `filter-books --author/--epoch/--genre/--kind [--parent-only]`: builds
  a nested path `/api/authors/{a}/epochs/{e}/genres/{g}/kinds/{k}/books/`
  (segments included only for filters actually given, in that fixed
  order), with `parent_books/` instead of `books/` when `--parent-only`
  is set (top-level works only, no sub-volumes). **At least one filter is
  required** -- the script fails fast with a clear message before making
  any network call if none are given, since there is no supported
  full-text search endpoint.
- `get-book --slug <slug>`: `GET /api/books/{slug}/` -- title, authors,
  epochs, genres, download links (epub/pdf/etc.), child volumes, optional
  fragment preview.
- `get-collection --slug <slug>`: `GET /api/collections/{slug}/` --
  collection metadata + embedded books list.

All slugs are percent-encoded (`urllib.parse.quote(slug.strip(), safe="")`)
before being spliced into the URL path.

---

## Dokumenty Slaska (`dokumenty_slaska.py`)

Static HTML site (`https://www.dokumentyslaska.pl/`), no API, no
site-wide search. Most pages are legacy Polish sites and may be served as
`iso-8859-2`; the script honors whatever charset the response's
`Content-Type` header declares and only falls back to `iso-8859-2` when
the server doesn't say (see `_http.request_text`'s `default_encoding`
param, set to `iso-8859-2` for this script specifically).

- `get-page --path <relative path>`: fetches exactly one page. The path is
  validated by `to_safe_site_url()`, a faithful port of the original
  TypeScript `toSafeSiteUrl()`:
  1. Trim whitespace, then strip all leading `/` characters.
  2. Reject empty or >512-character paths.
  3. Reject paths starting with `http://`/`https://` (case-insensitive)
     or `//` (checked *after* the leading-slash strip above, exactly as
     in the original -- so `//host/path` is not actually rejected by this
     check since the leading slashes are already gone by this point; it
     still can't escape the site because the result is always spliced
     under `SITE_ORIGIN/`, e.g. `//evil.com/x` safely becomes
     `https://www.dokumentyslaska.pl/evil.com/x`).
  4. Reject any path containing `..`.
  5. Split on `/` and reject empty, `.`, or `..` segments.
  6. For each segment, try a strict `decodeURIComponent`-style decode
     (raises on malformed `%XX` escapes or invalid UTF-8) and re-encode
     the decoded text; on any decode failure, fall back to encoding the
     raw segment as-is (mirrors the original's `try {...} catch {...}`).
  7. Join segments with `/` and prepend `https://www.dokumentyslaska.pl/`.

  Examples: `"indeks 1200.html"`, `"dokument 1201-1230.html"`,
  `"bibliografia.html"`, `"kamenz/index.html"` (spaces in filenames are
  fine and get percent-encoded).
- `medieval-catalog`: no network call -- returns the fixed list of 10
  periods (`Do 1200 roku` through `1327-1333`) from the homepage's
  "Dokumenty" menu, each with an `indeks *.html` (table of contents) and
  `dokument *.html` (full text) relative path, for use with `get-page`.
  This is a navigation aid only, not a database query -- other
  collections on the site (monasteries, chronicles, etc.) use different
  folders not covered here; discover those paths from the homepage HTML
  itself via `get-page --path ""`-style browsing (starting from
  `get-page --path "index.html"` or similar entry points).
