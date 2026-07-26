# Reference: source APIs, parameters, and HTML-scraping fragility

This file holds the fiddly per-source details that don't belong in
SKILL.md: exact endpoints, parameter names, and — for the HTML-scraping
sources — what is actually parsed, how, and where it might break.

All five sources are ported from the original TypeScript MCP server
(asterixix/polish-academic-mcp, `src/tools/isap.ts`, `sejm-bs.ts`, `saos.ts`,
`pkn.ts`, `wiedza.ts`). Where this port adds something the original TS code
did not do (e.g. actually parsing HTML instead of returning it raw), that is
called out explicitly below.

---

## 1. ISAP / ELI API (`isap.py`)

- Base: `https://api.sejm.gov.pl/eli` — a real JSON API, no key, run by the
  Sejm. OpenAPI docs: https://api.sejm.gov.pl/eli/openapi/
- `search-acts` -> `GET /acts/search` with query params: `title`, repeated
  `keyword` (split from a comma-separated `--keyword` string — this matches
  an ISAP controlled-vocabulary tag, not free text), `year`, `publisher`
  (e.g. `DU`, `MP`), `type` (e.g. `Ustawa`, `Rozporzadzenie`), `position`,
  `volume`, `inForce=1` (only if `--in-force` passed), `dateFrom`/`dateTo`,
  `dateEffectFrom`/`dateEffectTo`, `pubDateFrom`/`pubDateTo`, `limit`
  (1-100, default 20; upstream API's own default is 500), `offset`,
  `sortBy` (`publisher|position|title|change`), `sortDir` (`asc|desc`).
- `get-act` -> `GET /acts/{publisher}/{year}/{position}`. The `--eli` value
  (e.g. `DU/2026/370`) is split on `/`, each segment is percent-encoded
  independently, and a defensive check rejects `..` segments or fewer than
  3 segments — this mirrors `eliToPath()` in `isap.ts` exactly.
- Response is passed through as JSON (`items[].ELI`, `title`,
  `displayAddress`, `texts`, `references`, etc.) — no local parsing needed.

## 2. Biblioteka Sejmowa OPAC (`biblioteka_sejmowa.py`)

- Base: `https://bs.sejm.gov.pl/F` — an **Aleph** OPAC. No JSON API, no
  documented SRU endpoint. This is a completely different Sejm service from
  api.sejm.gov.pl/ISAP above; do not confuse the two.
- `search` -> `GET /F?func=find-b&local_base=...&request=...&find_code=...&adjacent=...`.
  - `local_base` examples: `bis01` (main catalog), `bis02`, `bis03`,
    `bis05` (journal articles), `pos01` (Sejm session recordings), `tek01`
    (constitutional texts), `sta01` (old prints), `ars01`. The full list is
    on the OPAC's own landing page; this skill does not hardcode it.
  - `find_code`: `WRD` = all fields (default), `WST` = title, `WHF` =
    author, `WNW` = publisher, `WMW`, `WSE`, `WHP` = subject heading,
    `WTE`, `TXT`, `SYS` = record number, `WOB`.
  - Only the first results page is returned; narrow the query or increase
    specificity rather than expecting pagination.
- `get-item` -> `GET /F?func=item-global&doc_library=...&doc_number=...&year=...&volume=...&sub_library=...`.
  `doc_library`/`doc_number` (and, rarely, `year`/`volume`) must come
  **exactly** from an `item-global` link in a `search` result — they are
  not guessable. `sub_library` is usually `BS`.
- **Parsing note (enhancement beyond the original TS tool):** the original
  `bs_sejm_search` just returns the raw HTML result page and relies on the
  calling LLM to read `doc_library`/`doc_number` out of the `item-global`
  links by eye (per its tool description text). This port additionally
  runs an `html.parser.HTMLParser` subclass (`ItemGlobalLinkParser` in
  `biblioteka_sejmowa.py`) over the page: it collects every `<a>` tag whose
  `href` contains `func=item-global`, parses that link's query string for
  `doc_library`, `doc_number`, `sub_library`, `year`, `volume`, and pairs it
  with the anchor's visible text, de-duplicating repeated links to the same
  record (Aleph often renders more than one link per hit row, e.g. an icon
  plus a text link). The result is exposed as a `hits` array alongside the
  full `html` body. **This extraction rule is inferred from the tool's
  documented usage pattern, not a literal TS selector** (no such selector
  exists in the original code) — treat `hits` as a best-effort convenience
  and fall back to reading `html` directly if the markup ever changes.

## 3. SAOS (`saos.py`)

- Base: `https://www.saos.org.pl/api` — public JSON API, no key.
- Two independent sub-APIs under the same base — kept as clearly separate
  subcommand groups:
  - **Search & detail** (`search-judgments`, `get-judgment`): for normal
    "find some judgments" / "get this one judgment" use. `search-judgments`
    accepts a long list of filters mirroring `buildSearchJudgmentsParams()`
    in `saos.ts` 1:1 (see `saos.py --help` for the full flag list): free
    text (`--all`), paging (`--page-size` 10-100, `--page-number`),
    sorting, legal-basis/regulation/law-journal-entry text filters, judge
    name, exact case number, common-court filters (`--cc-*`), Supreme Court
    filters (`--sc-*`), `--judgment-types` (comma-separated, OR-matched:
    `DECISION,RESOLUTION,SENTENCE,REGULATION,REASONS`), `--keywords`
    (comma-separated, AND-matched, exact spelling), and a judgment-date
    range.
  - **Bulk dump API** (`dump-services`, `dump-common-courts`,
    `dump-sc-chambers`, `dump-judgments`, `dump-enrichments`): for
    wholesale mirroring/syncing, documented at
    https://www.saos.org.pl/help/index.php/dokumentacja-api/api-pobierania-danych.
    **`dump-judgments` returns full judgment records per row and can
    produce very large responses** — always pass a narrow
    `--judgment-start-date`/`--judgment-end-date` window and a small
    `--page-size` (10-20). It is not a substitute for `search-judgments`.
- SAOS periodically enters a "Przerwa techniczna" (scheduled maintenance)
  mode where `search-judgments` may hang or fail; `dump-judgments` with a
  narrow date range is the documented workaround, and `search-judgments`'s
  error message in this script points that out.
- The original TS `saos_search_judgments` tool used a tighter 20s
  per-request timeout (distinct from the general 30s policy) specifically
  to fail fast during those maintenance windows. This port uses the
  standard shared 30s timeout/retry-once policy uniformly across all
  scripts in this skill for simplicity; if SAOS search hangs near the 30s
  mark, that is expected and `dump-judgments` is the fallback either way.

## 4. PKN website search (`pkn.py`)

- Base: `https://www.pkn.pl` — Drupal + Search API/Solr. No JSON API
  (`/jsonapi` returns 404).
- `search` -> `GET {path}?szukaj=...&sort_by=...&page=...` where `path` is
  `/wyszukiwarka` (pl), `/en/search` (en), or `/ru/poisk` (ru). `sort_by`
  is `search_api_relevance` (default) or `changed`. `page` is 0-based.
- This does **not** search the WIEDZA norms catalog (see below) — it's
  general site content (news, sections, etc.).
- **Parsing note:** the original TS tool returns the raw HTML page
  unparsed, and there is no documented/stable CSS class structure for
  pkn.pl's Drupal search results to mirror confidently (unlike the
  Biblioteka Sejmowa case, the tool description here doesn't name a
  specific link pattern either). This port adds a generic
  `html.parser.HTMLParser` subclass (`LinkCollector`) that just gathers
  every `<a href>`/text pair on the page into a `links` array as a rough
  aid — it is **not** scoped to "just the result list" the way the
  Biblioteka Sejmowa parser is, so expect navigation/footer links mixed
  in. `html` is always included and is the authoritative source; treat
  `links` as a coarse hint only.

