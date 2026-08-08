"""
Shared subprocess fan-out helper for this skill's search_all.py.

Standard-library only. Embedded in THIS skill only -- do not import from
sibling skill directories.

Runs several of this skill's own scripts as subprocesses in parallel and
collects their JSON stdout into one combined result. A single slow, broken,
or rate-limited source can never block or fail the others -- every job's
outcome (success or error) is captured per-source.
"""

from __future__ import annotations

import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SUBPROCESS_TIMEOUT = 45  # seconds; comfortably above _http.py's 30s x 2-attempt budget


def _run_one(name: str, args: list[str]) -> dict[str, Any]:
    script = SCRIPT_DIR / f"{name}.py"
    cmd = [sys.executable, str(script), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"source": name, "ok": False, "error": f"timed out after {SUBPROCESS_TIMEOUT}s"}
    if proc.returncode != 0:
        return {"source": name, "ok": False, "error": (proc.stderr or "").strip() or f"exit code {proc.returncode}"}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"source": name, "ok": False, "error": "non-JSON stdout", "raw_stdout": proc.stdout[:1000]}
    return {"source": name, "ok": True, "data": data}


def run_sources(jobs: dict[str, list[str]], max_workers: int = 8) -> dict[str, Any]:
    """jobs: {source_name: [argv...]} -- one entry per script (without the
    .py suffix) in this skill's scripts/ directory, argv being the
    subcommand + flags to run it with. Returns {source_name: {"ok": bool,
    "data"|"error": ...}}, in no particular order (parallel execution)."""
    results: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_one, name, args): name for name, args in jobs.items()}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            source = r.pop("source")
            results[source] = r
    return results
