# okf-author

> **STATUS: v0.0.1 — in development (pre-release).** Scaffold + vendored spec done;
> the skill itself (`SKILL.md`, `install.py`, `validate.py`) is not written yet.
> Full spec + decision log: [`DESIGN.md`](DESIGN.md).

A cross-agent **Agent Skill** that helps users author markdown in **Open Knowledge
Format (OKF)** — and review/convert existing markdown into it — from inside **Claude
Code** and **Codex**. Open-source and public: anyone can install it.

## About Open Knowledge Format (OKF)

**OKF** is an open, vendor-neutral specification for representing knowledge — the
metadata, context, and curated insight around your data and systems — as a **directory
of Markdown files with YAML frontmatter**. Each file is one concept; files interlink
with ordinary Markdown links; the only required frontmatter field is `type` (with
`title`, `description`, `resource`, `tags`, and `timestamp` recommended).

- **Introduced:** **2026-06-12** by Google Cloud, released as **OKF v0.1** —
  formalizing the emerging "LLM-wiki" pattern into a portable, interoperable standard.
- **License:** the OKF specification itself is **Apache-2.0**.
- **Authoritative links:**
  - Specification: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
  - Announcement (Google Cloud blog): <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
  - Reference repository: <https://github.com/GoogleCloudPlatform/knowledge-catalog>

### Why use OKF

- **No lock-in.** It's just Markdown files in a directory — no proprietary platform,
  database, SDK, or account. If you can `cat` a file you can read it; if you can
  `git clone` a repo you can ship it.
- **Readable by humans *and* agents.** It renders on GitHub, opens in any editor, and
  is indexable by any search tool — while giving AI agents the accurate, curated
  context they need to reason about your data and systems.
- **Durable and diffable.** One version-controlled home for your knowledge, living next
  to the code it describes; every change shows up in a normal diff.
- **Interoperable.** A small set of agreed conventions lets knowledge written by one
  producer be consumed by different agents and tools without translation.

`okf-author` packages these rules as an installable skill so the documents an agent
writes are conformant from the start, and so older Markdown can be brought into
conformance on request.

## What it does (planned)

- **Author** — when you create a Markdown document, apply OKF frontmatter and
  conventions so it conforms from the first save.
- **Convert** — review prior Markdown and bring it into OKF (add frontmatter and
  `type`, fix links, introduce reserved files).
- **Validate** — check a directory ("bundle") against the OKF v0.1 conformance rules.

## Install (planned — cross-agent)

One source, installed for both agents (mechanism in [`DESIGN.md`](DESIGN.md)):

- Claude Code: `~/.claude/skills/okf-author/`
- Codex: `~/.agents/skills/okf-author/` (exact location verified during build)

## Author & maintainer

Created and maintained by **Robert Parks** — <raparks@icloud.com>.
Issues and contributions are welcome once the repository is public.

## License

Licensed **[MIT](LICENSE)** for okf-author's own code. The OKF specification, once
vendored at `skill/okf-author/reference/SPEC.md`, remains © Google LLC under
**Apache-2.0** and is included verbatim with attribution.

## References

- Agent Skills (Anthropic, open `SKILL.md` format): <https://github.com/anthropics/skills>
- Prior-art community OKF skill (reference only): <https://github.com/scaccogatto/okf-skills>
- OKF specification and announcement: see **About Open Knowledge Format (OKF)** above.
