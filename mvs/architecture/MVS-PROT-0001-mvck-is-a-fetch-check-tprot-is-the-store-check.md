---
id: MVS-PROT-0001
title: MVCK's key operand is a fetch check, not the protection it is taken for — TPROT is the store check
status: inferred
platform: [mvs38j]
sources:
  - "oftpd asm/oftpsvc.asm — the caller-range validation of the private SVC, and the review that raised this (oftpd#1, PRs #5/#6, 2026-10-17)"
  - "as370 1.6.3 — TPROT assembles as SSE: `TPROT 4(5),8(9)` -> `E501 5004 9008` (host measurement)"
  - "Hercules (hyperion) feat370.h:30 FEATURE_2K_STORAGE_KEYS, feature.h:397-407 STORAGE_KEY_PAGESIZE 2048 vs 4096 — the key granularity the emulator builds for S/370 mode (read 2026-10-18)"
  - "IBM Principles of Operation — the architecture statements below come from the reviewing session's reading of it; the manual is NOT held locally and is not catalogued in sources/, so nothing here is cited to a page"
applies_to: [oftpd, nsf370, ufsd, libc370]
tags: [storage-key, key-granularity, protection, mvck, mvcp, mvcs, tprot, fetch-protection, svc, cross-address-space, key0, csa]
related: [ECO-0004]
---

## The claim worth remembering

**Moving data "under the caller's key" does not keep a forged pointer out of
key-0 storage.** `MVCK`'s third operand supplies the key used to *fetch* the
second operand. A fetch with key 8 from storage with a different storage key
succeeds whenever that storage's **fetch-protection bit is off** — which is
the ordinary state of key-0 CSA. `[inferred]`

So a routine that validates a caller's buffer by moving it with `MVCK` has
validated nothing about whether the caller was entitled to that storage. Only
a **store** check distinguishes the caller's own storage from everybody
else's. `[inferred]`

This matters wherever an unauthorized caller hands an address to code running
in key 0 — a private SVC, an SSI router, any cross-address-space service. The
routine runs with the authority to read anything; the caller's pointer must
therefore be proven to lie in storage the *caller* could have written.

## TPROT gives the store check without faulting

`TPROT` reports accessibility in the condition code instead of raising a
program interruption, so it can be used to refuse a request rather than to
survive one:

| CC | Meaning |
|---|---|
| 0 | store permitted (and therefore fetch) |
| 1 | fetch permitted, store not |
| 2 | no access |
| 3 | storage not available |

`[inferred]`

The test to require is **CC 0 under the caller's key**: the range must be
storable by the caller. `[inferred]`

It assembles under as370 1.6.3 as an SSE instruction:
`TPROT 4(5),8(9)` → `E501 5004 9008`. `[tested: as370 1.6.3, host]`

## Two probes cover a range of 2048 bytes or less — and only that far

Testing the first and the last byte of a range covers every protection block
it touches **only while the range cannot span three blocks**. That bound is
the storage-key granularity, and the granularity is exactly what is not
established here:

- S/370 associates a key with each **2 K** block.
- 370-XA and later use **4 K**.

**The emulator we run on builds the 2 K case.** Hercules defines
`FEATURE_2K_STORAGE_KEYS` for S/370 mode `[source: hyperion/feat370.h:30]`,
and under it `STORAGE_KEY_PAGESIZE 2048` / `STORAGE_KEY_BYTEMASK 0x000007FF`
— against 4096 / 0x00000FFF in the `#else`
`[source: hyperion/feature.h:397-407]`. That is a reading of the emulator's
source, not a measurement on MVS and not the architecture: it says what the
machine our systems actually run on does.

So 2 K is the value to design against, and under it a range of 2049 to 4096
bytes spans three blocks with **the middle one unchecked by a two-ended
probe**.
That is precisely the silent failure this document exists to prevent, so the
rule to follow is the one that is safe under either value:

> **≤ 2048 bytes: two probes are enough. Above that: walk, one probe per
> 2 K.**

oftpd's `OFTP_SVC_REPMAX` is 2048 for other reasons and therefore stays
inside the safe bound whichever granularity holds. A design that wants
larger caller ranges has to settle the granularity first — `TPROT` at offset
+2048 across a known boundary answers it, and that probe belongs with
oftpd#15.

oftpd's private SVC uses exactly this: `TPROT` on both ends of every caller
range before the request claims a slot, so a forged pointer is refused with a
return code instead of faulting in key 0 (oftpd `internals/xmem.md`).

## What this document does not have

**No page citation.** The Principles of Operation is not held locally and is
not in `sources/` — the architecture statements above are second-hand, which
is why this document is `inferred` and not `manual`. Treat the condition-code
table as a working contract, not as a quotation.

**No measurement either.** Nothing here has been run on a machine except the
assembly of the instruction. The cheap experiment that would settle both the
`TPROT` codes and the fetch-protection question in one go is **oftpd#15**: a
key-8 program probing (1) storage from `getmain(size, 241)`, (2) a module
loaded there by `__loadhi()`, (3) ordinary key-8 heap as the control. A
control that does not answer CC 0 invalidates the run, and a probe at +2048
across a block boundary settles the key granularity in the same job. When
that runs, this document becomes `tested`, and the fetch-protection state of
subpool 241 and the 2 K/4 K question get recorded here.

## Why it was nearly missed

The review that produced this was reading an SVC routine that *does* move
caller data under the caller's key, and the move looked like the protection.
It is not: it is the correct instruction for the copy and the wrong
instrument for the decision. The two are easy to conflate because both
mention the caller's key, and because the failure mode is silent — a forged
pointer is read successfully and the service answers with data the caller
could not otherwise see.
