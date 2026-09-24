# polish-academic-skills

Osiem **umiejętności (Agent Skills)** dla asystentów AI — Claude, Codex,
Gemini CLI, Cursor, GitHub Copilot, OpenCode i innych — które dają im
dostęp do polskich baz naukowych, publicznych i kulturowych: repozytoriów
uczelni, PBN, GUS, IMGW, ISAP, SAOS, archiwów filmowych, e-podręczników
i wielu innych.

Po instalacji wystarczy zapytać asystenta zwykłym językiem, np. *„Znajdź
publikacje o sztucznej inteligencji w polskich repozytoriach naukowych”*
albo *„Jaka jest teraz pogoda w Krakowie według IMGW?”* — asystent sam
wybierze właściwy skill i przeszuka źródła.

- **Bez serwera MCP i bez instalowania bibliotek** — każdy skill to folder
  z instrukcją (`SKILL.md`) i skryptami w Pythonie, które korzystają tylko
  z biblioteki standardowej. Wystarczy Python 3.9+.
- **Większość źródeł nie wymaga kluczy API** (wyjątki: PBN, opcjonalnie GUS BDL).
- To port narzędzi z serwera MCP [`polish-academic-mcp`](https://github.com/asterixix/polish-academic-mcp)
  (autor: [asterixix](https://github.com/asterixix)).

> Ten projekt nie jest oficjalnie powiązany z żadną z wymienionych baz
> danych ani z Anthropic. To niezależny, otwarty port publicznych API/zasobów.

---

## Szybki start

**Krok 1. Wybierz swoje narzędzie:**

| Korzystasz z… | Zrób to | Czas |
| --- | --- | --- |
| **Claude Desktop** lub **claude.ai** (czat, Cowork) | [pobierz pliki ZIP i wgraj je w ustawieniach](#claude-desktop-i-claudeai) | ~5 min |
| **Claude Code** (terminal lub zakładka *Code* w Claude Desktop) | [dwie komendy](#claude-code) | ~1 min |
| **Codex**, **Gemini CLI**, **Cursor**, **GitHub Copilot**, **OpenCode**, **Windsurf** | [instalator jednym poleceniem](#instalator-jednym-poleceniem) | ~1 min |
| inne narzędzie zgodne z Agent Skills | [`npx skills`](#npx-skills) albo [instalacja ręczna](#instalacja-ręczna) | ~2 min |

**Krok 2. Upewnij się, że masz Pythona** (nie dotyczy Claude Desktop /
claude.ai — tam skrypty działają na serwerach Anthropic):

- **Windows** — zainstaluj *Python 3.13* ze sklepu Microsoft Store albo
  z [python.org](https://www.python.org/downloads/) (w instalatorze zaznacz
  **„Add python.exe to PATH”**).
- **macOS** — otwórz Terminal i wpisz `python3 --version`. Jeśli system
  zaproponuje instalację „narzędzi wiersza poleceń” — zgódź się. Jeśli
  instalujesz Pythona z python.org, uruchom potem raz
  `Install Certificates.command` z folderu *Programy → Python 3.x*.
- **Linux** — Python 3 jest zwykle już zainstalowany.

**Krok 3. Zrestartuj narzędzie (albo otwórz nową rozmowę) i zapytaj** —
przykłady w sekcji [Jak z tego korzystać](#jak-z-tego-korzystać).

---

## Instalacja

### Claude Desktop i claude.ai

W czacie Claude (w przeglądarce, w aplikacji Claude Desktop i w Cowork)
skille wgrywa się jako pliki ZIP — każdy skill osobno.

1. **Pobierz ZIP-y** skilli, których potrzebujesz (nie rozpakowuj ich):

   | Skill | Plik do pobrania |
   | --- | --- |
   | Repozytoria naukowe uczelni i dane badawcze | [polish-academic-repositories.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-academic-repositories.zip) |
   | Bibliografia naukowa i profile badaczy (PBN, POL-on, Ludzie Nauki) | [polish-science-bibliography.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-science-bibliography.zip) |
   | Dane otwarte i statystyka (dane.gov.pl, GUS BDL) | [polish-open-data-statistics.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-open-data-statistics.zip) |
   | Pogoda i hydrologia (IMGW) | [polish-weather-hydrology.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-weather-hydrology.zip) |
   | Prawo, orzeczenia i normy (ISAP, SAOS, PKN…) | [polish-legal-normative-documents.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-legal-normative-documents.zip) |
   | Dziedzictwo kulturowe i archiwa | [polish-culture-archives.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-culture-archives.zip) |
   | Film i fotografia (FINA, FilmPolski…) | [polish-film-heritage.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-film-heritage.zip) |
   | E-podręczniki (epodreczniki.pl) | [polish-educational-resources.zip](https://github.com/asterixix/polish-academic-skills/releases/latest/download/polish-educational-resources.zip) |

   Linki prowadzą do najnowszego wydania ([Releases](https://github.com/asterixix/polish-academic-skills/releases)).
   Jeśli nie działają (np. przed pierwszym wydaniem), możesz zbudować ZIP-y
   sam: pobierz repozytorium (*Code → Download ZIP*), rozpakuj i uruchom
   `python3 install.py --zip` (Windows: `python install.py --zip`) — pliki
   trafią do podfolderu `polish-academic-skills-zips` w folderze *Pobrane*
   (`Downloads`), a instalator wypisze ich dokładne położenie.

2. W Claude otwórz **Customize → Skills → Add** (w starszych wersjach:
   *Settings → Capabilities → Skills*) i wskaż pobrany plik ZIP. Powtórz dla
   każdego skilla.

3. **Pozwól Claude łączyć się z polskimi serwerami.** Skrypty pobierają
   dane z internetu, a domyślnie Claude ma zwykle dostęp najwyżej do
   repozytoriów pakietów. W **Settings → Capabilities** znajdź ustawienie wykonywania
   kodu (*Code execution*) i **Allow network egress**, a potem wybierz
   **All domains** albo dodaj domeny z [tabeli poniżej](#domeny-dla-claudeai).
   W planach Team i Enterprise to ustawienie zmienia administrator
   organizacji. Bez tego skill się uruchomi, ale każde zapytanie skończy się
   błędem sieci (np. `403 Forbidden`) — Claude powinien wtedy sam
   podpowiedzieć, które domeny odblokować.

4. Otwórz **nową rozmowę** i zapytaj.

#### Domeny dla claude.ai

| Skill | Domeny, do których skill musi mieć dostęp |
| --- | --- |
| `polish-academic-repositories` | bibliotekanauki.pl, rcin.org.pl, ruj.uj.edu.pl, api.repo.agh.edu.pl, repozytorium.amu.edu.pl, repozytorium.uafm.edu.pl, open.icm.edu.pl, rodbuk.pl, repod.icm.edu.pl, depot.ceon.pl, ppm.edu.pl, emis.icm.edu.pl |
| `polish-science-bibliography` | pbn.nauka.gov.pl, radon.nauka.gov.pl, ludzie.nauka.gov.pl |
| `polish-open-data-statistics` | api.dane.gov.pl, bdl.stat.gov.pl |
| `polish-weather-hydrology` | danepubliczne.imgw.pl |
| `polish-legal-normative-documents` | api.sejm.gov.pl, bs.sejm.gov.pl, www.saos.org.pl, www.pkn.pl, wiedza.pkn.pl |
| `polish-culture-archives` | bazalegalnychzrodel.pl, baztol.library.put.poznan.pl, www.nac.gov.pl, katalog.sum.edu.pl, www.pauart.pl, wolnelektury.pl, www.dokumentyslaska.pl, ofiary.ipn.gov.pl, bgbase.up.krakow.pl, academica.edu.pl, www.chmuraczytania.pl |
| `polish-film-heritage` | ninateka.pl, gapla.fn.org.pl, fototeka.fn.org.pl, www.filmpolski.pl, fototekaslaska.pl, repozytorium.fn.org.pl |
| `polish-educational-resources` | api.epodreczniki.pl, epodreczniki.pl |

Ta sama lista jest w polu `compatibility` każdego `SKILL.md`.

### Claude Code

To repozytorium jest też **marketplace pluginów Claude Code** — instalacja
tą drogą daje automatyczne aktualizacje.

```bash
# 1) Dodaj marketplace (raz)
claude plugin marketplace add asterixix/polish-academic-skills

# 2) Zainstaluj wszystkie 8 skilli jednym pluginem…
claude plugin install polish-academic-skills-all@polish-academic-skills

# …albo tylko wybrany skill
claude plugin install polish-weather-hydrology@polish-academic-skills
```

Wewnątrz sesji Claude Code (także w zakładce *Code* aplikacji Claude
Desktop) działają te same komendy z ukośnikiem: `/plugin marketplace add
asterixix/polish-academic-skills` i `/plugin install …`. Dostępne pluginy
(`<nazwa>@polish-academic-skills`): `polish-academic-repositories`,
`polish-science-bibliography`, `polish-open-data-statistics`,
`polish-weather-hydrology`, `polish-legal-normative-documents`,
`polish-culture-archives`, `polish-film-heritage`,
`polish-educational-resources` oraz zbiorczy `polish-academic-skills-all`.

Aktualizacja: `claude plugin marketplace update polish-academic-skills`
(albo `claude plugin update <nazwa-pluginu>`).

### Instalator jednym poleceniem

`install.py` sam sprawdza, które narzędzia AI masz na komputerze, kopiuje
do każdego z nich wszystkie skille i na koniec testuje połączenie
z polskimi serwerami. Działa na Windows, macOS i Linuksie.

**macOS / Linux** — wklej do Terminala:

```bash
curl -fsSL https://raw.githubusercontent.com/asterixix/polish-academic-skills/main/install.py | python3 -
```

**Windows** — wklej do PowerShella albo Wiersza polecenia:

```powershell
python -c "import urllib.request as u;exec(u.urlopen('https://raw.githubusercontent.com/asterixix/polish-academic-skills/main/install.py').read())"
```

**Bez terminala (Windows):** pobierz repozytorium (*Code → Download ZIP*),
rozpakuj i kliknij dwukrotnie **`install-windows.bat`**.

Instalator obsługuje te narzędzia (wykrywa je po folderze ustawień, który
tworzą przy pierwszym uruchomieniu):

| Narzędzie | Gdzie trafiają skille |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Cursor | `~/.cursor/skills/` |
| GitHub Copilot (CLI) | `~/.copilot/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| Windsurf | `~/.codeium/windsurf/skills/` |

Przydatne opcje (dopisz je na końcu polecenia — w wersji z `curl` po
`python3 -`, w wersji dla Windows po zamykającym cudzysłowie):

| Opcja | Co robi |
| --- | --- |
| `--agent codex` | instaluje tylko dla wskazanego narzędzia (`claude-code`, `codex`, `gemini-cli`, `cursor`, `github-copilot`, `opencode`, `windsurf`, `universal` = `~/.agents/skills`, `all`) |
| `--skill polish-weather-hydrology` | instaluje tylko wybrany skill (można powtórzyć) |
| `--project` | instaluje do bieżącego projektu (np. `.claude/skills/`) zamiast dla całego konta |
| `--target FOLDER` | instaluje do dowolnego folderu skilli (dla innych narzędzi) |
| `--zip` | buduje ZIP-y do wgrania w claude.ai / Claude Desktop |
| `--uninstall` | usuwa skille |
| `--list` | pokazuje skille i wykryte narzędzia, niczego nie zmienia |
| `--check` | tylko test połączenia z serwerami |

**Aktualizacja** — uruchom instalator ponownie. Nadpisuje tylko foldery
tych skilli i zachowuje Twój plik z kluczami API
([`polish-academic-skills.env`](#klucze-api-opcjonalne)).

### npx skills

Jeśli masz Node.js, uniwersalny instalator [`skills`](https://github.com/vercel-labs/skills)
obsługuje ponad 70 narzędzi i pozwala wybrać skille oraz narzędzia
z listy:

```bash
npx skills add asterixix/polish-academic-skills
```

Aktualizacja: `npx skills update`. W Gemini CLI możesz też użyć
wbudowanej komendy, osobno dla każdego skilla:
`gemini skills install https://github.com/asterixix/polish-academic-skills.git --path skills/polish-weather-hydrology`.

### Instalacja ręczna

Każdy skill to samodzielny folder `skills/<nazwa>/`. Skopiuj wybrane
foldery (w całości, razem z podfolderem `scripts/`) do katalogu skilli
swojego narzędzia:

| Narzędzie | Dla wszystkich projektów | Tylko dla jednego projektu |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenAI Codex | `~/.agents/skills/` | `.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` lub `~/.agents/skills/` | `.gemini/skills/` lub `.agents/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` lub `.agents/skills/` |
| GitHub Copilot | `~/.copilot/skills/` | `.github/skills/` lub `.agents/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` lub `.agents/skills/` |
| Windsurf | `~/.codeium/windsurf/skills/` | `.windsurf/skills/` |
| inne (Amp, Cline, Warp, Zed, Kilo…) | `~/.agents/skills/` | `.agents/skills/` |

`~` to Twój folder domowy (Windows: `C:\Users\<nazwa>`). Foldery
zaczynające się od kropki są ukryte — w Finderze pokażesz je skrótem
**Cmd+Shift+.**, w Eksploratorze Windows przez *Widok → Pokaż → Ukryte
elementy*.

```bash
cp -r skills/polish-weather-hydrology ~/.claude/skills/
```

---

## Jak z tego korzystać

Pytaj normalnie, po polsku lub po angielsku. Przykłady:

- *„Jaka jest teraz pogoda w Krakowie według IMGW? Czy są ostrzeżenia hydrologiczne?”*
- *„Znajdź publikacje o uczeniu maszynowym z ostatnich 3 lat w polskich repozytoriach naukowych.”*
- *„Znajdź rozprawy doktorskie o klimacie w repozytorium UJ.”*
- *„Ile osób mieszka w Poznaniu według GUS? Pokaż dane z ostatnich lat.”*
- *„Znajdź ustawę o ochronie danych osobowych w ISAP i orzeczenia sądów na ten temat.”*
- *„Pokaż plakaty i fotosy do filmów Andrzeja Wajdy.”*
- *„Znajdź na Wolnych Lekturach utwory Bolesława Prusa.”*
- *„Znajdź e-podręcznik do biologii dla szkoły podstawowej.”*
- *„Kim są badacze zajmujący się sztuczną inteligencją w Krakowie? (Ludzie Nauki)”*

Jeśli asystent nie sięga po skill, nazwij go wprost, np. *„Użyj skilla
polish-weather-hydrology…”*. Asystent uruchamia skrypty sam — przy
pierwszym użyciu narzędzie może poprosić o zgodę na uruchomienie
polecenia `python3 …`.

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

## Klucze API (opcjonalne)

Większość źródeł działa bez rejestracji. Wyjątki:

- **PBN** (`polish-science-bibliography`) — wymaga `PBN_APP_ID` +
  `PBN_APP_TOKEN` (opcjonalnie `PBN_USER_TOKEN`). Rejestracja:
  [Open API PBN](https://pbn.nauka.gov.pl/centrum-pomocy/open-api-w-wersji-produkcyjnej-pbn/).
  Bez kluczy pozostałe źródła tego skilla (POL-on/RAD-on, Ludzie Nauki)
  działają normalnie.
- **GUS BDL** (`polish-open-data-statistics`) — działa anonimowo, ale
  opcjonalny `BDL_CLIENT_ID` daje wyższe limity. Rejestracja:
  [Portal API GUS](https://api.stat.gov.pl/home/bdlapi).

Najprościej zapisać klucze w zwykłym pliku tekstowym o nazwie
**`polish-academic-skills.env`**:

```
PBN_APP_ID=twoj-app-id
PBN_APP_TOKEN=twoj-app-token
BDL_CLIENT_ID=twoj-client-id
```

Skrypty szukają go najpierw w folderze skilla (obok `SKILL.md`), a potem
w Twoim folderze domowym — np. `C:\Users\<nazwa>\polish-academic-skills.env`
albo `~/polish-academic-skills.env`. Możesz też poprosić asystenta, żeby
utworzył ten plik za Ciebie. Zmienne środowiskowe o tych samych nazwach
mają pierwszeństwo przed plikiem.

**claude.ai / Claude Desktop:** tam nie da się ustawić zmiennych
środowiskowych ani pliku w folderze domowym, więc plik musi być w ZIP-ie.
Pobierz repozytorium, zapisz plik w `skills/polish-science-bibliography/`,
uruchom `python3 install.py --zip --skill polish-science-bibliography`
i wgraj powstały ZIP. **Nie udostępniaj tego ZIP-a** — zawiera Twoje
klucze. Plik `polish-academic-skills.env` jest w `.gitignore`, więc nie
trafi przypadkiem do repozytorium.

---

## Rozwiązywanie problemów

| Objaw | Co zrobić |
| --- | --- |
| `python3: command not found`, `'python3' is not recognized…` albo „Python was not found” | Zainstaluj Pythona ([Krok 2](#szybki-start)). Na Windows polecenie nazywa się zwykle `python` albo `py` — skille o tym wiedzą i same go użyją. |
| Asystent nie widzi skilla | Zrestartuj narzędzie albo otwórz nową rozmowę. Sprawdź, czy folder skilla leży bezpośrednio w katalogu skilli (np. `~/.claude/skills/polish-weather-hydrology/SKILL.md`, a nie `…/skills/polish-academic-skills/skills/…`). Listę wczytanych skilli pokazuje np. `/skills` w Claude Code albo `/skills list` w Gemini CLI. |
| claude.ai odrzuca ZIP („description too long”, „invalid frontmatter”…) | Pobierz aktualne ZIP-y — starsze wersje miały za długie opisy i błędny nagłówek YAML w sześciu skillach. ZIP musi zawierać folder skilla, a w nim `SKILL.md` (tak buduje go `install.py --zip`). |
| Każde zapytanie kończy się błędem sieci, `403 Forbidden` albo `Tunnel connection failed` | Środowisko blokuje ruch wychodzący. W claude.ai / Claude Desktop włącz dostęp do sieci ([krok 3](#claude-desktop-i-claudeai)). Lokalnie sprawdź połączenie, VPN albo firewall; test: `python3 install.py --check`. |
| `CERTIFICATE_VERIFY_FAILED` (macOS) | Python z python.org nie ma jeszcze certyfikatów. Otwórz *Programy → Python 3.x* i kliknij dwukrotnie `Install Certificates.command`. |
| `UnicodeEncodeError` albo „krzaki” zamiast polskich liter (Windows) | Zaktualizuj skille — od tej wersji skrypty zawsze wypisują UTF-8. |
| „PBN API requires PBN_APP_ID and PBN_APP_TOKEN” | PBN wymaga kluczy — patrz [Klucze API](#klucze-api-opcjonalne). |
| Jedno ze źródeł zwraca błąd, a reszta działa | Część źródeł nie ma API i skrypty czytają ich strony HTML, więc zmiana wyglądu strony może je zepsuć — patrz [Ograniczenia](#ograniczenia). `search_all.py` raportuje status każdego źródła osobno. |

---

## Jak to działa

Skrypty to zwykłe programy wiersza poleceń, które agent uruchamia sam:

```bash
python3 scripts/imgw.py synop --station-name warszawa
python3 scripts/bdl.py search-subjects --name "ludność"
```

Zwracają JSON (UTF-8) na `stdout`. Błędy (HTTP, sieciowe, braki
poświadczeń) trafiają na `stderr` z kodem wyjścia różnym od zera. Każdy
request ma nagłówek
`User-Agent: polish-academic-skills/1.0 (+https://github.com/asterixix/polish-academic-skills)`,
timeout 30s i pojedynczy retry tylko dla przejściowych błędów sieciowych
(nigdy dla 4xx). Pełne parametry i przykłady — patrz `SKILL.md` każdego
skilla oraz, gdzie dotyczy, `reference/API.md`.

Nagłówki `SKILL.md` używają wyłącznie pól otwartego standardu
[Agent Skills](https://agentskills.io) (`name`, `description`, `license`,
`compatibility`), więc te same foldery działają w Claude Code, claude.ai,
Codex, Gemini CLI, Cursorze, Copilocie, OpenCode i innych narzędziach.

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

## Dla opiekunów repozytorium

- **Przed commitem** uruchom `python tools/check_skills.py` (najlepiej z
  zainstalowanym PyYAML, żeby nagłówki `SKILL.md` były parsowane tak ściśle
  jak w claude.ai, Codex i Gemini CLI). Skrypt sprawdza limity nagłówków,
  spójność `marketplace.json`, `--help` każdego skryptu, wypisywanie UTF-8
  przy stronie kodowej Windows oraz instalator i układ ZIP-ów. To samo
  robi CI (`.github/workflows/check.yml`) na Linuksie, Windows i macOS.
- `claude plugin validate .` sprawdza marketplace Claude Code.
- **Wydanie:** podbij wersje zmienionych pluginów w
  `.claude-plugin/marketplace.json` (Claude Code aktualizuje plugin tylko
  po zmianie wersji), a potem wypchnij tag, np.
  `git tag v1.2.0 && git push origin v1.2.0`. Workflow
  `.github/workflows/release.yml` dołączy do wydania po jednym ZIP-ie na
  skill — na nie wskazują linki w sekcji
  [Claude Desktop i claude.ai](#claude-desktop-i-claudeai).
- `install.py` musi pozostać czystym ASCII (PowerShell 5.1 psuje znaki
  spoza ASCII przy przekazywaniu skryptu do `python`) — pilnuje tego
  `check_skills.py`.

## Źródło i licencja

Logika API/parsowania jest portem z [`polish-academic-mcp`](https://github.com/asterixix/polish-academic-mcp)
(MIT, © Artur Sendyka). Ten projekt jest wydany na tej samej licencji — patrz
[`LICENSE`](LICENSE).
