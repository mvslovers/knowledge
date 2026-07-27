# CLAUDE.md — MVSLOVERS Knowledge Base

This repository is the persistent memory of the MVSLOVERS ecosystem. It is written
primarily to be *read by an agent*, secondarily by humans.

Its purpose is **not** to be complete. Its purpose is to be **retrievable** and
**trustworthy**: an agent must be able to find the two paragraphs it needs, and must
be able to tell whether those paragraphs are fact, observation, or guess.

---

## 0. Prime directive

> **Never answer an MVS, JES2, HLASM, or MVSLOVERS-internals question from model
> priors. Answer from this knowledge base, or say that the KB does not cover it.**

Training data about MVS 3.8j, OS/390 and z/OS internals is sparse, outdated, and
frequently wrong in confident-sounding ways. This KB exists specifically to override
those priors.

Rules that follow:

1. When stating a non-obvious technical fact, cite the KB document ID that backs it
   (e.g. `[MVS-SSI-0003]`).
2. If the KB does not cover it, say so: *"Not in KB — this is my inference."*
3. If your priors contradict the KB, **the KB wins**. If you believe the KB is wrong,
   do not silently correct it — raise a conflict (§9).
4. Never upgrade the status of a claim. An `assumed` fact does not become `tested`
   because it sounded right in three consecutive answers.

---

## 1. Capabilities

Concrete and testable. If one of these stops being true, the KB is broken.

1. **Find.** Any documented fact is reachable in at most three tool calls, starting
   from `INDEX.md`, without loading the whole KB.
2. **Trust.** Every non-obvious claim carries a status and a source. An agent can
   tell manual-derived from source-derived from empirically-observed knowledge.
3. **Stay clean.** Contradictions, duplicates, and stale entries surface on ingest
   instead of sitting quietly next to each other for two years.
4. **Stay honest under platform drift.** Every claim states whether it applies to
   MVS 3.8j, z/OS, or both. This is the single most common source of wrong answers.
5. **Be portable.** Every project repo can consume the KB without copying it.

---

## 2. Language

- **Documents: English.** Community-facing, and shares vocabulary with IBM manuals
  and source listings.
- **`inbox/`: any language.** Raw capture must have zero friction. German is fine
  there; it gets translated during refinement.
- Quotes from manuals and listings stay verbatim, in their original form.

---

## 3. Layout

```
knowledge/
├── CLAUDE.md              ← you are here (router + rules, keep it small)
├── INDEX.md               ← GENERATED. do not hand-edit
├── mvs/                   ← domain knowledge. durable. mostly written once.
│   ├── architecture/      control blocks, ASID, storage keys, CSA/LPA, AMODE/RMODE
│   ├── supervisor/        SVC, dispatching, ATTACH, ESTAE/ESPIE, recovery
│   ├── subsystem/         SSCT/SSCVT, IEFSSREQ, SSI function codes
│   ├── jes2/              job lifecycle, JCT, internal reader, HASP internals
│   ├── data-mgmt/         DASD geometry, VTOC/DSCB, BSAM/QSAM/BPAM, catalogs
│   ├── tso-rexx/          IKJEFT01, IRXINIT/IRXTMPX, REXX host environments
│   ├── tcpip/             EZASOKET, TCP/IP for MVS API, socket semantics
│   ├── encoding/          EBCDIC codepages, CP037 vs IBM-1047, translation tables
│   ├── languages/         HLASM idioms, C on MVS, linkage conventions
│   └── tooling/           AMASPZAP, IEBCOPY, SMP/E, linkage editor, compilers
├── projects/              ← one dir per repo. THIN. deep detail stays in the repo.
│   └── <project>/
│       ├── OVERVIEW.md    what it is, who uses it, where the code lives
│       ├── CONTRACTS.md   stable external interfaces others depend on
│       └── decisions/     ADR-0001-*.md
├── ecosystem/             ← cross-cutting, spans repos
│   ├── MAP.md             dependency graph (generated Mermaid) + narrative
│   ├── build.md           mbt, toolchain, artifacts
│   ├── ci-cd.md           GitHub Actions patterns, cross-repo asset fetching
│   ├── conventions.md     naming, error codes, logging, versioning
│   └── release.md
├── playbooks/             ← "how do I …" runbooks. imperative, tested.
├── postmortems/           ← debugging war stories. THE HIGHEST-VALUE CONTENT.
├── sources/               ← bibliography. what we read, where it is.
│   ├── manuals.md         IBM pubs w/ order number, edition, local path
│   └── listings.md        source decks we have (JES2, compiler, linker, …)
├── conflicts/             ← open contradictions awaiting a human decision (§9)
├── log/                   ← ingest run log (§8)
└── inbox/                 ← raw, unrefined capture. never cited. drained regularly.
```

