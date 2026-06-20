# okf-author — Design Specification

**Status: v1.3.0 — released 2026-06-20.** All eleven decisions are settled in §2; every build
stage (§7) is complete and verified; published at <https://github.com/parkscloud/okf-author>.

## 1. Summary

`okf-author` is a cross-agent Agent Skill (Claude Code + Codex) that makes the
markdown documents an LLM agent writes conform to **Open Knowledge Format (OKF)**,
and that can review and convert previously written markdown into OKF on request.
OKF v0.1 (Google Cloud, 2026-06-12) represents knowledge as a directory of markdown
files with YAML frontmatter; the only required frontmatter field is `type`.

### Goals (provisional)

- **Generic and public** — written for any user, with no organization-specific
  vocabulary baked in; intended to be released publicly so anyone can install it.
- Installable in **both** Claude Code and Codex by any user, from one source of truth.
- **Author mode:** new markdown is OKF-conformant from the first save.
- **Convert mode:** any existing directory of markdown can be reviewed and brought
  into OKF.
- **Validate mode:** check a bundle against OKF v0.1 conformance rules (§9 of SPEC).
- Authoritative: track the official OKF spec rather than paraphrasing it.

### Non-goals (provisional)

- Reimplementing OKF or diverging from the official spec.
- A hosted service or any infrastructure (this is a skill, not a deployment).
- Forcing conversion of every existing document (conversion is opt-in, per request).

## 2. Decision log

Decisions made with the user, one at a time. Each open question in §3 becomes a
`Dnn` row here once signed off.

