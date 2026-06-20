#!/usr/bin/env python3
"""validate.py - Open Knowledge Format (OKF) v0.1 conformance checker.

Part of the `okf-author` skill (https://github.com/parkscloud/okf-author).

Dependency-free: this runs on the Python 3 standard library alone. If PyYAML
happens to be installed it is used for fully-accurate frontmatter parsing
(matching the OKF reference implementation); otherwise a small built-in parser
handles the conformance-relevant checks. Either way, no `pip install` is needed.

WHAT "CONFORMANT" MEANS
-----------------------
Conformance is defined by OKF v0.1, section 9 ("Conformance"). A bundle is
conformant if:

  1. Every non-reserved `.md` file contains a parseable YAML frontmatter block.
  2. Every frontmatter block contains a non-empty `type` field.
  3. Every reserved file (`index.md`, `log.md`) follows the structure in
     sections 6 and 7 respectively, when present.

Everything else the spec describes is "soft guidance". Section 9 is explicit
that a consumer MUST NOT reject a bundle for: missing optional fields, unknown
`type` values, unknown extra keys, broken cross-links, or missing `index.md`
files. This checker therefore reports those as *warnings*, never errors, and
they never affect the exit code.

The OKF reference enrichment agent additionally treats `title`, `description`
and `timestamp` as required. That is stricter than the spec. Pass `--strict`
to opt into that behavior (those three become errors instead of warnings).

The authoritative spec is vendored next to this file at `reference/SPEC.md`
(OKF v0.1, Apache-2.0, (c) Google LLC).

USAGE
-----
    python validate.py PATH [PATH ...]   # validate one or more bundle dirs
    python validate.py --strict PATH     # also require title/description/timestamp
    python validate.py --json PATH       # machine-readable output
    python validate.py --quiet PATH      # errors + summary only (hide warnings)

EXIT CODES
----------
    0  all bundles conformant (no errors)
    1  one or more conformance errors found
    2  usage / path error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

CHECKER_VERSION = "1.3.0"
OKF_VERSION = "0.1"
RESERVED_FILENAMES = {"index.md", "log.md"}
# Recommended by spec section 4.1; required by the reference agent. Soft here
# unless --strict is given.
RECOMMENDED_FIELDS = ("title", "description", "timestamp")

# Optional, more-accurate YAML parsing (matches the reference implementation).
try:
    import yaml  # type: ignore

    _HAVE_YAML = True
except Exception:  # pragma: no cover - environment dependent
    yaml = None  # type: ignore
    _HAVE_YAML = False

# ISO 8601 calendar date, e.g. 2026-05-28 (used for log.md date headings).
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# ISO 8601 datetime, accepting a trailing 'Z' or +/-HH:MM offset and optional
# fractional seconds, e.g. 2026-05-28T22:53:05+00:00 or ...T22:53:05Z.
_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$"
)
# Markdown inline link: [text](target)
_LINK_RE = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)")
# A YAML-ish "key: value" line at the top level of a frontmatter block.
_KEY_RE = re.compile(r"^([A-Za-z0-9_.\-]+):\s*(.*)$")


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #

class Finding:
    """One issue discovered in one file.

    level  -- "error" (breaks conformance) or "warning" (soft guidance)
    relpath-- path shown to the user, relative to the bundle root
    message-- human-readable description
    line   -- 1-based source line number, if known
    """

    __slots__ = ("level", "relpath", "message", "line")

    def __init__(self, level: str, relpath: str, message: str, line: int | None = None):
        self.level = level
        self.relpath = relpath
        self.message = message
        self.line = line

    def render(self) -> str:
        loc = self.relpath if self.line is None else f"{self.relpath}:{self.line}"
        tag = "ERROR  " if self.level == "error" else "warning"
        return f"  {tag}  {loc}\n           {self.message}"

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "path": self.relpath,
            "line": self.line,
            "message": self.message,
        }


# --------------------------------------------------------------------------- #
# Frontmatter handling
# --------------------------------------------------------------------------- #

class FrontmatterError(ValueError):
    """Raised when a frontmatter block is present but cannot be parsed."""


def extract_frontmatter_text(text: str) -> str | None:
    """Return the text *inside* the leading `---` ... `---` block.

    Returns None if the file does not open with a frontmatter delimiter.
    Raises FrontmatterError if a block opens but is never closed.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    raise FrontmatterError("unterminated YAML frontmatter block (no closing '---')")