## 5. WIEDZA-PKN norms catalog (`wiedza.py`)

- Base: `https://wiedza.pkn.pl` — **Liferay 6.1** portal, unrelated to
  `pkn.py` above (different subdomain, different backend, different
  content — Polish Standards/PN metadata, not general site content).
- No JSON API. Every call requires a fresh two-step session:
  1. `GET` a locale-specific landing page (`/web/guest/wyszukiwarka-norm`
     pl, `/en/wyszukiwarka-norm` en, `/ru/wyszukiwarka-norm` ru) to obtain
     a Liferay session cookie (via `Set-Cookie`) and scrape two values out
     of the HTML with regexes that mirror `wiedza.ts` **exactly**:
     - `parse_auth_token`: `Liferay\.authToken = '([^']+)'`
     - `parse_form_date` (search only): a hidden input named
       `{PORTLET_PREFIX}_formDate` — full prefix is
       `_searchstandards_WAR_p4scustomerpknzwnelsearchstandardsportlet`.
  2. Either `POST` (search) or `GET` (standard detail) the portlet's
     resource URL (`/wyszukiwarka-norm?p_auth=...&p_p_id=...&...`), with
     the session cookie attached and a `Referer` header pointing back at
     the landing page.
- **Session implementation:** rather than manually copying `Set-Cookie`
  into a `Cookie` header (what the TS code does, since `fetch` doesn't
  auto-manage cookies across manual calls), this port uses
  `http.cookiejar.CookieJar` + `urllib.request.build_opener(HTTPCookieProcessor(jar))`
  (see `build_cookie_opener()` in `_http.py`) so the landing-page GET and
  the follow-up POST/GET automatically share cookies the way a browser
  would — still 100% standard library, just a different (arguably more
  idiomatic-for-Python) mechanism to reach the same end state. If the
  landing GET returns no cookies at all, both subcommands raise a
  `RuntimeError` immediately (mirrors the two explicit checks in
  `wiedza.ts`).
