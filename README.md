# okf-author

> **STATUS: v1.2.0.** Cross-agent skill for authoring, converting, and validating Open
> Knowledge Format (OKF) Markdown — installable in **Claude Code** and **Codex**.
> Repo: <https://github.com/parkscloud/okf-author> · Design + decision log: [`DESIGN.md`](DESIGN.md).

A cross-agent **Agent Skill** that helps users author Markdown in **Open Knowledge Format
(OKF)** — and review/convert existing Markdown into it — from inside **Claude Code** and
**Codex**. Open-source (MIT) and public: anyone can install it.

## About Open Knowledge Format (OKF)

**OKF** is an open, vendor-neutral specification for representing knowledge — the metadata,
context, and curated insight around your data and systems — as a **directory of Markdown
files with YAML frontmatter**. Each file is one concept; files interlink with ordinary
Markdown links; the only required frontmatter field is `type` (with `title`, `description`,
`resource`, `tags`, and `timestamp` recommended).

- **Introduced:** **2026-06-12** by Google Cloud, released as **OKF v0.1** — formalizing the
  emerging "LLM-wiki" pattern into a portable, interoperable standard.
- **License:** the OKF specification itself is **Apache-2.0**.
- **Authoritative links:**
  - Specification: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
  - Announcement (Google Cloud blog): <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
  - Reference repository: <https://github.com/GoogleCloudPlatform/knowledge-catalog>

### Why use OKF

- **No lock-in.** It's just Markdown files in a directory — no proprietary platform,
  database, SDK, or account. If you can `cat` a file you can read it; if you can `git clone`
  a repo you can ship it.
- **Readable by humans *and* agents.** It renders on GitHub, opens in any editor, and is
  indexable by any search tool — while giving AI agents the accurate, curated context they
  need to reason about your data and systems.
- **Durable and diffable.** One version-controlled home for your knowledge, living next to
  the code it describes; every change shows up in a normal diff.
- **Interoperable.** A small set of agreed conventions lets knowledge written by one producer
  be consumed by different agents and tools without translation.

## What it does

`okf-author` is one skill with three modes:

- **Author** — new Markdown comes out OKF-conformant: a `type` plus smart-default frontmatter
  (`title`, `description`, `timestamp`, and `tags`/`resource` when applicable).
- **Convert** — bring existing Markdown into OKF safely and in stages (frontmatter first,
  structure second); in place when the directory is a clean git repo, otherwise into a
  parallel copy. Non-destructive by default. The bundled `generate_indexes.py` builds the
  per-folder `index.md`/`log.md` deterministically.
- **Validate** — check a bundle against OKF v0.1 §9 conformance with the bundled,
  dependency-free `validate.py`.

It activates when you mention OKF or work inside an existing OKF bundle, and otherwise
*offers* OKF once when you're authoring substantial Markdown. Full behavior:
[`skill/okf-author/SKILL.md`](skill/okf-author/SKILL.md).

## Install

From a clone of this repo (Python 3, standard library only — no `pip install`):

```bash
python3 install.py --all          # install into Claude Code and Codex
python3 install.py --claude       # Claude Code only
python3 install.py --codex        # Codex only
python3 install.py --all --dry-run   # preview, change nothing
```

(On Windows use `python` or `py` instead of `python3`.)

It installs the skill folder into:

- **Claude Code:** `~/.claude/skills/okf-author/`
- **Codex:** `~/.agents/skills/okf-author/` (per OpenAI's Codex skills docs; override with `--codex-dir`)

Then restart your agent (or open a new session) so it discovers the skill, and mention OKF or
ask it to author / convert / validate Markdown.

## Standalone tools

Both bundled tools are dependency-free (PyYAML used only if already installed) and run on their own:

```bash
# validate a bundle against OKF v0.1 conformance
python3 skill/okf-author/validate.py examples/handbook       # -> CONFORMANT
python3 skill/okf-author/validate.py --strict path/to/bundle # also require title/description/timestamp
python3 skill/okf-author/validate.py --json path/to/bundle   # machine-readable

# (re)generate index.md + log.md across a bundle from its frontmatter
python3 skill/okf-author/generate_indexes.py path/to/bundle --title "My Knowledge Base"
python3 skill/okf-author/generate_indexes.py path/to/bundle --dry-run
```

Exit code `0` = conformant, `1` = errors, `2` = bad path. Warnings (missing recommended
fields, non-ISO timestamps, broken links) are advisory and never fail a bundle. PyYAML is
used if installed; otherwise a built-in minimal parser handles the conformance checks.

## Repository layout

```
okf-author/
├── README.md · DESIGN.md · CLAUDE.md · LICENSE · install.py
├── skill/okf-author/        # the installable skill (this folder is what install.py copies)
│   ├── SKILL.md             # the skill: Author / Convert / Validate
│   ├── validate.py          # dependency-free OKF v0.1 conformance checker
│   ├── generate_indexes.py  # deterministic index.md / log.md generator
│   └── reference/           # vendored OKF spec (verbatim) + license + attribution
└── examples/handbook/       # a tiny conformant example bundle
```

## Author & maintainer

Created and maintained by **Robert Parks** — <raparks@icloud.com>.
Issues and contributions welcome.

## License

Licensed **[MIT](LICENSE)** for okf-author's own code. The vendored OKF specification
(`skill/okf-author/reference/SPEC.md`) remains © Google LLC under **Apache-2.0** and is
included verbatim with attribution (see `skill/okf-author/reference/`).

## References

- Agent Skills (Anthropic, open `SKILL.md` format): <https://github.com/anthropics/skills>
- Codex skills: <https://developers.openai.com/codex/skills>
- Prior-art community OKF skill (reference only): <https://github.com/scaccogatto/okf-skills>
- OKF specification and announcement: see **About Open Knowledge Format (OKF)** above.