def parse_frontmatter(fm_text: str) -> dict:
    """Parse a frontmatter block into a dict.

    Uses PyYAML when available (authoritative, matches the reference parser);
    otherwise falls back to a minimal flat-key parser sufficient for the
    section-9 checks. Raises FrontmatterError on clearly invalid content.
    """
    if _HAVE_YAML:
        try:
            data = yaml.safe_load(fm_text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise FrontmatterError(f"invalid YAML: {exc}") from exc
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise FrontmatterError("frontmatter must be a YAML mapping")
        return data
    return _minimal_parse(fm_text)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _minimal_parse(fm_text: str) -> dict:
    """Stdlib-only fallback parser.

    Handles flat `key: value` pairs, quoted scalars, inline `[a, b]` lists, and
    block `- item` lists / indented continuation lines. This is intentionally
    NOT a full YAML engine -- it exists only to answer the section-9 questions
    (is there a parseable block? is `type` present and non-empty?) when PyYAML
    is unavailable. Indented continuations are tolerated rather than rejected.
    """
    data: dict = {}
    current_key: str | None = None
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # Block list item -> append to the current key's value.
        if raw.lstrip().startswith("- "):
            if current_key is not None:
                if not isinstance(data.get(current_key), list):
                    data[current_key] = []
                data[current_key].append(_unquote(raw.lstrip()[2:].strip()))
            continue
        # Any other indented line -> continuation of the previous value; ignore.
        if raw[0] in " \t":
            continue
        match = _KEY_RE.match(raw)
        if not match:
            raise FrontmatterError(f"cannot parse frontmatter line: {raw!r}")
        key, value = match.group(1), match.group(2).strip()
        current_key = key
        if value == "":
            data[key] = ""  # may become a block list via following '- ' lines
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_unquote(x.strip()) for x in inner.split(",")] if inner else []
        else:
            data[key] = _unquote(value)
    return data