- `search-norms` requires at least one non-empty criterion among: standard
  number, title (PL/EN), content, ICS, sector, technical committee,
  directive, introducing-standard, **or** a publish/withdrawal date range —
  mirrors the zod `.refine()` validation in `wiedzaSearchSchema` in
  `wiedza.ts`. `--title-match phrase` sends `searchType=2` (exact phrase),
  `words` (default) sends `searchType=1`.
- `get-standard` needs the *exact* standard number string as it appears in
  a `search-norms` result (e.g. `PN-EN ISO 9001:2015-10F`, usually with a
  version-language suffix) — it is not a fuzzy lookup.
- **No caching, by design:** the original tool explicitly skips the shared
  KV cache used by every other tool in the source MCP server, because each
  session's `p_auth` token and cookie are short-lived and tied to that one
  GET. This standalone script has no cache layer at all, but the same
  reasoning applies — don't try to reuse a token/cookie pair across
  separate invocations of this script; each run does its own fresh
  session bootstrap (2 HTTP round-trips minimum per subcommand call).

---

## General HTTP policy (all scripts, `_http.py`)

- `User-Agent: polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)`
  on every request (search/detail *and* the WIEDZA session GET).
- 30-second timeout per request.
- Exactly one automatic retry, and only for transient network-level
  failures (connection reset/refused, unreachable network, timeouts) — an
  HTTP 4xx or 5xx response is never retried by the transport layer; the
  script surfaces it as a `RuntimeError` with the status code and a body
  snippet (truncated) so the caller can decide what to do next.
- All scripts print a single JSON object to stdout via
  `json.dumps(result, ensure_ascii=False, indent=2)` on success, and print
  `Error: ...` to stderr + exit 1 on failure.
