# polish-academic-skills

Zestaw samodzielnych **Agent Skills** (otwarty standard `SKILL.md` promowany
przez Anthropic, wspierany m.in. przez Claude Code, Claude.ai/Cowork, Cursor,
Codex CLI, Gemini CLI, GitHub Copilot i OpenCode) udostępniających polskie
bazy naukowe, publiczne i kulturowe.

To port narzędzi z serwera MCP [`polish-academic-mcp`](https://github.com/asterixix/polish-academic-mcp)
(autor: [asterixix](https://github.com/asterixix)) do formy **niezależnej od
MCP** — każdy skill to folder z `SKILL.md` + skryptami Python 3 (**tylko
biblioteka standardowa, zero zależności zewnętrznych**), które agent
uruchamia bezpośrednio jako CLI. Nie trzeba konfigurować żadnego serwera MCP
ani nic instalować przez `pip`/`npm` — wystarczy Python 3.9+.

> Ten projekt nie jest oficjalnie powiązany z żadną z wymienionych baz danych
> ani z Anthropic. To niezależny, otwarty port publicznych API/zasobów.

To repo jest też **Claude Code Plugin Marketplace** (`.claude-plugin/marketplace.json`)
— najszybszy sposób na instalację to `claude plugin marketplace add
asterixix/polish-academic-skills`, patrz [Instalacja](#instalacja).

---

## Dostępne skille

| Skill | Zakres | Źródła |
| --- | --- | --- |
| [`polish-academic-repositories`](skills/polish-academic-repositories/SKILL.md) | Repozytoria naukowe uczelni i dane badawcze | Biblioteka Nauki, RCIN, RUJ (UJ), AGH, AMU (UAM), UAFM, ICM Open, RODBuK, RePOD, Depot CeON, PPM, EMIS/ELibM |
| [`polish-science-bibliography`](skills/polish-science-bibliography/SKILL.md) | Bibliografia naukowa i profile badaczy | PBN, POL-on/RAD-on, Ludzie Nauki (następca nauka-polska.pl) |
| [`polish-open-data-statistics`](skills/polish-open-data-statistics/SKILL.md) | Dane otwarte i statystyka publiczna | dane.gov.pl, BDL/GUS (w tym dane ze stat.gov.pl) |
| [`polish-weather-hydrology`](skills/polish-weather-hydrology/SKILL.md) | Pogoda i hydrologia w czasie rzeczywistym | IMGW-PIB |
| [`polish-legal-normative-documents`](skills/polish-legal-normative-documents/SKILL.md) | Akty prawne, orzeczenia sądów, normy | ISAP/ELI, Biblioteka Sejmowa, SAOS, PKN, WIEDZA-PKN |
| [`polish-culture-archives`](skills/polish-culture-archives/SKILL.md) | Dziedzictwo kulturowe i archiwa | Baza Legalnych Źródeł, BazTOL, NAC, Katalog ŚUM (Aleph), PAUart, Wolne Lektury, Dokumenty Śląska, Ofiary IPN, EDUKATOR, Academica, Chmura Czytania |
| [`polish-film-heritage`](skills/polish-film-heritage/SKILL.md) | Dziedzictwo filmowe i fotograficzne | Ninateka, Gapla, Fototeka, FilmPolski.pl, Fototeka Śląska, Repozytorium FN |
| [`polish-educational-resources`](skills/polish-educational-resources/SKILL.md) | Otwarte podręczniki szkolne K-12 | epodreczniki.pl (ORE/MEN) |

Każdy folder skilla zawiera `SKILL.md` (opis + instrukcje dla agenta),
`scripts/` (skrypty CLI) i często `reference/API.md` (szczegóły parametrów,
dla tych, które byłyby zbyt długie w `SKILL.md`).

**Przeszukiwanie wszystkich źródeł naraz:** sześć skilli z więcej niż jednym
źródłem (`polish-academic-repositories`, `polish-culture-archives`,
`polish-film-heritage`, `polish-legal-normative-documents`,
`polish-open-data-statistics`, `polish-science-bibliography`) ma skrypt
`scripts/search_all.py`, który odpytuje równolegle wszystkie źródła danego
skilla dla jednego zapytania i zwraca połączony JSON — `SKILL.md` każdego z
nich jawnie instruuje agenta, żeby dla szerokich zapytań użył najpierw
właśnie tego skryptu, zamiast poprzestawać na pierwszym trafionym źródle.

---

## Wymagania

- **Python 3.9+** (tylko biblioteka standardowa — `urllib`, `json`,
  `xml.etree.ElementTree`, `html.parser`, `argparse`; brak zależności do
  instalacji).
- Większość źródeł **nie wymaga kluczy API**. Wyjątki:
  - **PBN** (`polish-science-bibliography/scripts/pbn.py`) — wymaga
    `PBN_APP_ID` + `PBN_APP_TOKEN` (opcjonalnie `PBN_USER_TOKEN`). Rejestracja:
    [Open API PBN](https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/).
  - **BDL/GUS** (`polish-open-data-statistics/scripts/bdl.py`) — działa
    anonimowo, ale opcjonalny `BDL_CLIENT_ID` (nagłówek `X-ClientId`) daje
    wyższe limity. Rejestracja: [Portal API GUS](https://api.stat.gov.pl/home/bdlapi).

---

## Instalacja

### Claude Code — przez Plugin Marketplace (zalecane)

To repo jest jednocześnie **marketplace pluginów** Claude Code
(`.claude-plugin/marketplace.json`). Każdy skill jest osobnym pluginem, więc
możesz zainstalować tylko te, których potrzebujesz, plus jeden plugin-zbiorczy
z wszystkimi ośmioma naraz.

```bash
# 1) Dodaj marketplace (raz)
claude plugin marketplace add asterixix/polish-academic-skills

# 2) Zainstaluj wybrany skill jako plugin
claude plugin install polish-weather-hydrology@polish-academic-skills

# ...albo wszystkie 8 naraz jednym pluginem
claude plugin install polish-academic-skills-all@polish-academic-skills
```

Te same komendy działają jako `/plugin marketplace add ...` i
`/plugin install ...` wewnątrz interaktywnej sesji Claude Code. Dostępne
nazwy pluginów (`<nazwa>@polish-academic-skills`):

`polish-academic-repositories`, `polish-science-bibliography`,
`polish-open-data-statistics`, `polish-weather-hydrology`,
`polish-legal-normative-documents`, `polish-culture-archives`,
`polish-film-heritage`, `polish-educational-resources`, oraz zbiorczy
`polish-academic-skills-all`.

Aktualizacja po zmianach w repo: `claude plugin marketplace update polish-academic-skills`
(albo `claude plugin update <nazwa-pluginu>`).

### Ręczne kopiowanie folderu (dla innych agentów / bez Claude Code)

Skille rozpoznaje każdy agent zgodny z otwartym standardem Agent Skills —
wystarczy skopiować folder danego skilla (`skills/<nazwa>/`) do właściwego
katalogu skilli danego narzędzia.

#### Claude Code (bez marketplace)

```bash
# Osobiste (dostępne we wszystkich projektach)
cp -r skills/polish-weather-hydrology ~/.claude/skills/

# Projektowe (tylko w danym repo, wersjonowane z projektem)
cp -r skills/polish-weather-hydrology .claude/skills/
```

Możesz skopiować dowolną liczbę folderów — każdy skill jest niezależny.

#### Claude.ai / Claude Cowork (Skills)

W ustawieniach **Settings → Capabilities → Skills** (plan Pro/Team/Enterprise)
spakuj wybrany folder skilla do `.zip` (zawartość folderu, nie sam folder
nadrzędny) i wgraj przez "Upload skill". Więcej:
[Creating custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills).

#### Cursor

```bash
cp -r skills/polish-weather-hydrology ~/.cursor/skills/   # globalnie
cp -r skills/polish-weather-hydrology .cursor/skills/     # per projekt
```

#### Codex CLI (OpenAI)

```bash
cp -r skills/polish-weather-hydrology ~/.codex/skills/    # globalnie
cp -r skills/polish-weather-hydrology .codex/skills/      # per projekt
```

#### GitHub Copilot (agent skills)

```bash
cp -r skills/polish-weather-hydrology .github/skills/
```

#### Gemini CLI, OpenCode i inne

Większość pozostałych hostów zgodnych ze standardem Agent Skills honoruje
też uniwersalną, międzynarzędziową ścieżkę:

```bash
cp -r skills/polish-weather-hydrology .agents/skills/
```

Sprawdź dokumentację danego narzędzia, jeśli używa innej konwencji katalogu.

---

## Jak to działa

Skrypty to zwykłe CLI:

```bash
python3 scripts/imgw.py synop --station-name warszawa
python3 scripts/bdl.py search-subjects --name "ludność"
```

Zwracają JSON na `stdout`. Błędy (HTTP, sieciowe, braki poświadczeń) trafiają
na `stderr` z kodem wyjścia różnym od zera. Każdy request ma nagłówek
`User-Agent: polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)`,
timeout 30s i pojedynczy retry tylko dla przejściowych błędów sieciowych
(nigdy dla 4xx). Pełne parametry i przykłady — patrz `SKILL.md` każdego
skilla oraz, gdzie dotyczy, `reference/API.md`.

## Ograniczenia

Kilka źródeł (m.in. w `polish-culture-archives` i `polish-film-heritage`) nie
udostępnia publicznego JSON API i skrypty parsują HTML — to z natury bardziej
kruche niż wywołanie REST i może się zepsuć przy zmianie layoutu strony.
Szczegóły i status poszczególnych źródeł (np. katalogi nieaktualizowane od
lat) są opisane w `SKILL.md` odpowiedniego skilla.

`ppm.py` (`polish-academic-repositories`) ma nie w pełni zweryfikowany
adres bazowy OAI-PMH — patrz docstring skryptu i uruchom `identify` przed
`search`/`get`.

`ofiary_ipn.py`, `bgbase_edu.py` i `academica.py` (`polish-culture-archives`)
mają potwierdzone na żywo nazwy pól formularzy/endpointy (dla `academica.py`
także cały dwuetapowy przepływ JSF/RichFaces z ciasteczkiem sesji i
`javax.faces.ViewState`), ale nie widziano jeszcze strony z realnymi
trafieniami — struktura pojedynczego rekordu w wynikach nie jest jeszcze
sparsowana, skrypty zawsze zwracają też surowy HTML. `emis.py`
(`polish-academic-repositories`) to czysty katalog statyczny — potwierdzono
na żywo, że nie ma tam żadnego wyszukiwania ani API. `chmuraczytania.py`
(`polish-culture-archives`) też nie ma wyszukiwania po stronie serwera —
potwierdzony na żywo katalog (`catalog.php`) jest w pełni sparsowany
(id/tytuł/autor), a `search` filtruje po tytule/autorze po stronie klienta,
przechodząc kolejne strony katalogu.

**`archiwa.gov.pl` / `szukajwarchiwach.gov.pl` — sprawdzone i odrzucone.**
Oba adresy są za Incapsula (WAF przeciw botom) na poziomie HTTP, nie tylko
JS w przeglądarce — nawet zwykły `curl`/`Invoke-WebRequest` dostaje pustą
stronę z wyzwaniem `_Incapsula_Resource` zamiast treści. Obejście wymaga
prawdziwej przeglądarki (headless) wykonującej JS, co łamie założenie tego
projektu "tylko biblioteka standardowa, zero zależności" — nie będzie tu
zaimplementowane, chyba że ktoś zaakceptuje dodanie takiej zależności.

**infona.pl — pominięte na życzenie** (nie jest obecnie priorytetem;
strona zresztą i tak nie ma `<form>` na stronie głównej, wyszukiwanie idzie
przez JS — do ewentualnego podjęcia w przyszłości potrzebne "Copy as cURL"
z devtools).

**Źródła nadal czekające na kolejną rundę testów na żywo**:
powstania.pilsudski.org — `ajax_req.js` potwierdza generyczny mechanizm AJAX
(`{url_base}/ajax_req.php?aaction=<action>&...`, gdzie `url_base =
https://powstania.pilsudski.org`), ale konkretna nazwa `action` używana przy
wyszukiwaniu osób nie jest w tym pliku — jest w `js/front.js` albo w inline
`<script>` na stronie `/osoby`. Potrzebny albo `front.js`, albo fragment
strony `/osoby` z wywołaniami `JSONAsyncRequest`/`aaction=`.

## Źródło i licencja

Logika API/parsowania jest portem z [`polish-academic-mcp`](https://github.com/asterixix/polish-academic-mcp)
(MIT, © Artur Sendyka). Ten projekt jest wydany na tej samej licencji — patrz
[`LICENSE`](LICENSE).
