---
id: PM-2026-002
title: Load module truncates past 16 KB — ld370's TXT-card reader silently dropped text, it was never FETCH
status: tested
platform: [mvs38j]
sources:
  - "cc370/docs/multitext-fetch-truncation.md — the full investigation including the refuted phases"
  - "cc370/ld370/src/ld370.c:201-210, 285-292, 1898-1908 — the comment recording both bugs, the realloc growth, RLDMAX"
  - "cc370 commit de39a60 — fix(ld): emit complete object text for multi-text load modules"
  - "cc370 commit 47a6cc7 — fix(ld): split RLD records to <= 236 bytes so program fetch can relocate them"
  - "cc370 commit 6e4dbef — fix(ld370): grow rld/ld on demand (>512 RLD items clobbered LD symbols)"
verified_on: 2026-06-21
applies_to: [cc370, libc370, httpd, rexx370]
tags: [ld370, linker, load-module, txt-card, s0c1, s106, iewfetch, amblist, rld, truncation, postmortem, toolchain]
related: [PM-2026-001]
---

## Symptom

A load module built by `ld370` installs via `--xmit` → RECV370, starts executing, then
takes **S0C1** at a roughly fixed point a little past 16 KB in.

- AMBLIST and the control-record CCW counts both reported the module at its full
  expected size.
- Load point (EPA `0x095590`) and extent (`0x4A70`, 19056) were correct.
- Everything past the cut was **zeros**.

Two reproductions, and the second is the decisive one:

| run | record layout | observed cut | where it falls |
|---|---|---|---|
| original | text1 = 12288, text2 = 12288 | load+0x3FF8 = **16376** | inside text2 |
| `--t1 17000 --t2 2056` | text1 = 17000, text2 = 2056 | load+0x3FE0 = **16352** | **inside text1** |

The cut lands **inside a single text record**, so it is neither a "second text record"
problem nor a track crossing. It sits at a fixed *cumulative* text offset, independent
of how the module was carved into records.

## Environment

MVS 3.8j under Hercules, install via RECV370. `ld370` from the cc370 repo. Harness
`ld370/tests/run_nopt_mvs.py` with `--t1` / `--t2` sizes. Resolved 2026-06-21.

## Root cause

**In the linker's own object reader. The emitted member is already short.**

`struct obj` in `ld370/src/ld370.c` held each object's text in a **fixed 16384-byte
array** (`unsigned char text[1 << 14]`), and the OBJ TXT-card reader (`parse_object`)
did:

```c
if (addr + cnt <= sizeof o->text) memcpy(...);
```

— so it **silently dropped every TXT card that would not fit**. No diagnostic, no
return code. The dropped region stayed zeros in `mod`, was emitted into the member,
written to disk, and at run time the first zero halfword past the cut took S0C1.

An OBJ TXT card carries at most **56 bytes** of text, and the guard drops the *whole*
card. So the cut sits at the **last 56-byte TXT-card boundary at or below 16384** — not
at 16384 — which explains the 16352/16376 pair exactly, to the byte:

- run 2 (1 CSECT, cards from 0): 292 × 56 = **16352** (next card would end at 16408)
- run 1 (12288 + csect2): 12288 + 73 × 56 = **16376** (next card would end at 16432)

The ~24-byte "wobble" between the two runs is not noise and not rounding. It is the
layout-dependent position of the last surviving card.

## Wrong turns

This investigation went wrong for a long time, in a way worth preserving — the
2026-07-31 benchmark showed a model reproducing these same turns unprompted.

**"The on-disk image is full, so the bug is in the reader."** This is the one that
cost the most. It was an *inference* from two things that both only report metadata:
AMBLIST LISTLOAD interprets the control records, and the "CCW counts" **are** the
control records. Neither touches the text bytes. **Nobody scanned the member bytes.**
A one-command host-side hexscan of `ld370`'s own `nopt.lm` shows the fill run ending at
16352 followed by zeros — the member `ld370` emits is already truncated.

