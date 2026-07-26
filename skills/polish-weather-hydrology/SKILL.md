---
name: polish-weather-hydrology
description: Fetches real-time Polish weather, hydrology, and warnings data from IMGW-PIB (danepubliczne.imgw.pl) with no API key required. Use for current synoptic/weather station readings, river gauge (hydrological) station data, meteorological station readings, and active meteorological or flood warnings in Poland. Keywords -- IMGW, weather stations Poland, hydrological data, flood warnings, pogoda w Polsce, stacje meteorologiczne, ostrzeżenia meteorologiczne, wodowskazy, poziom wody, stacje synoptyczne, dane hydrologiczne.
---

# Polish Weather & Hydrology (IMGW-PIB)

## Overview

This skill provides direct access to IMGW-PIB (Institute of Meteorology and
Water Management — National Research Institute) public real-time data feeds.
It is a small, single-source skill covering four data types:

- Current synoptic (weather) station readings
- Current hydrological (river gauge) station readings
- Current meteorological station readings
- Active meteorological and/or hydrological (flood) warnings

No API key or authentication is required. Data is refreshed roughly every
hour by IMGW-PIB. Source: https://danepubliczne.imgw.pl

All scripts are standard-library-only Python 3 (`urllib`, `json`, `argparse`)
— no dependencies to install.

## Scripts

| Script            | Subcommand           | Description                                                              |
|--------------------|-----------------------|----------------------------------------------------------------------------|
| `scripts/imgw.py`  | `synop`               | Synoptic (weather) station readings: temperature, wind, humidity, pressure, precipitation. Optional `--station-id` or `--station-name`; without either, returns all stations. |
| `scripts/imgw.py`  | `hydro`               | Hydrological (river gauge) station readings: water level, flow rate, ice phenomena, alarm status. |
| `scripts/imgw.py`  | `meteo`               | Meteorological station readings: temperature, precipitation, snow cover, wind. |
| `scripts/imgw.py`  | `warnings`            | Active warnings. `--type meteo\|hydro\|all` (default `all`).             |

`scripts/_http.py` is a shared internal helper (30s timeout, one retry on
transient network errors only, never on HTTP 4xx/5xx) — not invoked directly.

## Usage

Get all current synoptic stations:

```bash
python3 scripts/imgw.py synop
```

Get the current reading for a named station (Polish diacritics stripped from
the name, e.g. "Jelenia Góra" -> "jeleniagora"):

```bash
python3 scripts/imgw.py synop --station-name jeleniagora
```

Get the current reading by numeric station ID (takes precedence over
`--station-name` if both are given):

```bash
python3 scripts/imgw.py synop --station-id 12500
```

Get all hydrological (river gauge) stations:

```bash
python3 scripts/imgw.py hydro
```

Get all meteorological stations:

```bash
python3 scripts/imgw.py meteo
```

List all active warnings (both meteorological and hydrological, combined):

```bash
python3 scripts/imgw.py warnings
```

List only active flood/hydrological warnings:

```bash
python3 scripts/imgw.py warnings --type hydro
```

Each command prints pretty-printed JSON (`json.dumps(..., ensure_ascii=False,
indent=2)`) to stdout. On failure, a clear error is printed to stderr and the
process exits with status 1.

## Notes

- Data refreshes roughly hourly at the source; there is no benefit to
  polling more often than that.
- No API key or registration is required.
- `warnings --type all` returns a JSON array of two objects —
  `{"type": "meteo", "warnings": [...]}` and `{"type": "hydro", "warnings": [...]}`
  — matching the combined shape of the original `imgw_warnings` MCP tool.
- Source: https://danepubliczne.imgw.pl (IMGW-PIB public data API).

## Attribution

Ported from the `imgw_synop`, `imgw_hydro`, `imgw_meteo`, and `imgw_warnings`
tools in [polish-academic-mcp](https://github.com/asterixix/polish-academic-mcp)
by asterixix.