| #  | Decision | Choice | Rationale |
|----|----------|--------|-----------|
| D1 | Skill name | `okf-author` | Reads as a clear role and subsumes both authoring and conversion; distinct from the community `okf` namespace (`scaccogatto`), so both can coexist; lowercase-kebab per the Agent Skills convention, so the one string serves as the repo directory, the skill `name:`, and the `/okf-author` invocation. Decided 2026-06-20. |
| D2 | Audience & scope | Generic and public — for any user, no user/organization-specific vocabulary baked in; the repo will be published publicly for anyone to install | Keeps v0.1 tight and reusable, and is the path toward a clean, openly available skill. A per-user personalization layer (optional profile) is a possible future enhancement, not part of v0.1. Decided 2026-06-20. |
| D3 | Cross-agent packaging | Single hand-authored `SKILL.md` as the source of truth + a cross-platform `install.py --all\|--claude\|--codex` that copies the self-contained skill folder into `~/.claude/skills/okf-author/` (Claude Code) and Codex's skills dir | No build/transform step and no hosting; `git clone` then `python install.py --all` works on Windows/Mac/Linux. `SKILL.md` *is* the product, so it is the single source of truth. Repo laid out so a Claude Code plugin/marketplace can be added later for one-command install without reworking the skill. Decided 2026-06-20. |
| D4 | Structure & activation | One skill (single `SKILL.md`) with three modes — Author, Convert, Validate. Hybrid trigger: **apply** OKF when the user mentions OKF or is working inside an existing OKF bundle; **offer** (ask, proceed on yes) for any other markdown authoring. Anti-nag: offer once per directory/session, skip throwaway files, never re-offer after a decline | Model-invoked via a deliberately broad `description`, so it works in both Claude and Codex; best-effort by nature, so the offer is gated to avoid nagging. A deterministic Claude-Code-only `.md`-write hook was considered and deferred (Claude-only, separate install, more invasive) — revisit only if the soft offer proves unreliable. Decided 2026-06-20. |
| D5 | Type taxonomy & frontmatter | Spec-faithful with smart defaults: require only `type` (per spec); when authoring, infer a fitting `type` from content and confirm it, and auto-populate `title`, `description`, `timestamp` (add `tags`/`resource` when they apply). No hardcoded type enum; keep types consistent within a bundle (reuse existing types, avoid synonyms). Docs ship a short, non-binding "common types for inspiration" list | Honors OKF's rule that types are free-form and not centrally registered (and the D2 generic goal), while still producing rich, useful frontmatter instead of thin docs. Decided 2026-06-20. |
| D6 | Conversion behavior | Safe & staged. Output: convert in-place only when the directory is a clean git repo (reversible); otherwise write a parallel `*-okf/` copy — never silently mutate un-versioned originals. Plan-first (dry-run by default); convert on the user's go-ahead. **Stage 1** adds frontmatter (`type` + smart defaults), no renames; **Stage 2** (opt-in) is structural — add `index.md` (keep `README.md`), create `log.md`, rewrite links to bundle-relative (**SUPERSEDED by D10** — prefer relative, not bundle-absolute `/`-rooted, links), add `okf_version`; file renames always confirmed. `README.md` is kept with an `index.md` added alongside (humans on GitHub vs. agents navigating), not renamed | Non-destructive by default protects users' files (D2 generic/public + safety-first); staging delivers high-value frontmatter before any risky structural change; git-gating makes in-place edits reversible. Verified 2026-06-20 against GitHub docs: GitHub auto-renders a `README` file (looked up in `.github`, then root, then `docs`) at the top of a repo/folder view, whereas `index.md` is not rendered that way in the file browser (it is only the served page under GitHub Pages) — so `README.md` must remain the human/GitHub face. Decided 2026-06-20. |
| D7 | Spec vendoring + validation | (a) Vendor Google's `SPEC.md` **verbatim** inside the skill (Apache-2.0; license + attribution preserved), pinned to OKF **v0.1**; `SKILL.md` treats the vendored copy as the source of truth and notes the pinned version (refresh when OKF revs). (b) Ship a **dependency-free** `validate.py` (Python stdlib only) that checks a bundle against OKF §9 conformance — frontmatter present + parseable, non-empty `type`, reserved-file rules, link sanity — and prints pass/fail; uses `PyYAML` for stricter parsing only if already installed, never requires it | Pushes correctness onto the real spec rather than model memory (matches the verify-empirically goal and D5); a zero-install validator keeps the same friction-free bar as `install.py` (D3). Decided 2026-06-20. |
| D8 | License & hosting | okf-author's own code (`SKILL.md`, `install.py`, `validate.py`) under **MIT**; the vendored `SPEC.md` retains its original **Apache-2.0** + attribution. Publish as a **public** repo at **`github.com/parkscloud/okf-author`** (push only on the user's go-ahead) | MIT is the shortest, most common license for a small dev tool/skill and pairs cleanly with the Apache-2.0 vendored file; public + `parkscloud` matches the D2 generic/public goal. Decided 2026-06-20. |
| D9 | README vs. `index.md` by destination | **Always ask** (once per bundle): the skill asks whether the project is headed to GitHub or a similar forge. Forge-bound → maintain **both** `README.md` (human/forge-rendered overview) + `index.md` (OKF reserved listing, no frontmatter); not forge-bound → **`index.md` only**. Non-destructive (D6): an existing `README.md` is never deleted — if not forge-bound but one exists, leave it and ensure `index.md` exists (optionally offer Stage-2 consolidation). Asked once per bundle, not per file (D4 anti-nag) | User chose an explicit ask over inference for predictability and control; a `README.md` earns its place only where a forge auto-renders it (verified in D6). Decided 2026-06-20. |
| D10 | Cross-link form (relative vs. bundle-absolute) | Recommend **relative** Markdown links (e.g. `../concepts/x.md`); do not rewrite to bundle-absolute `/`-rooted links. Supersedes the link-form choice in D6. `validate.py` accepts both forms; `generate_indexes.py` already emits relative links. | Both forms are conformant (spec §5.1–5.2), so this is a spec-permitted preference, not a violation — but GitHub and other forges resolve a `/`-rooted link against the **repository** root, so bundle-absolute links break whenever the bundle is a subdirectory. Verified empirically 2026-06-20 on the live repo: in `examples/handbook/concepts/onboarding.md`, GitHub rendered `/concepts/glossary.md` as `…/blob/main/concepts/glossary.md` — a 404, since the file lives under `examples/handbook/`. Relative links render correctly wherever the bundle sits, preserving OKF's "renders on GitHub" promise. Decided 2026-06-20. |
| D11 | Distribution & auto-update (plugin packaging) | Repackage the repo as a **Claude Code plugin** (`.claude-plugin/plugin.json`) plus a **self-hosted marketplace** (`.claude-plugin/marketplace.json`, `source: ./`) so Claude Code users can `/plugin marketplace add parkscloud/okf-author` and opt into auto-update; rename `skill/`→`skills/` for default skill discovery. Keep `install.py` (copy method) for Codex + manual installs — Codex has no plugin/auto-update mechanism. | A copied skill cannot self-update; the plugin marketplace is the only native auto-update path (verified against Claude Code docs + `claude plugin validate`). Self-hosting our own marketplace lets anyone install + auto-update immediately, independent of Anthropic. Note: you cannot submit to `claude-plugins-official` (curated by Anthropic at its discretion, no application process); third-party submissions go to the **community** marketplace via an in-app form (individuals: platform.claude.com/plugins/submit), must pass `claude plugin validate` + automated safety screening, and sync nightly. Decided 2026-06-20. |

## 3. Open decisions (planning queue)

_All planning decisions are resolved — D1–D11 in §2, as of 2026-06-20._ The finalized
design follows: repo layout (§5), skill behavior (§6), and the staged build plan (§7).
Implementation begins after sign-off.

## 4. References & reused patterns

