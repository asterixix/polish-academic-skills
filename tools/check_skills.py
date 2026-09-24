#!/usr/bin/env python3
"""Offline sanity checks for every skill in this repository.

Run before committing, and in CI on Linux/macOS/Windows:

    python tools/check_skills.py

Checks (no network access needed):
  * SKILL.md frontmatter is strict YAML (with PyYAML installed) and follows
    the Agent Skills limits claude.ai enforces on upload: name matches the
    folder, description <= 1024 chars, compatibility <= 500 chars, and only
    the keys claude.ai accepts.
  * .claude-plugin/marketplace.json points at existing skills and gives every
    skill its own plugin.
  * Every script answers --help when started from an unrelated folder.
  * Every script switches stdout to UTF-8 even under a cp1252 code page (the
    Windows default that cannot encode Polish letters).
  * install.py is pure ASCII, installs into a folder, and builds ZIPs with
    the skill folder at the root.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

problems: list[str] = []


def problem(msg: str) -> None:
    problems.append(msg)
    print("  FAIL " + msg)


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("does not start with a --- frontmatter block")
    block = text.split("---\n", 2)[1]
    try:
        import yaml  # optional; CI installs it for a strict parse
    except ImportError:
        yaml = None
    if yaml is not None:
        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            raise ValueError("frontmatter is not a mapping")
        return data
    # Fallback for machines without PyYAML: single-line "key: value" pairs,
    # rejecting the plain-scalar characters that break strict YAML parsers.
    data = {}
    for line in block.splitlines():
        key, sep, value = line.partition(": ")
        if not sep:
            raise ValueError("unsupported frontmatter line: %r" % line[:60])
        if value[:1] not in "\"'" and (": " in value or " #" in value):
            raise ValueError("%s contains ': ' or ' #' -- invalid in unquoted YAML" % key)
        data[key] = value
    return data


def check_frontmatter() -> None:
    print("Frontmatter")
    for skill in SKILLS:
        try:
            fm = parse_frontmatter(skill / "SKILL.md")
        except Exception as exc:  # noqa: BLE001 -- report any parse failure
            problem("%s: invalid SKILL.md frontmatter: %s" % (skill.name, str(exc).splitlines()[0]))
            continue
        name, desc = fm.get("name", ""), fm.get("description", "")
        if name != skill.name or not NAME_RE.match(name) or len(name) > 64:
            problem("%s: name %r must equal the folder name (lowercase, hyphens, <= 64 chars)" % (skill.name, name))
        if not desc or len(desc) > 1024:
            problem("%s: description is %d chars (must be 1-1024)" % (skill.name, len(desc)))
        if "<" in desc or ">" in desc:
            problem("%s: description must not contain < or >" % skill.name)
        if len(fm.get("compatibility", "")) > 500:
            problem("%s: compatibility is longer than 500 chars" % skill.name)
        extra = set(fm) - ALLOWED_KEYS
        if extra:
            problem("%s: claude.ai rejects frontmatter keys %s" % (skill.name, sorted(extra)))
    print("  checked %d skills" % len(SKILLS))


def check_marketplace() -> None:
    print("Marketplace")
    data = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    covered = set()
    names = [p["name"] for p in data["plugins"]]
    if len(names) != len(set(names)):
        problem("marketplace.json has duplicate plugin names")
    for plugin in data["plugins"]:
        for rel in plugin.get("skills", []):
            path = (ROOT / plugin.get("source", "./") / rel).resolve()
            if not (path / "SKILL.md").is_file():
                problem("plugin %s lists %s, which has no SKILL.md" % (plugin["name"], rel))
            covered.add(path.name)
    for skill in SKILLS:
        if skill.name not in covered:
            problem("skill %s has no plugin entry in marketplace.json" % skill.name)
    print("  checked %d plugins" % len(data["plugins"]))


def entry_scripts() -> list[Path]:
    return [s for skill in SKILLS for s in sorted((skill / "scripts").glob("*.py")) if not s.name.startswith("_")]


def check_scripts() -> None:
    print("Scripts")
    probe = (
        "import runpy, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "runpy.run_path(sys.argv[2], run_name='probe')\n"
        "sys.stdout.write(sys.stdout.encoding)\n"
    )
    scripts = entry_scripts()
    with tempfile.TemporaryDirectory() as elsewhere:
        for script in scripts:
            rel = script.relative_to(ROOT)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            run = subprocess.run([sys.executable, str(script), "--help"], cwd=elsewhere, env=env,
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
            if run.returncode != 0:
                problem("%s --help exited %d: %s" % (rel, run.returncode, run.stderr.strip()[-200:]))
            env["PYTHONIOENCODING"] = "cp1252"
            run = subprocess.run([sys.executable, "-c", probe, str(script.parent), str(script)], cwd=elsewhere,
                                 env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if run.stdout.strip().lower() != "utf-8":
                problem("%s leaves stdout as %r under a cp1252 code page (Polish text would crash on Windows)"
                        % (rel, run.stdout.strip() or run.stderr.strip()[-200:]))
    aggregates = {p.read_bytes() for p in (ROOT / "skills").glob("*/scripts/_aggregate.py")}
    if len(aggregates) > 1:
        problem("the per-skill copies of _aggregate.py have drifted apart; keep them identical")
    print("  checked %d scripts" % len(scripts))


def check_installer() -> None:
    print("Installer")
    installer = ROOT / "install.py"
    if any(b > 127 for b in installer.read_bytes()):
        problem("install.py must be pure ASCII (PowerShell 5.1 mangles non-ASCII when piping it to python)")
    with tempfile.TemporaryDirectory() as tmp:
        target, zips = Path(tmp) / "skills", Path(tmp) / "zips"
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for args in (["--target", str(target), "--no-check"], ["--zip", str(zips)]):
            run = subprocess.run([sys.executable, str(installer), *args], env=env,
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
            if run.returncode != 0:
                problem("install.py %s exited %d: %s" % (args[0], run.returncode, (run.stderr or run.stdout)[-300:]))
        for skill in SKILLS:
            if not (target / skill.name / "SKILL.md").is_file():
                problem("install.py --target did not install %s" % skill.name)
            archive = zips / ("%s.zip" % skill.name)
            if not archive.is_file():
                problem("install.py --zip did not build %s" % archive.name)
                continue
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
            if {n.split("/")[0] for n in names} != {skill.name} or "%s/SKILL.md" % skill.name not in names:
                problem("%s must contain the skill folder at its root" % archive.name)
            if len(names) > 200 or any("__pycache__" in n for n in names):
                problem("%s has too many files or bytecode caches" % archive.name)
    print("  installed and zipped %d skills" % len(SKILLS))


def main() -> int:
    for check in (check_frontmatter, check_marketplace, check_scripts, check_installer):
        check()
    if problems:
        print("\n%d problem(s) found." % len(problems))
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