**Markdown is the only truth.** Every other artifact — `INDEX.md`, the dependency
graph, any search index — is a derived view, regenerated from these files, and may be
deleted at any time without losing knowledge. Nothing goes into a database.

**Why `projects/` is thin:** documentation that does not live next to the code it
describes rots. Implementation detail belongs in `<repo>/docs/`. This KB holds only
what outlives a refactor: purpose, external contracts, and *why* decisions were made.

---

## 4. Document format

Front matter is mandatory for everything outside `inbox/`:

```yaml
---
id: MVS-SSI-0003
title: SSCVT chain traversal and JESCT anchoring
status: source            # see §6
platform: [mvs38j]        # mvs38j | zos | both — DO NOT OMIT
sources:
  - "JES2 source: HASPSSSM, label SSVTSCAN"
  - "GC28-1150 MVS/XA SPL: System Macros and Facilities, 4-12"
verified_on: 2026-07-12   # when the claim was last checked against reality
applies_to: [ufsd, mvsmf]
tags: [ssi, sscvt, cross-address-space]
related: [MVS-ARCH-0007, UFSD-ADR-0002]
---
```

Body rules:

- **One topic per file.** If the title needs an "and", split it.
- **Atomic claims.** Short paragraphs, each independently quotable.
- **Show the evidence.** Paste the control-block offset, the macro expansion, the
  listing fragment. A claim with an artifact attached is worth ten without.
- **No narrative padding.** No "as we all know", no restating the title.

---

## 5. Identifiers

Stable IDs survive file moves; paths do not. Always cite by ID.

| Prefix              | Meaning                    | Example           |
| ------------------- | -------------------------- | ----------------- |
| `MVS-<AREA>-<nnn>`  | Domain knowledge           | `MVS-ENC-0004`    |
| `<PROJ>-ADR-<nnn>`  | Architecture decision      | `UFSD-ADR-0002`   |
| `ECO-<nnn>`         | Cross-cutting              | `ECO-0011`        |
| `PB-<nnn>`          | Playbook                   | `PB-0007`         |
| `PM-<yyyy>-<nnn>`   | Postmortem                 | `PM-2026-003`     |
| `CF-<yyyy>-<nnn>`   | Open conflict              | `CF-2026-014`     |

IDs are never reused and never renumbered. A retired document gets `status: obsolete`
and a `superseded_by:` field — it is not deleted. Knowing what used to be true, and
why we stopped believing it, is knowledge.

---

## 6. Status taxonomy

The backbone of the KB. Be pedantic about it.

| Status     | Meaning                                                           |
| ---------- | ----------------------------------------------------------------- |
| `source`   | Read in original source code or a listing. Cite module and label. |
| `manual`   | Documented in an IBM publication. Cite order number and page.     |
| `tested`   | We ran it on a real system and observed this. Cite the setup.     |
| `inferred` | Derived from `source`/`manual`/`tested` facts. Plausible, unproven.|
| `assumed`  | Working assumption. Actively needs validation.                    |
| `disputed` | Sources or observations conflict. Points at a `CF-` document.     |
| `myth`     | Widely believed, demonstrably false. Includes the correction.     |
| `obsolete` | Was true; no longer applies. Keep with `superseded_by:`.          |

