# CLAUDE.md

Guidance for AI coding agents working in this repository.

## What this is

`okf-author` is a cross-agent Agent Skill (Claude Code + Codex) for authoring, converting,
and validating Markdown in **Open Knowledge Format (OKF)**. The product is the skill in
`skill/okf-author/`; everything else supports building, documenting, and installing it.

## Source-of-truth chain

- **`skill/okf-author/SKILL.md`** is the skill and the single source of agent-facing behavior.
- **`skill/okf-author/reference/SPEC.md`** is the OKF v0.1 specification, vendored verbatim
  (Apache-2.0, © Google LLC). It is authoritative for all OKF rules — point to it from SKILL.md
  rather than paraphrasing. Provenance (source, pinned commit, SHA-256): `reference/ATTRIBUTION.md`.
- **`skill/okf-author/validate.py`** is the deterministic §9 conformance checker (stdlib-only;
  PyYAML used only if already installed). It ships inside the skill so Validate mode can call it.
- **`install.py`** (repo root) copies `skill/okf-author/` into each agent's skills directory.
- **`DESIGN.md`** is the spec + decision log (D1–D9) + build plan + versioning. Read the
  relevant decision before changing behavior.

## Working rules

- Keep the skill self-contained: anything `SKILL.md` needs at runtime must live under
  `skill/okf-author/` — that folder is the only thing `install.py` copies.
- Do not hand-edit `reference/SPEC.md`; it is vendored. To track a new OKF version, re-vendor it
  and refresh `reference/ATTRIBUTION.md` (source URL, pinned commit, SHA-256).
- After changing `validate.py` or `SKILL.md`, re-verify (see Test below).
- Versioning: see `DESIGN.md` §8. Bump the `README.md` banner, the `SKILL.md` banner, and the
  git tag together.

## Test

```bash
python3 skill/okf-author/validate.py examples/handbook   # expect CONFORMANT, exit 0
python3 skill/okf-author/validate.py --strict examples/handbook
python3 install.py --all --dry-run                       # preview install, change nothing
```