def _is_empty(value) -> bool:
    """True if a frontmatter value counts as 'missing/empty'."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


# --------------------------------------------------------------------------- #
# Per-file validators
# --------------------------------------------------------------------------- #

def _validate_concept(rel: str, text: str, strict: bool) -> list[Finding]:
    """A non-reserved `.md` file: requires parseable frontmatter + non-empty type."""
    findings: list[Finding] = []
    try:
        fm_text = extract_frontmatter_text(text)
    except FrontmatterError as exc:
        return [Finding("error", rel, str(exc), line=1)]
    if fm_text is None:
        return [Finding("error", rel,
                        "missing YAML frontmatter block (file must start with '---')",
                        line=1)]
    try:
        fm = parse_frontmatter(fm_text)
    except FrontmatterError as exc:
        return [Finding("error", rel, str(exc), line=1)]

    # Requirement 2: a non-empty `type`.
    if _is_empty(fm.get("type")):
        findings.append(Finding("error", rel,
                                "frontmatter is missing a non-empty 'type' field (spec section 9)",
                                line=1))

    # Recommended fields: warnings by default, errors under --strict.
    for key in RECOMMENDED_FIELDS:
        if _is_empty(fm.get(key)):
            level = "error" if strict else "warning"
            note = " (required with --strict)" if strict else " (recommended, spec section 4.1)"
            findings.append(Finding(level, rel, f"missing '{key}'{note}", line=1))

    # Timestamp format (soft): only check string values; PyYAML may give a date.
    ts = fm.get("timestamp")
    if isinstance(ts, str) and ts.strip() and not _ISO_DATETIME_RE.match(ts.strip()):
        findings.append(Finding("warning", rel, f"'timestamp' is not ISO 8601: {ts!r}", line=1))

    return findings


def _validate_index(rel: str, text: str, is_root_index: bool) -> list[Finding]:
    """`index.md`: no frontmatter except the bundle-root index (okf_version only)."""
    findings: list[Finding] = []
    try:
        fm_text = extract_frontmatter_text(text)
    except FrontmatterError as exc:
        return [Finding("error", rel, f"index.md: {exc}", line=1)]

    if fm_text is not None:
        if not is_root_index:
            findings.append(Finding(
                "error", rel,
                "index.md must not contain frontmatter; only the bundle-root "
                "index.md may, and only for 'okf_version' (spec sections 6 & 11)",
                line=1))
        else:
            try:
                fm = parse_frontmatter(fm_text)
            except FrontmatterError as exc:
                return [Finding("error", rel, f"root index.md: {exc}", line=1)]
            extra = [k for k in fm if k != "okf_version"]
            if extra:
                findings.append(Finding(
                    "warning", rel,
                    "root index.md frontmatter should contain only 'okf_version'; "
                    f"also found: {', '.join(map(str, extra))}", line=1))
            ver = fm.get("okf_version")
            if ver is not None and str(ver) != OKF_VERSION:
                findings.append(Finding(
                    "warning", rel,
                    f"declared okf_version {ver!r} differs from this checker's "
                    f"target {OKF_VERSION!r}", line=1))

    # Soft sanity check: an index should list things (links). Empty/linkless is
    # not a conformance error, just suspicious.
    body = text
    if fm_text is not None:
        body = text.split("---", 2)[-1]
    if not _LINK_RE.search(body):
        findings.append(Finding("warning", rel,
                                "index.md contains no markdown links (expected a directory listing, spec section 6)"))
    return findings


def _validate_log(rel: str, text: str) -> list[Finding]:
    """`log.md`: every `##` heading must be an ISO 8601 date (spec section 7)."""
    findings: list[Finding] = []
    if text.lstrip().startswith("---"):
        findings.append(Finding("warning", rel, "log.md normally has no frontmatter (spec section 7)"))
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^##\s+(.*\S)\s*$", line)
        if match:
            heading = match.group(1).strip()
            if not _ISO_DATE_RE.match(heading):
                findings.append(Finding(
                    "error", rel,
                    f"log.md date heading must be ISO 8601 'YYYY-MM-DD' (spec section 7); got {heading!r}",
                    line=lineno))
    return findings


def _check_links(rel: str, path: Path, root: Path, text: str) -> list[Finding]:
    """Warn (never error) on broken intra-bundle links. Spec section 5.3 says
    consumers MUST tolerate broken links, so these are advisory only."""
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _LINK_RE.finditer(line):
            target = match.group(1).strip()
            target = target.split("#", 1)[0].split("?", 1)[0]
            target = unquote(target)  # decode %20 etc. so percent-encoded links resolve
            if not target:
                continue
            low = target.lower()
            if low.startswith(("http://", "https://", "mailto:", "tel:", "data:", "//")):
                continue
            if target.startswith("/"):
                resolved = root / target.lstrip("/")
            elif target.startswith(("./", "../")) or target.endswith((".md", "/")):
                resolved = path.parent / target
            else:
                continue  # not obviously an intra-bundle reference
            try:
                exists = resolved.resolve().exists()
            except OSError:
                continue
            if not exists:
                findings.append(Finding("warning", rel,
                                        f"broken intra-bundle link -> {target!r}", line=lineno))
    return findings


# --------------------------------------------------------------------------- #
# Bundle driver
# --------------------------------------------------------------------------- #

def validate_bundle(root: Path, strict: bool) -> tuple[int, list[Finding]]:
    """Validate one bundle directory. Returns (md_file_count, findings)."""
    root = root.resolve()
    findings: list[Finding] = []
    md_files = sorted(root.rglob("*.md"))
    for path in md_files:
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(Finding("error", rel, "file is not valid UTF-8 (spec section 4)", line=1))
            continue
        name = path.name
        if name == "index.md":
            is_root_index = path.parent == root
            findings.extend(_validate_index(rel, text, is_root_index))
        elif name == "log.md":
            findings.extend(_validate_log(rel, text))
        else:
            findings.extend(_validate_concept(rel, text, strict))
        findings.extend(_check_links(rel, path, root, text))
    return len(md_files), findings


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _print_human(name: str, n_files: int, findings: list[Finding], quiet: bool) -> None:
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    shown = errors if quiet else findings
    verdict = "CONFORMANT" if not errors else "NONCONFORMANT"
    print(f"\n{name}  [{verdict}]  ({n_files} markdown file{'s' if n_files != 1 else ''}, "
          f"{len(errors)} error{'s' if len(errors) != 1 else ''}, "
          f"{len(warnings)} warning{'s' if len(warnings) != 1 else ''})")
    for finding in shown:
        print(finding.render())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate.py",
        description="Open Knowledge Format (OKF) v0.1 conformance checker.",
        epilog="Exit code 0 = conformant, 1 = errors found, 2 = usage error.",
    )
    parser.add_argument("paths", nargs="+", help="bundle directory/directories to validate")
    parser.add_argument("--strict", action="store_true",
                        help="also require title/description/timestamp (matches the OKF reference agent)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="hide warnings; show errors and the summary only")
    parser.add_argument("--version", action="version",
                        version=f"validate.py {CHECKER_VERSION} (OKF v{OKF_VERSION}; "
                                f"YAML parser: {'PyYAML' if _HAVE_YAML else 'built-in minimal'})")
    args = parser.parse_args(argv)

    bundles = []
    total_errors = 0
    total_warnings = 0

    for raw in args.paths:
        root = Path(raw)
        if not root.is_dir():
            print(f"error: not a directory: {raw}", file=sys.stderr)
            return 2
        n_files, findings = validate_bundle(root, args.strict)
        errors = sum(1 for f in findings if f.level == "error")
        warnings = sum(1 for f in findings if f.level == "warning")
        total_errors += errors
        total_warnings += warnings
        bundles.append((root, n_files, findings, errors, warnings))

    if args.json:
        payload = {
            "okf_version": OKF_VERSION,
            "checker_version": CHECKER_VERSION,
            "yaml_parser": "pyyaml" if _HAVE_YAML else "minimal",
            "conformant": total_errors == 0,
            "totals": {"errors": total_errors, "warnings": total_warnings},
            "bundles": [
                {
                    "path": str(root),
                    "files": n_files,
                    "conformant": errors == 0,
                    "errors": errors,
                    "warnings": warnings,
                    "findings": [f.to_dict() for f in findings],
                }
                for (root, n_files, findings, errors, warnings) in bundles
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0 if total_errors == 0 else 1

    if not _HAVE_YAML:
        print("note: PyYAML not found - using the built-in minimal parser "
              "(install PyYAML for fully-accurate YAML validation).", file=sys.stderr)

    for (root, n_files, findings, _errors, _warnings) in bundles:
        _print_human(root.name or str(root), n_files, findings, args.quiet)

    verdict = "CONFORMANT" if total_errors == 0 else "NONCONFORMANT"
    print(f"\n{'=' * 60}")
    print(f"OVERALL: {verdict}  -  {total_errors} error(s), {total_warnings} warning(s) "
          f"across {len(bundles)} bundle(s)")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