`myth` documents are deliberately first-class and are high-priority reading — they
are the direct antidote to model priors.

When one document mixes confidence levels, tag inline:

```markdown
The SSCVT chain is anchored at JESCT+X'18'. `[source: HASPSSSM]`
The chain is not serialized during traversal. `[assumed]`
```

---

## 7. Retrieval ladder

When answering, climb down this ladder and **stop at the first rung that answers the
question**. Do not read the KB broadly. Do not load directories "for context".

1. **`INDEX.md`** — generated catalogue: one line per document (ID, title, status,
   platform, tags). A few hundred lines. Always the first read.
2. **`conflicts/`** — if the topic appears there, say so *before* answering.
3. **grep** on identifiers: control block names, macro names, module names, function
   codes, hex offsets. These are highly distinctive; plain-text search is excellent
   in this domain and needs no embeddings.
4. **Open exactly the documents you identified.** Not the folder. Documents are sized
   to be read whole.
5. **`postmortems/`** — if the question is "why does X fail", the answer lives here
   more often than in `mvs/`.
6. **The project repo itself**, for implementation detail below the contract level.

The point of the ladder is token discipline. Search cost dominate[118;1:3us: every search step
re-reads the whole conversation so far, so an unfocused search gets more expensive
each round. Two targeted rungs beat ten exploratory greps.

---

## 8. Ingest: how knowledge gets in

A knowledge base dies from write-friction. Two speeds.

### Two intakes, different lifecycles

`inbox/` is for **raw capture**: notes, transcripts, fragments. It is drained to
zero and its files are deleted after refinement. Its steady state is empty.

`sources/` is for **reference material**: IBM manuals, source listings, dumps,
converted PDFs. These are never distilled wholesale into KB documents — they are
catalogued so they can be *cited* when a question arises. Its steady state grows.

Large or binary material stays outside the repository. `sources/` holds only the
catalogue entry:

    ### SRC-0012 — IBM TCP/IP for MVS: API Reference
    order:    SC31-7187-03
    format:   PDF, 552 pp., converted from sc31718703.boo
    location: ~/mainframe/pubs/sc31718703.pdf
    covers:   EZASOKET call syntax, return/errno codes, ASYNC socket semantics
    why kept: only complete reference we have for the pre-OE socket API

### Fast path (always available)

Drop a file into `inbox/`. Any format, any language, no front matter. A terminal
transcript, a chat excerpt, three bullet points. Only requirement: a date in the
filename — `2026-07-27-ssi-post-race.md`.

### Ingest (batched, agent-driven)

Ingesting one inbox item:

1. Read the source.
2. Consult `INDEX.md` to determine which existing documents the topic touches.
   **Open only those.** Never the whole KB.
3. For each touched document, check whether the new information **contradicts** what
   is already there. Contradictions go to §9 — they are never silently resolved.
4. Integrate what fits: update affected documents, create missing ones, set
   `related:` links in both directions.
5. Assign IDs and front matter to anything new. Set `status` and `platform` honestly.
6. Split the item if it covers more than one topic.
7. Append a line to `log/ingest.md`: date, source, documents created, documents
   changed, conflicts raised.
8. Delete the inbox file.

The log is what separates a KB you have to believe from one you can check.

### Postmortems

After a long debugging session that produced real insight, **proactively offer to
write the postmortem**:

```
## Symptom      what was observed, verbatim (messages, ABEND codes, dump excerpts)
## Environment  system, versions, commit hashes
## Wrong turns  what we suspected and why it wasn't that   ← do not skip this
## Root cause   the actual mechanism
## Fix          commit / PR reference
## Extracted    new/changed KB documents that came out of this
```

*Wrong turns* saves the most future time and is always the most tempting to omit.

---

## 9. Conflicts

When new information contradicts existing information:

- **Do not overwrite. Do not decide.** Both statements stay, each with its source.
- Create `conflicts/CF-<yyyy>-<nnn>.md` stating both sides, their statuses, their
  platforms, and what evidence would settle it.
- Set `status: disputed` on every affected document and link the `CF-` ID. A conflict
  is marked everywhere it appears, not only where it was noticed.
- Surface it in the next answer that touches the topic.

**Do not confuse "different" with "contradictory."** Information that merely extends
or confirms an open point gets integrated normally. Only genuine incompatibility gets
marked; a KB that flags everything gets ignored.

### Weighing evidence

There is no total order, but useful heuristics:

- `tested` on the platform in question beats `manual`, when the manual documents a
  later release. IBM pubs routinely describe MVS/XA or ESA behaviour that 3.8j does
  not have. This is our most frequent conflict class.
- `source` beats `manual` for *what the code does*; `manual` beats `source` for *what
  the contract intends*. A behaviour visible in a listing may be an accident.
- Two conflicting `tested` results mean the environments differed. The missing
  variable is itself the knowledge — find it and document that instead.

### Resolution

Unlike a personal note vault, most of our conflicts are **decidable by experiment**.
A disputed control-block offset can be checked under Hercules in minutes. So a `CF-`
document has three possible outcomes, in order of preference:

1. **Experiment.** Write the test job or program, run it, record the result as
   `tested`, close the conflict. Prefer this whenever it is cheap.
2. **Human decision.** Mike decides which stand applies and why.
3. **Stays open.** Documented as such, with what would settle it.

**Repair the source, not the marker.** Deleting a conflict marker without fixing the
underlying documents means the next ingest finds the same conflict again.

---

## 10. Verification

Two questions, both measurable, both required.

**Does it help?** Maintain `benchmark/questions.md`: ten real questions from actual
work, with known-correct answers and the evidence for them. Run them with and without
the KB. Record correctness first, tokens and turns second. For us correctness is the
point — the failure mode we are buying insurance against is a confidently wrong
answer about an SSI function code, not a slow one.

**Is it still true?** `verified_on` ages. `tested` claims older than twelve months
and all `assumed` claims are review candidates, flagged by the linter.

Re-run the benchmark after any structural change to the KB. Without it we cannot tell
whether a reorganisation helped or quietly broke retrieval.

---

## 11. Tooling

Deterministic code does everything a machine can do reliably. The model is used only
where understanding is genuinely required — that is ingest, conflict detection, and
answering. Everything else is a script: same result every time, seconds, no cost.

- `tools/kb-index.py` — regenerates `INDEX.md` and `ecosystem/MAP.md`. Never edit
  those by hand.
- `tools/kb-lint.py` — must pass before commit. Checks: front matter present and
  schema-valid; `platform` set; IDs unique; referenced IDs exist; `related:` links
  bidirectional; `sources:` non-empty for `source`/`manual`; `verified_on` present
  for `tested`; every `disputed` document points at an existing `CF-`; flags stale
  `tested` and all `assumed`.

Semantic search (e.g. a local hybrid index) is deliberately **not** part of the base
system. Our vocabulary is unusually distinctive — module names, macro names, hex
offsets — and grep handles it well, while embeddings handle it poorly. Revisit only
if natural-language questions demonstrably fail the benchmark.

---

## 12. Anti-patterns

- Summarising an IBM manual instead of citing it and recording the specific fact we
  needed. The manual already exists; the KB records what *we learned from it*.
- Copying project README content into `projects/`. Link instead.
- Documents past ~300 lines. Split them.
- `status: source` without a module name.
- Marking something `tested` because it worked once, on one system, in 2019.
- Resolving a contradiction by picking the newer document.
- Fixing a bug without asking whether the underlying misunderstanding belongs here.
- Building the visualisation before the retrieval works.
