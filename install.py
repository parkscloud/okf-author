#!/usr/bin/env python3
"""install.py - install the okf-author skill into Claude Code and/or Codex.

Copies the self-contained skill folder (`skill/okf-author/`) into the per-user
skills directory of each target agent:

    Claude Code : ~/.claude/skills/okf-author/
    Codex       : ~/.agents/skills/okf-author/

Stdlib-only; works on Windows, macOS, and Linux. From a clone of the repo:

    python3 install.py --all                # install for both agents
    python3 install.py --claude             # Claude Code only
    python3 install.py --codex              # Codex only
    python3 install.py --all --dry-run      # show what would happen, change nothing
    python3 install.py --claude --claude-dir /custom/skills  # override the target root
    python3 install.py --codex  --codex-dir  /custom/skills

(On Windows use `python` or `py` instead of `python3`.)

Notes:
- `--claude-dir` / `--codex-dir` point at the skills ROOT (the directory that
  holds per-skill folders); an `okf-author/` folder is created beneath it.
- Re-installing replaces any existing `okf-author/` skill folder with a clean copy.
- Codex's skills directory is `~/.agents/skills/` per OpenAI's official Codex
  skills documentation. Some third-party guides instead cite `~/.codex/skills/`;
  if your Codex build looks there, point `--codex-dir` at it.
- After installing, restart the agent (or open a new session) so it discovers the skill.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_NAME = "okf-author"
SOURCE = Path(__file__).resolve().parent / "skill" / SKILL_NAME

CLAUDE_DEFAULT = Path.home() / ".claude" / "skills"
CODEX_DEFAULT = Path.home() / ".agents" / "skills"

# Never copy Python bytecode caches into an installed skill.
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def _check_source() -> None:
    """Fail fast if we are not sitting next to a real, complete skill folder."""
    if not (SOURCE / "SKILL.md").is_file():
        sys.exit(
            f"error: no skill found at {SOURCE} (SKILL.md is missing).\n"
            f"Run install.py from a clone of the okf-author repository."
        )


def _install_one(agent: str, skills_root: Path, dry_run: bool) -> None:
    dest = skills_root / SKILL_NAME
    verb = "Would install" if dry_run else "Installing"
    print(f"{verb} {agent}:\n  {SOURCE}\n  -> {dest}")
    if dry_run:
        return
    skills_root.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  replacing existing {dest}")
        shutil.rmtree(dest)
    shutil.copytree(SOURCE, dest, ignore=_IGNORE)
    print(f"  installed {dest}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Install the okf-author skill into Claude Code and/or Codex.",
    )
    parser.add_argument("--all", action="store_true", help="install for both agents")
    parser.add_argument("--claude", action="store_true", help="install for Claude Code")
    parser.add_argument("--codex", action="store_true", help="install for Codex")
    parser.add_argument("--claude-dir", type=Path, default=CLAUDE_DEFAULT,
                        help=f"Claude Code skills root (default: {CLAUDE_DEFAULT})")
    parser.add_argument("--codex-dir", type=Path, default=CODEX_DEFAULT,
                        help=f"Codex skills root (default: {CODEX_DEFAULT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the planned actions without changing anything")
    args = parser.parse_args(argv)

    do_claude = args.all or args.claude
    do_codex = args.all or args.codex
    if not (do_claude or do_codex):
        parser.error("choose at least one target: --all, --claude, and/or --codex")

    _check_source()
    if do_claude:
        _install_one("Claude Code", args.claude_dir, args.dry_run)
    if do_codex:
        _install_one("Codex", args.codex_dir, args.dry_run)

    if not args.dry_run:
        print("\nDone. Restart your agent (or open a new session) so it picks up the skill.")
        verify_path = (args.claude_dir if do_claude else args.codex_dir) / SKILL_NAME / "validate.py"
        print(f"Verify with: {sys.executable} {verify_path} --version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