- OKF spec (canonical): `GoogleCloudPlatform/knowledge-catalog` → `okf/SPEC.md`
  (Apache-2.0). Required field: `type`. Recommended: `title`, `description`,
  `resource`, `tags`, `timestamp`. Reserved files: `index.md`, `log.md`.
  Versioning via optional `okf_version` in the bundle-root `index.md`.
- **Cross-agent install pattern to reuse:** a small cross-platform script
  (e.g. `install.py --all` / `--claude` / `--codex`) that copies the self-contained
  skill folder into `~/.claude/skills/<name>/` (Claude Code) and
  `~/.agents/skills/<name>/` (Codex). Repo conventions worth keeping: a tight root
  layout (`README.md` + `DESIGN.md` + the skill at root), `docs/` for plans, and a
  `Dnn` decision log.
- Prior-art community skill (reference, not a dependency): `scaccogatto/okf-skills`
  — vendors `SPEC.md` verbatim, ships author/validate/visualize, MIT.

## 5. Repo layout

```
okf-author/
├── .claude-plugin/               # Claude Code plugin packaging (D11)
│   ├── plugin.json               # plugin manifest (name, version, metadata)
│   └── marketplace.json          # self-hosted marketplace: lists this plugin (source ./)
├── README.md                     # orientation, status, install steps (the human/GitHub face)
├── DESIGN.md                     # this spec + decision log
├── CLAUDE.md                     # guidance for AI agents working in this repo
├── LICENSE                       # MIT — okf-author's own code (D8)
├── install.py                    # cross-platform installer (D3): copies skills/okf-author/ into the agents' skills dirs
├── skills/
│   └── okf-author/               # the self-contained skill — install.py copies it; the plugin discovers it
│       ├── SKILL.md              # name + description frontmatter + Author/Convert/Validate instructions
│       ├── validate.py           # dependency-free OKF v0.1 conformance checker (D7); also runnable standalone
│       ├── generate_indexes.py   # deterministic index.md / log.md generator (D6 Stage 2); also runnable standalone
│       └── reference/
│           ├── SPEC.md           # OKF v0.1 spec, vendored verbatim (D7) — pinned commit ee67a5c
│           ├── SPEC-LICENSE.txt  # Apache-2.0 license (upstream LICENSE.md, verbatim)
│           └── ATTRIBUTION.md    # provenance: source, pinned commit, SHA-256, license
└── examples/
    └── handbook/                 # a tiny conformant example bundle
```

- **install.py** — run from a clone; `--all` / `--claude` / `--codex` copy `skills/okf-author/`
  into `~/.claude/skills/okf-author/` and Codex's skills dir. Python stdlib only; Windows/Mac/Linux.
- **skills/okf-author/SKILL.md** — the product. Broad `description` for the hybrid trigger (D4);
  body covers the three modes (§6).
- **skills/okf-author/validate.py** — copied with the skill so Validate mode can call it; also
  runnable directly (`python validate.py <dir>`).
- **skills/okf-author/generate_indexes.py** — copied with the skill; (re)generates `index.md` /
  `log.md` from concept frontmatter for Convert Stage 2 (§6); also runnable directly.
- **skills/okf-author/reference/SPEC.md** — the authority the skill reads (D7), pinned to OKF v0.1.

## 6. Skill behavior (SKILL.md modes)

- **Trigger (D4):** apply OKF when the user mentions OKF or is inside an existing OKF bundle;
  otherwise *offer* once per directory/session for substantive markdown; never re-offer after a decline.
- **Author (D5, D9):** infer a fitting `type` from content and confirm it; populate `title`,
  `description`, `timestamp` (+ `tags`/`resource` when apt); keep types consistent within the bundle.
  For a new bundle, ask whether it's headed to GitHub/a forge → both `README.md` + `index.md`,
  else `index.md` only.
- **Convert (D6):** safe & staged. In-place only in a clean git repo, else a parallel `*-okf/` copy;
  plan/dry-run first, convert on go-ahead. Stage 1 = frontmatter; Stage 2 (opt-in) = structure
  (add `index.md`, `log.md`, relative links (D10), `okf_version`), renames always confirmed;
  an existing `README.md` is never deleted.
- **Validate (D7):** run `validate.py` and report pass/fail against §9 — don't eyeball.
- **Authority (D7):** defer to `reference/SPEC.md` for all rules; the skill summarizes, the
  vendored spec governs.

## 7. Build plan (staged; commit per stage, push on go-ahead)

1. **Scaffold + vendor** — **DONE (2026-06-20).** `LICENSE` (MIT), the `skills/okf-author/`
   dir, and the vendored `SPEC.md` + `SPEC-LICENSE.txt` + `ATTRIBUTION.md`. Byte-identity
   verified: local SHA-256 == fresh upstream pull (`b9655e60…ad6e`); pinned commit `ee67a5c`
   (2026-06-12).
