---
id: MVS-SMP-0001
title: APPLY checks requisites against the CDS, ACCEPT against the ACDS — a PTF applied but never accepted blocks every later ACCEPT
status: tested
platform: [mvs38j]
sources:
  - "MVSCE-LAB (MVS/CE 3.0.0 under Hercules), SMP 4 level 04.48, 2026-09-23 — APPLY CHECK job IBCK1313/JOB01079 RC 0000, ACCEPT CHECK job IBACC001 RC 0012, ACCEPT job IBAC6910/JOB01093 RC 0004"
  - "SMPOUT of IBACC001: HMA3022 / HMA3590 --- UZ82014 PRE / status NOGO"
verified_on: 2026-09-23
verified_platforms: ["MVS/CE 3.0.0 (mvsdev)"]
applies_to: [mvs38src, ufsd, httpd, ftpd, mbt]
tags: [smp, smp4, apply, accept, requisite, pre, req, cds, acds, sysmod, nogo, hma3022, hma3590]
related: [ECO-0007, MVS-SMP-0002, MVS-SMP-0003]
---

## The claim

**`APPLY` resolves `PRE()`/`REQ()` against the target zone (`SMPCDS`).
`ACCEPT` resolves them against the distribution zone (`SMPACDS`).** `[tested]`

This answers the open question in `ECO-0007`: it is neither "both" nor "the
CDS". Each function checks the zone it writes.

## The evidence

`UY13431` has `PRE(UZ82014)`. On MVS/CE, `UZ82014` was `APPLIED` in the CDS and
had no ACDS entry at all.

**APPLY accepted it** — `APPLY SELECT(UY13431) CHECK .`, RC 0000:

```
SYSMOD   STATUS    TYPE      FMID     REQUISITE AND SUPEDBY SYSMODS
UY13431  APPLIED   PTF       EBB1102  PRE     UZ82014
```

No `-` marker: the requisite is satisfied.

**ACCEPT refused it** — `ACCEPT SELECT(UY13431) CHECK .`, RC 0012, same system,
same minute, same SYSMOD:

```
HMA3022 ** ACCEPT PROCESSING TERMINATED FOR SYSMOD UY13431 - REASON = MISSING/NOGO REQUISITES:
HMA3590     --- UZ82014 PRE
UY13431  NOGO      PTF       EBB1102  PRE    -UZ82014
```

The only variable between the two runs is the function.

## Why this matters more than it looks

A SYSMOD that is applied but never accepted is invisible to `APPLY` planning and
fatal to `ACCEPT` planning. **On MVS/CE, 111 SYSMODs are in that state.**
`[tested]` Every one of them blocks the ACCEPT of anything that names it as a
requisite, transitively.

Measured consequence: accepting one PTF required accepting **six**.

```
UZ47575 → UZ47871 → UZ44177 ┐
                  UZ48384 ┤→ UZ82014 → UY13431
```

and moved **19 elements** — 16 modules in `AOST4`/`ACMDLIB`, two macros in
`ATSOMAC` (`IKJECT`, `IKJTMPWA`), one target-zone module. The DLIB's accepted
SYSMOD count went 103 → 109.

## How to compute the closure

**`ACCEPT SELECT(…) CHECK .` is the requisite solver.** Give it the set you
believe you need; it reports `NOGO` with the missing ids. Add them, repeat until
RC 0000. `[tested]` The element summary of the CHECK run also lists exactly
which elements will move, before anything moves.

Read the whole element report, not only the `MOD` lines. The two macros above
were in the CHECK output and were missed by filtering on `MOD`.

## Practical rules

- **Do not size an upgrade by counting SYSMODs.** The count of "SYSMODs that
  differ" is a lower bound. The work set is the transitive `PRE`/`REQ` closure
  over everything not yet accepted.
- `ACCEPT` is one-way. `RESTORE` refuses an accepted SYSMOD (`ECO-0007`), and
  there is no older level to return to unless one was accepted earlier.
- A re-`APPLY` of an already applied SYSMOD is **not refused**. SMP 4 re-links
  the module and returns RC 0000. `[tested]` Idempotent in effect, but it does
  work rather than declining it.

## Open

- Whether `SUP()` is resolved per zone the same way. Not measured.