**Five IEWFETCH hypotheses**, each raised from static reading of `IEWFETCH.ASM` and
each refuted by measurement: track boundary, note list, re-drive, the `FIXLIMTM`
page-fix window, `TXTFIX`. *Reading the loader to infer what the writer should produce
is the approach that kept failing.*

**"Just lower `MAXTEXT` to 16384."** 16384 is not an IEWL text-record size at all — the
table is 18432/13312/12288/…, and IEWL's maximum is **18432 > 16384**. Records that
size load fine in production. The 16 KB figure is a magnet precisely because it looks
like a system limit and is not one.

**The IEWL oracle phase — right method, wrong conclusion.** The exact failing `nopt.o`
was linked with real IEWL, AMBLISTed, run, and its directory dumped. IEWL produced a
**byte-identical member** (control 1 `06000000 40004268`, 17000; control 2, 2056,
MODEND; length 0x4A70) and identical PDS2 attributes (`C2F2`) — and **the IEWL member
ran, COND CODE 0000**. From that, the investigation concluded the member was exonerated
and the bug had to be in **physical placement**: `ld370` writes one block per track,
IEWL packs contiguously. That conclusion was wrong, and it was wrong because the
comparison was of *sizes and attributes*, never of *content*.

**The red herrings:** IDR-82 and the off33 directory diffs. Both FETCH-irrelevant.

**Blaming a bad entry point, a missing relocation, or AMODE/RMODE.** Never in play —
S0C1 on zeros means the text was never written there. Bad relocation leaves real
instructions in place and gives a wild branch or S0C4 instead.

## Fix

`o->text` became a `realloc`-grown pointer tracked by `textcap`, zero-filling gaps and
**erroring on OOM instead of dropping**. Builds clean under `-Wall -Wextra -Werror`.
`[source: ld370.c:285-292; commit de39a60]`

`[tested]` NOPT `--t1 17000 --t2 2056` and `--t1 12288 --t2 12288`, both previously
S0C1, now RECV370-install and **RUN COND CODE 0000**. `ld370/tests/run.sh` fixture
byte-identity to IEWL all green — text below 16 K fills identically, no regression.

## Two neighbours in the same class

The same "fixed array, no bounds check, silent drop" pattern appeared twice more in the
same file. `[source: ld370.c:201-210]`

**`rld[512]` / `ld[64]`.** Fixed arrays with no bounds check, so an object with more
than 512 RLD items overflowed `rld[]` into `ld[]` and **exported LD symbols silently
vanished** — surfacing much later as "unresolved" at a subsequent link. Fixed by
growing both on demand. `[commit 6e4dbef]`

**Oversized RLD *records*** — a different bug with a different symptom. Program fetch
reads each RLD record into a **256-byte buffer** (`IEWFETCH FTRBUF`), so IEWL caps RLD
data at **236 bytes per record** (16-byte header + data must fit). One oversized record
makes fetch read past the buffer and relocate garbage → **S106 reason 0E**. Fixed by
splitting RLD data into ≤236-byte records like IEWL.
`[source: ld370.c:1898-1908, const long RLDMAX = 236; commit 47a6cc7]`

A third, found afterwards: a section larger than MAXTEXT was emitted as one oversized
text record because intra-section splitting was unimplemented, giving `U0200-13 RECV370
.RECVBLK` on a ~60 KB module. Again not a geometry limit. Fixed by splitting at MAXTEXT
boundaries, byte-for-byte the IEWL layout.

## The transferable lesson

**When "the image is complete" is an inference, scan the bytes before theorising about
the reader.** AMBLIST, the control records and the CCW counts are all the linker's own
account of itself. They are perfectly consistent with a linker that declares N bytes
and writes fewer.

And the same lesson as **PM-2026-001**, from the other end of the toolchain: our own
tools produced structurally valid, silently wrong output. Suspect them before suspecting
MVS.
