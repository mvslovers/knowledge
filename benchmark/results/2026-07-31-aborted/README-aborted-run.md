# Aborted baseline run — 2026-07-31

**Not a valid measurement. Do not score it or compare anything against it.**

Kept because six of the answers are substantively informative, and because the two
defects below are worth not repeating.

## What was run

- Arm: without-KB (baseline)
- Harness: `claude -p --output-format json --disallowedTools "WebSearch,WebFetch" --max-turns 3`
- Working directory: `~/kb-baseline` — **this was the mistake, see defect 2**
- Questions: 9 of 10 (`Q-03` blocked, see `CF-2026-001`), 3 runs each = 27 invocations
- Model: _(fill in from `modelUsage` in any of the JSON files)_

## Defect 1 — 21 of 27 invocations returned no result

Only `Q-04-r2`, `Q-06-r1`, `Q-09-r2`, `Q-09-r3`, `Q-10-r1`, `Q-10-r3` produced a
`result` field. The remaining 21 are `null`. File size is a reliable tell: every
1.6k/2.0k JSON is empty, every file above 3k carries an answer.

Cause not conclusively established at the time of filing. The two candidates are
`--max-turns 3` being exhausted, and repeated denied tool calls under
`--disallowedTools` burning the turn budget. Check `stop_reason`,
`terminal_reason`, and `permission_denials` in the empty files if it matters later.

Mitigation for the re-run: `--max-turns 1`, and check `has("result")` inside the
loop rather than after it.

## Defect 2 — the model could read the other questions

`questions/` and `results/` sat in the working directory. The model listed it:

- `Q-09-r2` opens by noting the working directory holds only `questions/` and
  `results/`.
- `Q-06-r1` refers to *"the same hazard as Q-07 in your set"* — it knew about a
  question it had not been asked.

Cross-question contamination of exactly the kind the per-question-session protocol
was meant to prevent, arriving by a filesystem path instead of by conversation
carryover.

Mitigation for the re-run: run from an empty working directory with the question
files and the output directory both outside it.

## What is still usable

The six answers stand on their own as evidence of what the model produces without
the KB. Findings, in order of value:

### Q-09 — the z/OS reflex, in pure form

Both runs independently diagnose the abend in terms of Language Environment:
XPLINK, CAA in R12, DSA, NAB at offset 76, CEEDUMP, `STORAGE(00,FE,00)`,
`TERMTHDACT(UAALL)`, `#pragma linkage(name, OS)`. None of this exists on MVS 3.8j.
The actual cause — as370 assembling RS-format `D(,B)` with base 0, so registers are
restored from PSA low core — appears in neither answer.

Fluent, specific, internally consistent, and drawn entirely from a platform the
target system does not have. This is the failure mode the knowledge base exists to
prevent, and these two answers are the reference text for the first `myth`
document.

### Q-04 — right value, fabricated provenance

The answer correctly states ASCII `0x0A` → EBCDIC `0x15`. Its entire justification,
however, is about **Apache HTTP Server's z/OS port** — `os_toascii[]`,
`os/os390/ebcdic.c`, Martin Kraemer — and it closes by offering to check the table
rows against a specific httpd/APR release. It is describing a different codebase
throughout and does not know it.

This raises a rubric question that must be settled **before** the with-KB arm runs,
so that the answer cannot be chosen to favour the KB: does a correct value with
invented provenance pass? Current recommendation is no — sourced provenance is the
point of the KB, and a coincidental hit is not the capability being measured.

### Q-06 — passes without the KB

Two C environments, separate writable static areas, and the vector-table data-slot
fix, substantially correct from priors alone. Recorded as an honest negative: not
every question in the set needs the KB.

### Q-10 — partial

`r1` reaches "per-block clip" and is in the right neighbourhood, but attributes it
to library BLKSIZE rather than to a fixed buffer in our own linker. `r3` goes to
CCW/IDAW chain length and misses.

## Follow-ups this run generated

- First `myth` document: MVS 3.8j has no Language Environment. Source text for it
  is `Q-09-r2` and `Q-09-r3` in this directory.
- Rubric decision on Q-04 (provenance), to be made before the with-KB arm.
