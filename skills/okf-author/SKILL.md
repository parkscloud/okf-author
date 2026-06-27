---
name: okf-author
description: Author, convert, and validate Markdown in Open Knowledge Format (OKF) — the open, vendor-neutral spec for representing knowledge as a directory of Markdown files with YAML frontmatter. Use this skill when the user mentions OKF or is working inside an existing OKF bundle (apply OKF directly), and also when creating or substantially revising Markdown knowledge, reference, notes, or documentation files (offer OKF once). Do not use it for trivial or throwaway Markdown, code, chat prose, or content the user has not asked to structure.
---

# okf-author

Author, convert, and validate **Open Knowledge Format (OKF)** documents — skill version **1.4.1**.

OKF (Google Cloud, v0.1, released 2026-06-12) represents knowledge as a directory of
Markdown files with YAML frontmatter. The authoritative specification is vendored next to
this file at **`reference/SPEC.md`** and is the source of truth — when in doubt, read it.
A deterministic conformance checker (**`validate.py`**) and an index/log generator (**`generate_indexes.py`**) ship alongside.

## When to use this skill

- **Apply (no need to ask)** when the user mentions OKF, or the working directory is
  already an OKF bundle — detect that by a root `index.md`, files carrying `type:`
  frontmatter, or an `okf_version` declaration. In an OKF context, author and maintain
  documents in OKF automatically.
- **Offer (ask first)** when the user is creating or substantially revising a Markdown
  knowledge / reference / notes / documentation file outside any OKF context. Offer once:
  *"I can structure this as OKF (portable Markdown knowledge with YAML frontmatter) — want
  that?"* Proceed only on a yes.

Anti-nag rules: offer at most **once per directory per session**; never re-offer after a
decline; skip trivial/throwaway files (scratch notes, TODO lists, transcripts), code, and
prose the user has not asked to structure. All three modes below can also be invoked
explicitly at any time on request.

## OKF in brief (authoritative detail in `reference/SPEC.md`)

- A **bundle** is a directory tree of UTF-8 Markdown files. A **concept** is one `.md` file.
- A concept = a **YAML frontmatter block** (delimited by `---`) + a Markdown **body**.
- **Required frontmatter:** `type` — a short, descriptive, free-form string (e.g.
  `Reference`, `Playbook`, `Meeting`, `BigQuery Table`). Types are not registered centrally.
- **Recommended frontmatter (priority order):** `title`, `description` (one sentence),
  `resource` (canonical URI, if any), `tags` (list), `timestamp` (ISO 8601 last-modified).
- **Reserved filenames:** `index.md` — a directory listing for progressive disclosure, with
  **no frontmatter** (except the bundle-root `index.md`, which may carry `okf_version`); and
  `log.md` — chronological history whose `##` headings are ISO `YYYY-MM-DD` dates.
- **Links:** ordinary Markdown links express relationships. Both **relative** links
  (`../concepts/x.md`) and **bundle-absolute** links beginning with `/` (resolved from the
  bundle root) are conformant — but **prefer relative**: GitHub and other forges resolve a
  `/`-rooted link against the *repository* root, so bundle-absolute links break whenever the
  bundle is a subdirectory, while relative links render correctly wherever the bundle lives.
- **Conformance (§9):** every non-reserved `.md` has parseable frontmatter with a non-empty
  `type`, and reserved files follow their structure. Everything else is soft guidance —
  missing optional fields, unknown types, and broken links never make a bundle nonconformant.

### Frontmatter template

```yaml
---
type: <Concept type>                 # REQUIRED — short, descriptive
title: <Human-readable display name>
description: <One-sentence summary.>
resource: <https://canonical/uri>    # omit for purely abstract concepts
tags: [<tag>, <tag>]
timestamp: <YYYY-MM-DDTHH:MM:SSZ>   # ISO 8601, UTC 'Z'; real time of day when editing
---

# <Body — prefer headings, lists, tables, and fenced code over free prose>
```

### Timestamps

`timestamp` is the concept's **last-modified time**, an ISO 8601 datetime. Write it in **UTC**
with a trailing `Z` — `YYYY-MM-DDTHH:MM:SSZ` (e.g. `2026-06-27T15:30:42Z`); this is the form
the spec's own examples and Google's reference bundles use. **Never** emit a local-timezone
offset like `-04:00`. Two cases, by mode:

- **Authoring or live-editing** (Mode 1) → the **actual current UTC time**, including the real
  time of day, refreshed on each meaningful edit. Don't guess the clock — read it from the
  system: `date -u +%Y-%m-%dT%H:%M:%SZ`.
- **Converting an existing document** (Mode 2) → the source file's **last-modified date** at
  midnight UTC, `YYYY-MM-DDT00:00:00Z` — e.g. `date -u -r <file> +%Y-%m-%dT00:00:00Z` (or
  Python `os.path.getmtime`). The time of day is unknown for an import, so `00:00:00Z` honestly
  signals date-level precision.

