---
id: MVS-PROT-0001
title: MVCK's key operand is a fetch check, not the protection it is taken for — TPROT is the store check
status: inferred
platform: [mvs38j]
sources:
  - "oftpd asm/oftpsvc.asm — the caller-range validation of the private SVC, and the review that raised this (oftpd#1, PRs #5/#6, 2026-10-17)"
  - "as370 1.6.3 — TPROT assembles as SSE: `TPROT 4(5),8(9)` -> `E501 5004 9008` (host measurement)"
  - "Hercules (hyperion) control.c, the E501 `test_protection` handler — `PRIV_CHECK(regs)`, the key taken from `effective_addr2 & 0xF0`, and the CC order fetch-protected -> 2 / store-protected -> 1 / else 0 / translation exception -> 3 (read 2026-10-18)"
  - "Hercules (hyperion) feat370.h:30 FEATURE_2K_STORAGE_KEYS, feature.h:397-407 STORAGE_KEY_PAGESIZE 2048 vs 4096 — the key granularity the emulator builds for S/370 mode (read 2026-10-18)"
  - "oftpd TSTPROT in a throwaway MVS/CE container, 2026-10-18 (oftpd#15, internals/xmem.md section 12): TPROT run authorized against subpool 241, a __loadhi module area and a key-8 heap control"
  - "IBM Principles of Operation — the architecture statements below come from the reviewing session's reading of it; the manual is NOT held locally and is not catalogued in sources/, so nothing here is cited to a page"
# Still `inferred`, deliberately: the headline claim about MVCK is an
# architecture statement nobody here has measured. What IS measured --
# the fetch-protection state of subpool 241 -- is its premise, and the
# body marks every part with its own status.
verified_on: 2026-10-18
verified_platforms: ["MVS/CE"]
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

The condition-code order is the emulator's own: it answers **2** when the
location is fetch-protected against the given key, **1** when it is store-
protected, **0** otherwise, and **3** on a translation exception.
`[source: hyperion control.c, test_protection]`

The test to require is **CC 0 under the caller's key**: the range must be
storable by the caller. `[inferred]`

## TPROT is privileged, and that decides who may ask

`TPROT` is a **privileged instruction** — Hercules checks it with
`PRIV_CHECK(regs)` immediately after the operand decode in its `E501`
handler. `[source: hyperion control.c, test_protection]` A problem-state
program issuing it gets S0C2.

The key it tests is **not** the PSW key: it comes from bits 24-27 of the
second operand's *address* (`effective_addr2 & 0xF0` in the handler), and
nothing is fetched from that address. So an authorized routine asks "would a
key-8 access be permitted here" without being in key 8 — which is exactly
what a service validating a caller's buffer needs.

**The consequence is a design rule, not a detail.** An unauthorized caller
can never check its own access, because the only non-faulting way to ask is
closed to it. So every such check has to be made by the service, on the
caller's behalf, inside the authorized routine. A design that expected the
client to validate its own pointers before calling has no instrument to do it
with.

It also means a measurement of this question needs an APF-authorized job.
A probe that is written unauthorized measures nothing and abends.

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

## Measured: CSA is readable from key 8 and not writable

Run 2026-10-18 on MVS/CE in a throwaway container (oftpd `TSTPROT`,
oftpd#15). `TPROT` issued from an authorized program, asking about **key 8**:

| Storage | CC |
|---|---|
| ordinary key-8 heap — the control | **0** store and fetch |
| `getmain(9536, 241)` | **1** fetch only |
| a module area from `__loadhi()` | **1** fetch only |

`[tested: MVS/CE, 2026-10-18]` The control is what makes the other two
readable: a control that does not answer CC 0 invalidates the run.

So for key-0 CSA from subpool 241: **a key-8 fetch is permitted and a key-8
store is not.** That is the fetch-protection state this document had to leave
open, and it is the state the opening claim depends on — an unauthorized
caller really can read key-0 CSA, so `MVCK` under the caller's key really
does not keep a forged pointer out of it.

Two consequences for anyone designing with CSA. A service may let an
unauthorized client read a published anchor directly, which is how discovery
through the SSCT works at all. And nothing an unauthorized caller does can
corrupt that anchor, so the integrity of a control block in subpool 241 does
not rest on hiding its address.

## The granularity is still open, and a passive scan cannot close it

A scan of ±32 K around the block in 2048-byte steps, aligned to the step,
found key transitions at `00A8D000`, `00A90000` and `00A93000` — all three
4 K aligned, none at an odd 2 K. **That settles nothing.** MVS hands out
storage in pages, so it never creates a boundary at an odd 2 K even on
hardware whose keys are 2 K: the absence is what *both* candidates produce.
A positive would have been decisive; an absence is not evidence here.
`[tested: MVS/CE, 2026-10-18]`

Settling it needs an active probe — `SSK` on one half of a page and `ISK` on
the other — which no design in the ecosystem currently needs, because the
≤ 2048-byte rule above is sound under either value.

**The first run of that scan reported "no 2K-only boundary" as a finding, and
it was an artefact.** The grid started at an arbitrary `getmain()` address, so
every probe sat at that address modulo 2048 and the test for a boundary at an
odd 2 K could not be true for any input whatsoever — while the assertion above
it passed. Worth repeating here because it is the shape the root `CLAUDE.md`
warns about and it survived into a measurement: the number was real and the
sentence beside it was not.

## What this document still does not have

**No page citation.** The Principles of Operation is not held locally and is
not in `sources/` — the architecture statements above are second-hand, which
is why this document is not `manual`. Treat the condition-code table as a
working contract, not as a quotation.

**MVS/CE only.** TK5 is unverified for the CSA readings above, and nothing
here was run on real hardware.

**`MVCK` itself is still unmeasured.** The fetch-protection reasoning is now
measured, so the premise of the opening claim holds — but nobody has run an
`MVCK` across keys and watched it succeed. The claim stands on the measured
premise plus the architecture statement, not on an observation of the
instruction.

## Why it was nearly missed

The review that produced this was reading an SVC routine that *does* move
caller data under the caller's key, and the move looked like the protection.
It is not: it is the correct instruction for the copy and the wrong
instrument for the decision. The two are easy to conflate because both
mention the caller's key, and because the failure mode is silent — a forged
pointer is read successfully and the service answers with data the caller
could not otherwise see.
