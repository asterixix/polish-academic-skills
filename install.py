#!/usr/bin/env python3
"""One-step installer for polish-academic-skills (Python standard library only).

Copies the skills into the skills folder of every AI tool it finds on this
computer (Claude Code, OpenAI Codex, Gemini CLI, Cursor, GitHub Copilot,
OpenCode, Windsurf), or builds ZIP files to upload to claude.ai / Claude
Desktop. Running it again updates the skills in place.

From a downloaded copy of the repository:

    python3 install.py                 (macOS / Linux)
    python install.py                  (Windows, or double-click install-windows.bat)

Straight from GitHub, without downloading anything first:

    curl -fsSL https://raw.githubusercontent.com/asterixix/polish-academic-skills/main/install.py | python3 -
    python -c "import urllib.request as u;exec(u.urlopen('https://raw.githubusercontent.com/asterixix/polish-academic-skills/main/install.py').read())"

Run with --help for every option (pick tools, single skills, project folder,
ZIPs for claude.ai, uninstall).

Keep this file pure ASCII: Windows PowerShell 5.1 replaces non-ASCII
characters with "?" when a script is piped into python.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = "asterixix/polish-academic-skills"
USER_AGENT = "polish-academic-skills-installer (+https://github.com/%s)" % REPO
SETTINGS_FILENAME = "polish-academic-skills.env"
SKIPPED_NAMES = {"__pycache__", ".DS_Store"}
CHECK_URL = "https://danepubliczne.imgw.pl/api/data/synop/station/warszawa"
ZIP_MAX_FILES = 200  # claude.ai rejects skill ZIPs with more files than this

# name -> (label, folders whose presence means the tool is installed,
#          user-level skills folder, project-level skills folder)
AGENTS = {
    "claude-code": ("Claude Code", ("~/.claude",), "~/.claude/skills", ".claude/skills"),
    "codex": ("OpenAI Codex", ("~/.codex",), "~/.agents/skills", ".agents/skills"),
    "gemini-cli": ("Gemini CLI", ("~/.gemini",), "~/.gemini/skills", ".gemini/skills"),
    "cursor": ("Cursor", ("~/.cursor",), "~/.cursor/skills", ".cursor/skills"),
    "github-copilot": ("GitHub Copilot", ("~/.copilot",), "~/.copilot/skills", ".github/skills"),
    "opencode": ("OpenCode", ("~/.config/opencode",), "~/.config/opencode/skills", ".opencode/skills"),
    "windsurf": ("Windsurf", ("~/.codeium/windsurf",), "~/.codeium/windsurf/skills", ".windsurf/skills"),
    "universal": ("Other Agent Skills tools", (), "~/.agents/skills", ".agents/skills"),
}

EXAMPLE_PROMPT = "Jaka jest teraz pogoda w Krakowie wed\u0142ug IMGW?"


class InstallError(Exception):
    pass


def use_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def expand(path: str) -> Path:
    return Path(os.path.expanduser(path))


# --------------------------------------------------------------------------
# Finding the skills to install
# --------------------------------------------------------------------------


def skill_dirs(skills_root: Path) -> list[Path]:
    return sorted(p.parent for p in skills_root.glob("*/SKILL.md"))


def local_skills_root() -> Path | None:
    """The skills/ folder next to this file, when run from a repository copy."""
    here = globals().get("__file__")
    if not here or here.startswith("<"):  # piped into python ("<stdin>"), or exec()'d from python -c
        return None
    base = Path(here).resolve().parent
    manifest = base / ".claude-plugin" / "marketplace.json"
    try:
        is_ours = json.loads(manifest.read_text(encoding="utf-8")).get("name") == "polish-academic-skills"
    except (OSError, ValueError):
        is_ours = False
    if is_ours and skill_dirs(base / "skills"):
        return base / "skills"
    return None


def download_skills_root(ref: str, workdir: Path) -> Path:
    url = "https://github.com/%s/archive/%s.zip" % (REPO, ref)
    print("Downloading %s ..." % url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except urllib.error.URLError as exc:
        raise InstallError("could not download the skills from GitHub: %s%s" % (exc, certificate_hint(exc)))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(workdir)
    for top in workdir.iterdir():
        if skill_dirs(top / "skills"):
            return top / "skills"
    raise InstallError("the downloaded archive contains no skills/ folder")


# --------------------------------------------------------------------------
# Copying / removing
# --------------------------------------------------------------------------


def _make_writable_and_retry(func, path, _exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_make_writable_and_retry)
    else:
        shutil.rmtree(path, onerror=_make_writable_and_retry)


def is_this_skill(folder: Path, name: str) -> bool:
    """True if folder holds a copy of the skill called name (so it is safe to
    replace or delete), judged by the name: line of its SKILL.md."""
    try:
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return False
    return ("\nname: %s\n" % name) in text.replace("\r\n", "\n")


def install_skill(src: Path, target_root: Path, dry_run: bool) -> str:
    dest = target_root / src.name
    existed = dest.exists() or dest.is_symlink()
    dangling_link = dest.is_symlink() and not dest.exists()  # e.g. left behind by another installer
    if existed and not dangling_link and not is_this_skill(dest, src.name):
        raise InstallError("%s already exists and is not this skill -- left untouched" % dest)
    if dry_run:
        return "would update" if existed else "would install"
    settings = dest / SETTINGS_FILENAME
    kept_settings = settings.read_bytes() if settings.is_file() else None
    target_root.mkdir(parents=True, exist_ok=True)
    if existed:
        remove_path(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    if kept_settings is not None:
        (dest / SETTINGS_FILENAME).write_bytes(kept_settings)
    return "updated" if existed else "installed"


def uninstall_skill(name: str, target_root: Path, dry_run: bool) -> str:
    dest = target_root / name
    if not (dest.exists() or dest.is_symlink()):
        return "not installed"
    if not is_this_skill(dest, name):
        return "skipped (not this skill)"
    if dry_run:
        return "would remove"
    remove_path(dest)
    return "removed"


def build_zip(src: Path, out_dir: Path) -> tuple[Path, list[str]]:
    """ZIP a skill the way claude.ai expects: the skill folder at the root."""
    files = [
        f for f in sorted(src.rglob("*"))
        if f.is_file() and not SKIPPED_NAMES.intersection(f.relative_to(src).parts) and f.suffix != ".pyc"
    ]
    if len(files) > ZIP_MAX_FILES:
        raise InstallError("%s has %d files; claude.ai accepts at most %d" % (src.name, len(files), ZIP_MAX_FILES))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ("%s.zip" % src.name)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for f in files:
            archive.write(f, (Path(src.name) / f.relative_to(src)).as_posix())
    return out, [f.name for f in files if f.name == SETTINGS_FILENAME]


# --------------------------------------------------------------------------
# Connection test
# --------------------------------------------------------------------------


def certificate_hint(exc: BaseException) -> str:
    if "CERTIFICATE_VERIFY_FAILED" in str(exc) and sys.platform == "darwin":
        return ("\n  Fix: open the Applications > Python 3.x folder and double-click "
                "'Install Certificates.command', then try again.")
    return ""


def connection_test() -> bool:
    request = urllib.request.Request(CHECK_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print("Connection test: FAILED -- Python could not reach danepubliczne.imgw.pl (%s).%s"
              % (exc, certificate_hint(exc)))
        print("  The skills need internet access to Polish public data servers. Check your")
        print("  internet connection, VPN or firewall, then run this installer with --check.")
        return False
    print("Connection test: OK -- Python can reach Polish public data servers.")
    return True


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Install polish-academic-skills into your AI tools. With no options, "
                    "installs every skill for every supported tool found on this computer.",
        epilog="Supported tools for --agent: %s, or 'all'." % ", ".join(AGENTS),
    )
    parser.add_argument("--agent", action="append", metavar="NAME",
                        help="install only for this tool (repeatable).")
    parser.add_argument("--skill", action="append", metavar="NAME",
                        help="install only this skill, e.g. polish-weather-hydrology (repeatable).")
    parser.add_argument("--project", action="store_true",
                        help="install into the current folder's project skills folders "
                             "(e.g. .claude/skills) instead of your user folders.")
    parser.add_argument("--target", metavar="DIR",
                        help="install into this skills folder (for any other Agent Skills tool).")
    parser.add_argument("--zip", nargs="?", const="", metavar="DIR",
                        help="build upload-ready ZIP files for claude.ai / Claude Desktop "
                             "(default folder: Downloads/polish-academic-skills-zips).")
    parser.add_argument("--uninstall", action="store_true", help="remove the skills instead.")
    parser.add_argument("--list", action="store_true", help="show skills and detected tools, change nothing.")
    parser.add_argument("--check", action="store_true", help="only run the internet connection test.")
    parser.add_argument("--no-check", action="store_true", help="skip the connection test after installing.")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing.")
    parser.add_argument("--ref", default="main",
                        help="branch or tag to download when not run from a repository copy (default: main).")
    return parser.parse_args(argv)


def detected_agents() -> list[str]:
    return [name for name, (_, markers, _, _) in AGENTS.items()
            if any(expand(m).is_dir() for m in markers)]


def resolve_targets(args: argparse.Namespace) -> list[tuple[str, Path]]:
    """(label, skills folder) pairs, merged when several tools share a folder."""
    if args.target:
        return [("Custom folder", expand(args.target))]
    if args.agent:
        names = list(AGENTS) if "all" in args.agent else args.agent
        unknown = [n for n in names if n not in AGENTS]
        if unknown:
            raise InstallError("unknown tool %s; choose from: %s, all" % (", ".join(unknown), ", ".join(AGENTS)))
    else:
        names = detected_agents()
    merged: dict[Path, list[str]] = {}
    for name in names:
        label, _, user_dir, project_dir = AGENTS[name]
        folder = Path.cwd() / project_dir if args.project else expand(user_dir)
        merged.setdefault(folder, []).append(label)
    return [(" + ".join(labels), folder) for folder, labels in merged.items()]


def default_zip_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return (downloads if downloads.is_dir() else Path.cwd()) / "polish-academic-skills-zips"


def run(args: argparse.Namespace, skills_root: Path) -> int:
    skills = skill_dirs(skills_root)
    if args.skill:
        by_name = {s.name: s for s in skills}
        unknown = [n for n in args.skill if n not in by_name]
        if unknown:
            raise InstallError("unknown skill %s; choose from: %s" % (", ".join(unknown), ", ".join(by_name)))
        skills = [by_name[n] for n in args.skill]

    if args.list:
        print("Skills:")
        for s in skills:
            print("  " + s.name)
        found = detected_agents()
        print("Tools found on this computer: %s" % (", ".join(AGENTS[n][0] for n in found) or "none"))
        return 0

    if args.zip is not None:
        out_dir = expand(args.zip) if args.zip else default_zip_dir()
        for s in skills:
            path, secrets = build_zip(s, out_dir)
            print("  %s" % path)
            if secrets:
                print("    includes %s with your API keys -- do not share this ZIP" % SETTINGS_FILENAME)
        print("\nUpload each ZIP in claude.ai or Claude Desktop: Customize > Skills > Add.")
        print("Then allow network access for the skills (see README, 'Claude Desktop / claude.ai').")
        return 0

    targets = resolve_targets(args)
    if not targets:
        print("No supported AI tool was found on this computer (looked for: %s)."
              % ", ".join(AGENTS[n][0] for n in AGENTS if AGENTS[n][1]))
        print("  - Start your tool once so it creates its settings folder, then run this again, or")
        print("  - pick the tool yourself, e.g.:   install.py --agent codex")
        print("  - for claude.ai / Claude Desktop: install.py --zip   (then upload the ZIP files)")
        return 1

    verb = "Removing" if args.uninstall else "Installing"
    print("%s %d skill(s)%s:" % (verb, len(skills), " (dry run)" if args.dry_run else ""))
    failures = 0
    for label, folder in targets:
        outcomes: dict[str, int] = {}
        for s in skills:
            try:
                if args.uninstall:
                    outcome = uninstall_skill(s.name, folder, args.dry_run)
                else:
                    outcome = install_skill(s, folder, args.dry_run)
            except (InstallError, OSError) as exc:
                failures += 1
                outcome = "failed"
                print("    ! %s: %s" % (s.name, exc))
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        summary = ", ".join("%d %s" % (count, outcome) for outcome, count in outcomes.items())
        print("  %-30s -> %s  (%s)" % (label, folder, summary))

    if args.uninstall or args.dry_run:
        return 1 if failures else 0
    if not args.no_check:
        print()
        connection_test()
    print("\nDone. Restart your AI tool (or start a new chat/session), then ask for example:")
    print('  "%s"' % EXAMPLE_PROMPT)
    print("Using claude.ai or Claude Desktop chat? Those need ZIP uploads instead: install.py --zip")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    use_utf8_stdio()
    if sys.version_info < (3, 9):
        print("These skills need Python 3.9 or newer; this is Python %d.%d. "
              "Get a current version from https://www.python.org/downloads/" % sys.version_info[:2])
        return 1
    args = parse_args(argv)
    try:
        if args.check:
            return 0 if connection_test() else 1
        local = local_skills_root()
        if local is not None:
            return run(args, local)
        with tempfile.TemporaryDirectory(prefix="polish-academic-skills-") as tmp:
            return run(args, download_skills_root(args.ref, Path(tmp)))
    except InstallError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
