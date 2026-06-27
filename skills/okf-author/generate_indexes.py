#!/usr/bin/env python3
"""generate_indexes.py - generate OKF `index.md` and `log.md` across a bundle.

Part of the okf-author skill (https://github.com/parkscloud/okf-author).

Reads the YAML frontmatter already present on a bundle's concept files and
(re)writes the reserved files in every directory:

  - `index.md` : a listing of that directory's concepts (grouped by `type`) and
                 its subdirectories, with relative links and one-line
                 descriptions drawn from each concept's frontmatter. The
                 bundle-root `index.md` carries `okf_version`; every sub-directory
                 `index.md` carries no frontmatter (per OKF v0.1 sections 6 & 11).
  - `log.md`   : a date-grouped history of the directory's dated concepts
                 (newest first, `## YYYY-MM-DD` headings). Written only for
                 directories that have at least one dated concept; skip entirely
                 with --no-logs.

This automates the structural half of OKF authoring/conversion (the half the
agent would otherwise hand-write). Pair it with `validate.py`.

Dependency-free: standard library only. PyYAML is used for frontmatter parsing
when it is already installed; otherwise a small built-in parser reads the
scalar fields this tool needs (type/title/description/timestamp).

It OVERWRITES existing `index.md`/`log.md` files - use --dry-run to preview.

Usage:
    python generate_indexes.py BUNDLE_DIR
    python generate_indexes.py BUNDLE_DIR --title "My Knowledge Base"
    python generate_indexes.py BUNDLE_DIR --okf-version 0.1
    python generate_indexes.py BUNDLE_DIR --no-logs
    python generate_indexes.py BUNDLE_DIR --dry-run

Exit codes: 0 = ok, 2 = usage/path error.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

GENERATOR_VERSION = "1.4.0"
DEFAULT_OKF_VERSION = "0.1"
RESERVED = {"index.md", "log.md"}

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except Exception:  # pragma: no cover - environment dependent
    _HAVE_YAML = False

_KEY_RE = re.compile(r"^([A-Za-z0-9_.\-]+):\s*(.*)$")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
    except OSError:
        return ""


def read_frontmatter(p: Path) -> dict:
    """Best-effort frontmatter dict. PyYAML when available, else a minimal
    top-level-scalar parser (enough for type/title/description/timestamp)."""
    text = _read(p)
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    block = "\n".join(lines[1:end])
    if _HAVE_YAML:
        try:
            data = yaml.safe_load(block) or {}
        except yaml.YAMLError:  # type: ignore[attr-defined]
            return {}
        return data if isinstance(data, dict) else {}
    out: dict = {}
    for line in block.split("\n"):
        if not line.strip() or line[0] in " \t#" or line.lstrip().startswith("- "):
            continue
        m = _KEY_RE.match(line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            out[key] = val
    return out


def _disp(name: str) -> str:
    return re.sub(r"[-_]+", " ", name).strip()


def _enc(target: str) -> str:
    """Percent-encode a link target so it resolves and renders (spaces, parens,
    etc.), keeping path separators."""
    return quote(target, safe="/")


def _date_of(fm: dict, name: str) -> str | None:
    s = str(fm.get("timestamp", ""))
    m = _DATE_RE.match(s)
    if m:
        return m.group(1)
    m = _DATE_RE.search(name)
    return m.group(1) if m else None


def _scalar(fm: dict, key: str, fallback: str = "") -> str:
    return str(fm.get(key) or fallback).replace("\n", " ").strip()


def generate(root: Path, *, title: str | None, okf_version: str,
             logs: bool, dry_run: bool) -> tuple[int, int]:
    """Generate index.md (+ log.md) across the bundle. Returns (n_index, n_log)."""
    concept_dirs: dict[Path, list[Path]] = defaultdict(list)
    for f in root.rglob("*.md"):
        if "/.git/" in str(f) or f.name in RESERVED:
            continue
        concept_dirs[f.parent].append(f)

    # Index every directory that has concepts somewhere in its subtree.
    index_dirs: set[Path] = set()
    for d in concept_dirs:
        cur = d
        while True:
            index_dirs.add(cur)
            if cur == root:
                break
            cur = cur.parent

    def subdir_desc(d: Path) -> str:
        return _scalar(read_frontmatter(d / "README.md"), "description")

    n_index = n_log = 0
    for d in sorted(index_dirs):
        is_root = (d == root)
        concepts = sorted(concept_dirs.get(d, []), key=lambda p: p.name.lower())
        child_dirs = sorted([c for c in d.iterdir() if c.is_dir() and c in index_dirs],
                            key=lambda p: p.name.lower())

        # ----- index.md -----
        heading = (title or _disp(root.name)) if is_root else _disp(d.name)
        out = [f"# {heading}", ""]
        by_type: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
        for c in concepts:
            fm = read_frontmatter(c)
            by_type[str(fm.get("type") or "Other")].append((c, fm))
        for typ in sorted(by_type):
            out += [f"## {typ}", ""]
            for c, fm in sorted(by_type[typ],
                                key=lambda it: (_date_of(it[1], it[0].name) or "0000-00-00",
                                                it[0].name.lower()),
                                reverse=True):
                ttl = _scalar(fm, "title", _disp(c.stem))
                desc = _scalar(fm, "description")
                out.append(f"* [{ttl}]({_enc(c.name)})" + (f" - {desc}" if desc else ""))
            out.append("")
        if child_dirs:
            out += ["## Subdirectories", ""]
            for c in child_dirs:
                sd = subdir_desc(c)
                out.append(f"* [{_disp(c.name)}]({_enc(c.name)}/index.md)" + (f" - {sd}" if sd else ""))
            out.append("")
        body = "\n".join(out).rstrip() + "\n"
        if is_root:
            body = f'---\nokf_version: "{okf_version}"\n---\n\n' + body
        target = d / "index.md"
        if dry_run:
            print(f"[dry-run] index.md  {target.relative_to(root)}")
        else:
            target.write_text(body, encoding="utf-8")
        n_index += 1

        # ----- log.md -----
        if logs and concepts:
            dated: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
            for c in concepts:
                fm = read_frontmatter(c)
                dt = _date_of(fm, c.name)
                if dt:
                    dated[dt].append((c, fm))
            if dated:
                lg = ["# Update Log", ""]
                for dt in sorted(dated, reverse=True):
                    lg.append(f"## {dt}")
                    for c, fm in sorted(dated[dt], key=lambda it: _scalar(it[1], "title", it[0].stem).lower()):
                        lg.append(f"* [{_scalar(fm, 'title', _disp(c.stem))}]({_enc(c.name)})")
                    lg.append("")
                logtarget = d / "log.md"
                if dry_run:
                    print(f"[dry-run] log.md    {logtarget.relative_to(root)}")
                else:
                    logtarget.write_text("\n".join(lg).rstrip() + "\n", encoding="utf-8")
                n_log += 1

    return n_index, n_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_indexes.py",
        description="Generate OKF index.md and log.md across a bundle from concept frontmatter.",
    )
    parser.add_argument("bundle", help="bundle root directory")
    parser.add_argument("--title", help="title for the root index.md (default: derived from the directory name)")
    parser.add_argument("--okf-version", default=DEFAULT_OKF_VERSION,
                        help=f"okf_version recorded in the root index.md (default: {DEFAULT_OKF_VERSION})")
    parser.add_argument("--no-logs", action="store_true", help="do not generate log.md files")
    parser.add_argument("--dry-run", action="store_true", help="print what would be written; change nothing")
    parser.add_argument("--version", action="version",
                        version=f"generate_indexes.py {GENERATOR_VERSION} "
                                f"(YAML parser: {'PyYAML' if _HAVE_YAML else 'built-in minimal'})")
    args = parser.parse_args(argv)

    root = Path(args.bundle)
    if not root.is_dir():
        print(f"error: not a directory: {args.bundle}", file=sys.stderr)
        return 2
    root = root.resolve()

    n_index, n_log = generate(root, title=args.title, okf_version=args.okf_version,
                              logs=not args.no_logs, dry_run=args.dry_run)
    verb = "would generate" if args.dry_run else "generated"
    print(f"{verb}: {n_index} index.md + {n_log} log.md  "
          f"(bundle '{root.name}', okf_version {args.okf_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
