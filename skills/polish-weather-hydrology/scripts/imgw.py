#!/usr/bin/env python3
"""IMGW-PIB — Institute of Meteorology and Water Management (danepubliczne.imgw.pl).

Public REST API providing current synoptic, hydrological, and meteorological
station readings, plus active weather/flood warnings. No authentication
required.

API base: https://danepubliczne.imgw.pl/api/data

Subcommands (ported 1:1 from the polish-academic-mcp `imgw.ts` tools):
  synop     -- Current synoptic (weather) station readings. Optional
               --station-id or --station-name filter (station_id wins if
               both are given). With neither, returns all stations.
  hydro     -- Current hydrological (river gauge) station readings.
  meteo     -- Current meteorological station readings.
  warnings  -- Active meteorological and/or hydrological warnings.
               --type meteo|hydro|all (default: all).

Usage:
  python3 imgw.py synop
  python3 imgw.py synop --station-id 12500
  python3 imgw.py synop --station-name jeleniagora
  python3 imgw.py hydro
  python3 imgw.py meteo
  python3 imgw.py warnings
  python3 imgw.py warnings --type meteo
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from typing import Any

try:
    from _http import fetch_json
except ImportError:  # pragma: no cover - allows running from another cwd
    import os

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _http import fetch_json

API_BASE = "https://danepubliczne.imgw.pl/api/data"


def cmd_synop(args: argparse.Namespace) -> Any:
    if args.station_id:
        path = f"/synop/id/{urllib.parse.quote(args.station_id, safe='')}"
    elif args.station_name:
        path = f"/synop/station/{urllib.parse.quote(args.station_name, safe='')}"
    else:
        path = "/synop"
    return fetch_json(f"{API_BASE}{path}")


def cmd_hydro(_args: argparse.Namespace) -> Any:
    return fetch_json(f"{API_BASE}/hydro/")


def cmd_meteo(_args: argparse.Namespace) -> Any:
    return fetch_json(f"{API_BASE}/meteo/")


def cmd_warnings(args: argparse.Namespace) -> Any:
    warning_type = args.type

    if warning_type in ("meteo", "all"):
        meteo_data = fetch_json(f"{API_BASE}/warnings_meteo")
    else:
        meteo_data = None

    if warning_type in ("hydro", "all"):
        hydro_data = fetch_json(f"{API_BASE}/warnings_hydro")
    else:
        hydro_data = None

    if warning_type == "all":
        # Reproduce the TS tool's combined shape exactly: a JSON array with
        # one {"type":"meteo","warnings":[...]} object and one
        # {"type":"hydro","warnings":[...]} object.
        return [
            {"type": "meteo", "warnings": meteo_data},
            {"type": "hydro", "warnings": hydro_data},
        ]
    if warning_type == "meteo":
        return meteo_data
    return hydro_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imgw.py",
        description="IMGW-PIB weather/hydrology data (danepubliczne.imgw.pl).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_synop = sub.add_parser("synop", help="Current synoptic (weather) station readings.")
    p_synop.add_argument(
        "--station-id",
        dest="station_id",
        default=None,
        help="Numeric synoptic station ID, e.g. '12500'. Overrides --station-name if both given.",
    )
    p_synop.add_argument(
        "--station-name",
        dest="station_name",
        default=None,
        help="Station name without Polish diacritics, e.g. 'jeleniagora', 'warszawa', 'krakow'.",
    )
    p_synop.set_defaults(func=cmd_synop)

    p_hydro = sub.add_parser("hydro", help="Current hydrological (river gauge) station readings.")
    p_hydro.set_defaults(func=cmd_hydro)

    p_meteo = sub.add_parser("meteo", help="Current meteorological station readings.")
    p_meteo.set_defaults(func=cmd_meteo)

    p_warnings = sub.add_parser("warnings", help="Active meteorological and/or hydrological warnings.")
    p_warnings.add_argument(
        "--type",
        choices=["meteo", "hydro", "all"],
        default="all",
        help="Warning type: 'meteo' (weather), 'hydro' (hydrological), or 'all' for both (default).",
    )
    p_warnings.set_defaults(func=cmd_warnings)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = args.func(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
