# API / parsing reference -- polish-film-heritage

This file holds the gnarly per-source HTML-parsing details that don't
belong in SKILL.md. All six sources are ported from
[polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp)
(`src/tools/ninateka.ts`, `gapla.ts`, `fototeka.ts`, `filmpolski.ts`,
`fototekaslaska.ts`, `filmoteka-repo.ts`).

**Sandbox caveat that applies to every "best-effort" note below:** this
skill was authored in a sandbox that blocks arbitrary outbound HTTPS, so
none of the parsing logic below could be checked against a live fetch.
Two of the six sources (FilmPolski, Fototeka Śląska) have their parsing
**directly ported line-for-line from the TS regex source**, so those are
as reliable as the original MCP tool. The other four (Ninateka, Gapla,
Fototeka, Repozytorium FN) either use a real JSON API (Ninateka) or rely
on **new, generic, best-effort HTML extraction** layered on top of what
the TS tool did (which, for those four, was simply "return the raw HTML
unmodified" -- see per-source notes). Treat structured fields from those
four as helpful-but-unverified; `raw_html` is always included, capped, as
a fallback.

## Ninateka (`ninateka.py`)

Not actually HTML -- this is the one source with a real (if undocumented)
JSON API. The front-end SPA calls `https://ninateka.pl/api/products/vods/...`.

- `platform=BROWSER` is a **required** query parameter on every call; omit
  it and the API answers with a `PLATFORM_UNDEFINED` error. There is no
  other valid value for the public/anonymous case, so the CLI defaults
  it and only accepts `BROWSER`.
- Search uses `keyword` (not `query` or `q`) plus `limit` (page size, API
  usually accepts up to 100) and `firstResult` (zero-based offset).
- `get-vod` hits `/api/products/vods/{id}?platform=BROWSER` and returns full
  item metadata (description, categories, images, `type`: VOD / EPISODE /
  SERIAL, ...). No streaming URLs or DRM tokens are exposed by this
  endpoint.
- Both subcommands print the upstream JSON verbatim (after
  `json.loads`/re-`dumps` round-trip for consistent formatting) -- no
  reshaping, matching the TS tool's behavior of forwarding `cachedFetch`'s
  raw text.

## Gapla (`gapla.py`)

`https://gapla.fn.org.pl/` -- film poster gallery. No JSON API; classic
GET-form HTML.

- Search: `szukaj.html?q=&typ=&page=&sort=`.
  - `typ`: `tytul` (title), `autor` (artist/credited person), `rezyseria`
    (director).
  - `sort`: `alfabetycznie` (default), `chronologicznie_asc`,
    `chronologicznie_desc`.
- Poster detail: `plakat/{id}.html`. The `id` is purely numeric; any slug
  segment in the public URL (`plakat/{id}/some-title.html`) is optional for
  retrieval -- `plakat/{id}.html` alone works, per the TS tool's comment.
- **The upstream TS tool does no HTML parsing at all** -- `gapla_search`
  and `gapla_get_poster` return the fetched page as raw HTML text. This
  Python port adds:
  - `search`: `items` extracted via the shared `extract_id_links(html,
    "plakat", base_url=SITE_BASE)` heuristic in `_http.py` -- any anchor
    whose `href` contains `plakat/{numeric-id}`, deduplicated by id, first
    non-empty link text as `title`, first `<img src=...>`/`data-src` found
    inside the anchor as `image_url`.
  - `get-poster`: `title` (first `<h1>`, falling back to `<title>`) and
    `text` (whole `<body>` stripped to plain text, capped at 15,000 chars)
    via the shared `extract_title` / `extract_body_text` helpers.
  - `raw_html` (capped at 20,000 chars for search, included on both
    commands) is always present so nothing is lost if the heuristic
    extraction misses or misreads the page.

## Fototeka (`fototeka.py`)

`https://fototeka.fn.org.pl/` -- ~300k+ Polish cinema stills/production
photos. No documented public REST API.

- Search: `/pl/strona/wyszukiwarka.html?key=&search_type=&pageNumber=&howmany=`.
  - `search_type`: `tytul` (film title), `osoba` (person), `rezyseria`
    (director), `slowo_kluczowe` (keywords, default).
  - Note the API param names: the search phrase is `key`, not `query`;
    page is `pageNumber`; page size is `howmany`.
- Photo detail: `/pl/foto/view/{id}.html`.
- There is an internal `ajax.html` endpoint that returns JSON containing
  HTML fragments, but per the TS source's own comment it requires a fully
  serialized form (including a session hash) and is **not usable
  statelessly** -- neither the TS tool nor this port calls it.
- **Like Gapla, the upstream TS tool returns raw HTML unmodified** for both
  tools. This Python port layers the same generic extraction on top:
  `items` via `extract_id_links(html, "foto/view", base_url=SITE)` for
  search, `title`/`text` via `extract_title`/`extract_body_text` for
  get-photo, with `raw_html` always included as a fallback. Does not (and
  cannot) return the full-resolution image file -- text/HTML only, same
  as upstream.

## FilmPolski.pl (`filmpolski.py`) -- DIRECT PORT of TS parsing

`https://www.filmpolski.pl/fp/` -- Internetowa Baza Filmu Polskiego
(PWSFTviT Łódź). No public JSON API. **This is the one source where the TS
tool does real, targeted HTML parsing (regex-based), and this script ports
it field-for-field.**

- Search: `index.php?szukaj={query}&rodzaj={1|2|3}`.
  - `rodzaj=1` -- fragment (substring match anywhere), CLI `--mode fragment`
    (default).
  - `rodzaj=2` -- start / "początek" (title or surname prefix match), CLI
    `--mode start`.
  - `rodzaj=3` -- exact / "dokładnie", CLI `--mode exact`. For a person,
    the exact-match query must be `"Surname, Firstname"` (comma required) --
    this is a site convention, not something the script enforces.
  - The page has **two independent result lists**, both `<ul>` elements:
    - `<ul class="wynikiszukania wynikiszukaniaosoba">` -- people/institutions.
      Note the class string is `"wynikiszukania wynikiszukaniaosoba"` (two
      classes); the regex requires an exact match up to the closing quote,
      so it never collides with the films list below.
    - `<ul class="wynikiszukania">` -- films/TV/theatre. Because this
      regex requires the attribute value to be *exactly* `wynikiszukania`
      (immediately followed by the closing `"`), it does **not**
      accidentally match the people `<ul>` even though that class string
      also contains the substring `wynikiszukania`.
  - Inside each `<li>`, the site sometimes emits **more than one**
    `index.php/{id}` link per row (e.g. a thumbnail link and a text link).
    The parser takes the **last** link with non-empty text, matching TS's
    `let last = ...` loop-and-overwrite pattern exactly.
  - An optional `<div class="rodzajfilmu">...</div>` per `<li>` supplies a
    `hint` (people) or `details` (films) field -- kind of film, or a short
    descriptor.
  - Empty result page: detected via `<b>Nic nie znalazłem</b>` (case
    insensitive), returned as `{"people": [], "films": [],
    "empty_message": "Nic nie znalazłem"}`.
- Detail page: `index.php/{id}`. The record body is `<article
  id="film">...</article>` or `<article id="osoba">...</article>`
  depending on whether the id is a film or a person/institution. Extraction
  falls back to any `<article>`, then to `<main>`, if the specific
  `id="film|osoba"` article isn't found (mirrors `extractArticleHtml()`).
  If none of the three match, the script fails with a clear error
  (wrong id, or the site's layout changed) rather than silently returning
  nothing.
- `stripToPlain`/`decodeEntities` are ported verbatim (see "Shared
  stripToPlain/decodeEntities" below) and the resulting text is truncated
  to 25,000 chars (`MAX_RECORD_CHARS`, same constant as TS) with a
  `truncated: true` flag if cut.
- **Usage policy**: filmpolski.pl's terms restrict bulk copying of database
  content. `filmpolski.py` prints a one-line, non-blocking reminder to
  stderr on every `search` and `get-item` call ("...use short excerpts
  only and cite filmpolski.pl as the source"), and `get-item` never returns
  more than the capped excerpt above -- never the full page.

## Fototeka Śląska (`fototeka_slaska.py`) -- DIRECT PORT of TS parsing

`https://fototekaslaska.pl/` -- Muzeum Wsi Opolskiej (rural Silesia /
Opole region historical photos). WordPress site; a general `/wp-json/`
exists but the gallery custom post type has no public `wp/v2/{type}`
endpoint for individual records (404). This is the **other** source where
the TS tool does real HTML parsing, ported field-for-field.

- Search: `GET /?s={query}&t={field}&y={year_period}&paged={page}` (`y`
  and `paged` omitted when not applicable; `paged` is only sent when
  `page > 1`).
  - `t` (`field`): `title`, `place`, `district`, `description`,
    `catalog_n` (catalog number). Default `title`.
  - `y` (`year_period`, optional): `do1900`, `1900-1918`, `1918-1939`,
    `1939-1945`. Omit for all periods.
- **Critical parsing detail**: the homepage renders search results AND a
  "recently added" section on the same page. The parser must isolate
  **only** the `<div class="search-list">...</div>` block, specifically
  the region up to (but not including) `<h3 class="serch-recently-added">`
  (note: "serch", not "search" -- that's the site's own typo, preserved
  here because it's what's actually in the markup). Getting this wrong
  means "recently added" photos leak into search results. The regex is:
  `<div class="search-list">([\s\S]*?)<h3 class="serch-recently-added">`.
- No-results detection: `class="result-empty"` or the text "Nic nie
  znaleziono" anywhere in the page; the empty message is read from
  `<div class="result-empty">...`.
- Each result tile: `<div class="gallery-listing-single"><a href="...">
  ...</a></div>`. The `href` yields the `slug` (segment after
  `/galeria/`), an optional `image_url` (prefers `data-src` over `src`,
  for lazy-loaded images), and a `caption` from
  `<div class="gallery-listing-details">`.
- Photo detail page (`/galeria/{slug}/`):
  - `title`: `<div class="...single-gallery...">​<h2>...</h2>`.
  - `catalog_note`: `<p class="single-gallery-n">...</p>`.
  - `image_url`: prefers `<a class="gallery-listing-box...">` linking
    directly to a `.jpg/.jpeg/.png/.webp` file; falls back to
    `<img class="lazy single-gallery-image" data-src="...">`.
  - `details_text`: `<div class="single-gallery-details">...</div>`
    stripped to plain text, capped at 20,000 chars (`MAX_DETAIL_CHARS`,
    matches TS) with an `"… [truncated]"` suffix when cut.
  - If neither `title` nor `details_text` come back non-empty, the script
    fails with a clear error (layout changed, or bad slug) instead of
    returning an empty-looking success payload.
- `slug` handling: leading/trailing slashes and an optional leading
  `galeria/` prefix are stripped from the CLI `--slug` value before
  building the URL, matching the TS tool's `slug.replace(...)` logic.
- Respect the museum's copyright/terms: do not bulk-download image files.

## Repozytorium Cyfrowe FN (`fn_repozytorium.py`)

`https://repozytorium.fn.org.pl/` -- Drupal 7 + Apache Solr, no public
JSON API. All four MCP tools it ports (`fn_repo_search`, `fn_repo_get_node`,
`fn_repo_film_index`, `fn_repo_browse_kind`) return **raw, unparsed HTML**
in the original TS source -- there is no reference parsing logic to port
here, only URL construction. This script reproduces that URL construction
exactly (including a URL-encoding quirk, see below) and adds new
best-effort tile/detail extraction for usability.

- All four tools funnel through Drupal's `?q=` clean-URL parameter, e.g.
  `?q=pl/node/8937` or `?q=pl/search/site/warszawa`.
- **Double-encoding quirk, reproduced deliberately**: for `search` and
  `film-index`, the TS source calls `encodeURIComponent()` on the
  query/letter to build the inner path segment, and THEN hands the whole
  resulting string to `URLSearchParams.set("q", ...)`, which percent-encodes
  it a *second* time (e.g. a literal `%` in the first pass becomes `%25` in
  the final URL). `build_site_search_url()` and `build_film_index_url()` in
  `fn_repozytorium.py` reproduce this exactly via a `urllib.parse.quote()`
  pre-pass followed by `urlencode()`, since this is what the live site
  actually receives from the original tool and presumably works against
  Drupal's own query-string decoding. `get-node` and `browse-kind` do NOT
  have this quirk in the TS source (no `encodeURIComponent` pre-pass), so
  their Python equivalents only encode once.
- `search` facets: passed as repeated `--facet field:value` (e.g. `--facet
  bundle:doc` for documentaries, `bundle:feature` for fiction,
  `bundle:article`, `bundle:person`, or `sm_field_year:1964`), rendered as
  `f[0]=...&f[1]=...` query params, matching Solr's faceted-search URL
  convention used by the site's own facet links.
- `film-index --letter`: `A`-`Z`, Polish letters (`Ą Ć E Ł Ń Ó Ś Ź Ż`), or
  `-` (dash) for the "INNE" (other/uncategorized) bucket. The dash is
  passed through literally (not percent-encoded) since it's a proper URL
  path character.
- `browse-kind --kind`: `feature` (fabularne/fiction), `doc`
  (dokumentalne/documentary), `animation` (animacje), `magazine` (magazyn
  filmowy/newsreel magazine) -- these are the TS tool's own English kind
  identifiers mapped onto `search/{kind}` paths.
- New extraction (`items` for search/film-index/browse-kind,
  `title`/`text`/`related_nodes` for get-node): uses the same
  `extract_id_links(html, "node", base_url=ORIGIN)` heuristic as Gapla/
  Fototeka above -- any anchor whose `href` contains `node/{numeric-id}`
  anywhere (so `?q=pl/node/8937` matches, since the fragment search is a
  substring match), deduplicated by id. This is intentionally generic
  because the exact Drupal theme/markup on repozytorium.fn.org.pl could
  not be verified live; `raw_html` (capped 20,000 chars) is always
  included as a fallback for all four subcommands.

## Shared `stripToPlain`/`decodeEntities` (ported to `_http.py`)

`filmpolski.ts` and `fototekaslaska.ts` in the source repo each define
byte-for-byte identical `decodeEntities()`/`stripToPlain()` helper
functions. They're ported once into `_http.py` as `decode_entities()` /
`strip_to_plain()` and reused by every script in this skill (including the
new best-effort extractors for Gapla/Fototeka/Repozytorium, where no TS
reference existed): drop `<script>`/`<style>` bodies, turn `<br>` and
block-closing tags (`p`, `div`, `h1`-`h6`, `li`, `tr`) into newlines, strip
all remaining tags, decode a small fixed set of entities (`&nbsp;`,
`&amp;`, `&lt;`, `&gt;`, `&#8211;`, `&#8217;`, numeric `&#NNN;`/`&#xHH;`),
then collapse repeated whitespace and blank lines.

## Network policy (`_http.py`)

Matches `cache.ts` in the source project:
- 30 second timeout per attempt.
- Exactly one retry, and only for transient network-level errors
  (`urllib.error.URLError`, `TimeoutError`, `OSError` -- DNS failures,
  connection resets, timeouts). Never retried: HTTP 4xx/5xx responses
  (`urllib.error.HTTPError`), which raise immediately with the status code
  and a short (<=1024 char) body snippet.
- `User-Agent: polish-academic-skills/1.0
  (+https://github.com/asterixix/polish-academic-skills)` on every request.
- No response caching in this port (the TS project caches in Cloudflare
  KV; a standalone skill has no equivalent store, so every call hits the
  network directly).