`validate.py` accepts every UTC form and only warns when a `timestamp` isn't ISO 8601 at all
(e.g. a bare `2026-06-27` date); the rules above keep timestamps consistent, sortable, and
faithful to when each concept actually changed.

## Mode 1 — Author (new documents)

When writing a new document in an OKF context (or after the user accepts an offer):

1. **Choose `type`.** Infer a fitting type from the content and **confirm it** in one line.
   Reuse types already present in the bundle rather than inventing synonyms — keep the
   vocabulary consistent.
2. **Fill the recommended fields:** always set `title`, `description`, and `timestamp`; add
   `resource` when the concept maps to a real asset/URL, and `tags` for cross-cutting
   topics. For `timestamp`, use the **actual current UTC time** (real time of day, trailing
   `Z`) read from the system with `date -u +%Y-%m-%dT%H:%M:%SZ` — don't guess it; see
   **Timestamps** above.
3. **Write a structured body** — headings, lists, tables, fenced code. Use the conventional
   headings when they apply: `# Schema`, `# Examples`, `# Citations`.
4. **Link** to related concepts with **relative** links (e.g. `../concepts/glossary.md`) so
   they render correctly on GitHub and other forges wherever the bundle lives (see *Links* above).
5. **New bundle?** Ask the destination question (below), create the right entry files, then
   run `validate.py` on the result.

## Mode 2 — Convert (existing Markdown → OKF)

Default posture: **safe, staged, and non-destructive.** Never overwrite a user's files
without a clear, reversible plan.

1. **Pick an output mode.** If the target directory is a **clean git working tree**, convert
   **in place** (every change is reversible via git). Otherwise write a **parallel copy** at
   `<dir>-okf/` and say so — never silently mutate un-versioned originals.
2. **Show the plan first (dry run):** list which files get frontmatter, the `type` each will
   receive, and any structural changes. Convert only on the user's go-ahead.
3. **Stage 1 — frontmatter (safe, high value):** add a frontmatter block with `type` + smart
   defaults to each concept file. No renames, no moves. This alone makes a bundle conformant.
   Set each file's `timestamp` to its **last-modified date** at midnight UTC
   (`date -u -r <file> +%Y-%m-%dT00:00:00Z`) — see **Timestamps** above.
4. **Stage 2 — structure (opt-in):** only if the user wants it. Run the bundled
   **`generate_indexes.py`** to write each folder's `index.md` + `log.md` and the root
   `index.md` (with `okf_version`) deterministically from the frontmatter, instead of
   hand-writing them: `python generate_indexes.py <bundle> [--title "…"]`. Prefer **relative**
   links — bundle-absolute `/…` links break on GitHub when the bundle is a subdirectory.
   **Confirm every file rename**, and never delete an existing `README.md`.
5. **Validate** the result with `validate.py` and report.

### Destination question (README vs. index.md)

When creating a bundle's entry files, ask once: **"Is this going to GitHub or a similar git
host?"**

- **Yes →** maintain **both** `README.md` (the human/GitHub-rendered overview) **and**
  `index.md` (OKF's reserved listing, no frontmatter). GitHub auto-renders `README.md`, not
  `index.md`.
- **No →** `index.md` only (a `README.md` would be redundant where nothing renders it).
- Either way, never delete an existing `README.md`; if a non-forge bundle already has one,
  keep it and just ensure `index.md` exists.

### index.md and log.md templates

```markdown
# <Group / Section heading>

* [<Title>](<relative-link>) - <one-line description>
* [<Subdirectory>](subdir/index.md) - <what it contains>
```

```markdown
# Update Log

## 2026-06-20
* **Creation**: Established the [orders table](tables/orders.md).
* **Update**: Revised the SLA in the [freshness playbook](playbooks/freshness.md).
```

## Mode 3 — Validate

Run the bundled checker and report the verdict — do not eyeball conformance:

```bash
python validate.py <bundle-dir>            # spec §9 conformance; exit 0 = conformant
python validate.py --strict <bundle-dir>   # also require title/description/timestamp
python validate.py --json <bundle-dir>     # machine-readable output
```

Errors break conformance; warnings (missing recommended fields, non-ISO timestamps, broken
links) are advisory and never fail a bundle. Fix the errors, then re-run.

## Authority

`reference/SPEC.md` is the vendored OKF v0.1 specification (verbatim; Apache-2.0, © Google
LLC) and governs every rule above. If this skill and the spec ever disagree, the spec wins —
read it.

One deliberate, spec-permitted refinement: §5.1–5.2 make **both** link forms conformant and
the spec *recommends* bundle-absolute, but this skill prefers **relative** links because
bundle-absolute `/…` links break on GitHub and other forges when the bundle is a subdirectory.