2. **validate.py** — **DONE (2026-06-20).** Dependency-free checker (PyYAML used only when
   already installed). Implements the §9 rules; warnings never affect the exit code; `--strict`
   promotes title/description/timestamp to errors; `--json`/`--quiet`/`--version` supported.
   Verified: CONFORMANT on all three Google bundles (ga4/crypto_bitcoin/stackoverflow, 78 md
   files, 0 errors), correct errors on 6 isolated broken fixtures, and the minimal-parser
   fallback agrees with PyYAML.
3. **install.py** — **DONE (2026-06-20).** Cross-platform copy installer
   (`--all`/`--claude`/`--codex`, `--dry-run`, `--claude-dir`/`--codex-dir` overrides).
   Codex path confirmed as `~/.agents/skills/` against OpenAI's official Codex docs (some
   third-party guides wrongly cite `~/.codex/skills/`). Verified by subagent: dry-run, real
   install into both roots (correct files, no `__pycache__`, exec bit preserved), clean
   re-install, and the no-target error (exit 2).
4. **SKILL.md** — **DONE (2026-06-20).** One skill, three modes (Author/Convert/Validate) with
   the hybrid trigger, smart-default frontmatter, safe-staged conversion, and the
   README-vs-`index.md` destination question. End-to-end verified: a subagent followed SKILL.md
   to convert real meeting notes (copied to `/tmp`) into a bundle that passed `validate.py`
   (default and `--strict`); SKILL.md judged clear and complete, source left untouched.
5. **Polish + release** — **DONE (2026-06-20).** Finalized `README.md` (install/usage/layout),
   added `CLAUDE.md` and an example bundle (`examples/handbook`), bumped all version markers to
   **v1.0.0**, created the public repo `github.com/parkscloud/okf-author`, pushed `main` + tag
   `v1.0.0`, and published the v1.0.0 release.
6. **Plugin packaging** — **DONE (2026-06-20).** Repackaged as a Claude Code plugin + self-hosted
   marketplace (`.claude-plugin/plugin.json` + `marketplace.json`, `source: ./`); renamed
   `skill/`→`skills/` for default skill discovery; kept `install.py` for Codex/manual installs.
   Verified with `claude plugin validate --strict` (plugin + marketplace manifests). Released as
   **v1.3.0** (D11).

## 8. Versioning

The project uses semantic-style versions, starting at **0.0.1**.

- **0.0.x** — pre-release scaffolding and early development (current).
- **0.1.0** — first installable, functional skill (Author/Convert/Validate working,
  `install.py` verified on both agents).
- **1.0.0** — stable public release.

Bump rules: during `0.x`, **patch** = fixes/docs; **minor** = new capability or a new
logged decision; a `minor` may include breaking changes while pre-1.0. The version is
carried in the `README.md` status banner, the `SKILL.md` banner (once it exists), and a
matching **git tag** (`vMAJOR.MINOR.PATCH`) — bump them together; the git tag is canonical.

| Version | Date | Notes |
|---------|------|-------|
| 0.0.1 | 2026-06-20 | Initial scaffold: README, DESIGN (decisions D1–D9), MIT LICENSE, vendored OKF v0.1 spec. |
| 1.0.0 | 2026-06-20 | First functional release: `validate.py`, `SKILL.md` (three modes), `install.py` (Claude Code + Codex), `examples/handbook`, `CLAUDE.md`, full docs. Verified against Google's bundles, broken fixtures, and an end-to-end conversion. |
| 1.0.1 | 2026-06-20 | `validate.py`: URL-decode link targets so percent-encoded (`%20`) intra-bundle links resolve — removes false-positive broken-link warnings. |
| 1.1.0 | 2026-06-20 | Add `generate_indexes.py`: deterministically (re)generates per-folder `index.md` + `log.md` and the root `index.md` (`okf_version`) from concept frontmatter. |
| 1.2.0 | 2026-06-20 | **D10:** recommend **relative** cross-links over bundle-absolute `/`-rooted links (which break on GitHub/forges when the bundle is a subdirectory — verified live); updated SKILL.md guidance + templates and the `examples/handbook` bundle (`generate_indexes.py` already emitted relative links). Also corrected the §5 repo-layout tree (added `CLAUDE.md` + `generate_indexes.py`; dropped the never-created `docs/`). |
| 1.3.0 | 2026-06-20 | **D11:** repackage as a Claude Code **plugin** + self-hosted **marketplace** (`.claude-plugin/`) with opt-in auto-update; rename `skill/`→`skills/` for default discovery; keep `install.py` for Codex/manual. Validated with `claude plugin validate --strict`. |
