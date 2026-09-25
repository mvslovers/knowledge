---
id: MVS-SMP-0002
title: A received SYSMOD is unknown to LIST CDS — SMP 4 keeps the receive state in SMPPTS, not in the zone
status: tested
platform: [mvs38j]
sources:
  - "MVSCE-LAB (MVS/CE 3.0.0 under Hercules), SMP 4 level 04.48, 2026-09-23 — LIST job IBLST1/JOB01077 RC 0004, RECEIVE job IBRC1256/JOB01078 RC 0008"
  - "SMPOUT of IBRC1256: HMA3862 ** SYSMOD UY13431 ALREADY RECEIVED"
  - "LIST ACDS SYSMOD(UY13431) after APPLY and ACCEPT, job IBVFY002 — STATUS = REC APP ACC RGN with all three timestamps"
verified_on: 2026-09-23
verified_platforms: ["MVS/CE 3.0.0 (mvsdev)"]
applies_to: [mvs38src, ufsd, httpd, ftpd, mbt]
tags: [smp, smp4, receive, smpptfin, smppts, cds, acds, sysmod, hma3862, hma3920, list]
related: [ECO-0007, MVS-SMP-0001, MVS-SMP-0003, MVS-SMP-0004]
---

## The trap

**`LIST CDS SYSMOD(x)` returning "NOT FOUND" does not mean `x` was never
received.** `[tested]`

`ECO-0007` records that RC 04 with an empty list means "the id is unknown to
that zone". True — but *unknown to the zone* and *not received* are different
states, and the difference is invisible from the CDS.

## The evidence

`UY13431` on MVS/CE, 2026-09-23. `LIST CDS SYSMOD(UY13431) .` — RC 0004:

```
THE FOLLOWING SELECTED ENTRIES WERE NOT FOUND OR WERE NOT ELIGIBLE FOR PROCESSING
 TYPE        NAME
 SYSMOD      UY13431
```

The member was nevertheless in `SYS1.SMPPTS` — 162 records, complete MCS with
`++PTF`, `++VER`, `++IF`, `++MOD` and the `TXT` cards. A `RECEIVE` of it said
so:

```
HMA3862 ** SYSMOD UY13431 ALREADY RECEIVED
HMA3902 ** SYSMOD UY13431 SELECTED BUT COULD NOT BE RECEIVED
HMA3920    SYSMOD UY13431 NOT RECEIVED
```

After `APPLY` and `ACCEPT`, the zone entry finally appeared — and carried the
receive timestamp all along:

```
UY13431   TYPE            = PTF
          STATUS          = REC  APP  ACC  RGN
          DATE/TIME REC   = 26.213  21:50:43
                    APP   = 26.266  16:09:03
                    ACC   = 26.266  17:08:52
```

**The receive happened seven weeks before the zone knew anything about it.**

## The model

| state | where it lives | how to probe it |
|---|---|---|
| received | member present in `SYS1.SMPPTS` | list the PDS directory, or attempt a `RECEIVE` |
| applied | `SMPCDS` entry | `LIST CDS SYSMOD(x) .` |
| accepted | `SMPACDS` entry | `LIST ACDS SYSMOD(x) .` |

A SYSMOD creates its zone entry at `APPLY`, not at `RECEIVE`. Until then the
zone has nothing to say about it, and `REC` in a later `STATUS` line is
back-filled from the PTS, not evidence that the zone tracked it.

## Consequences

- **An inventory built only from `LIST CDS`/`LIST ACDS` misses everything
  received and not installed.** For a received-PTF inventory, list the `SMPPTS`
  directory — member names are the documented exception to hashed CDS names
  (`ECO-0007`).
- **`RECEIVE` is a usable existence probe**: `HMA3862` is a definite yes, and it
  changes nothing. It does write to the CDS when it *does* receive, so it is not
  free of side effects on a miss.
- **A member in `SMPPTS` is a valid `SMPPTFIN` stream.** Feeding
  `//HMASMP.SMPPTFIN DD DSN=SYS1.SMPPTS(x),DISP=SHR` re-receives from the PTS
  itself; SMP parsed it and reached `HMA3862`, so the format is accepted.
  `[tested]`
- After an `ACCEPT` the PTS member is deleted (`ECO-0007`), so absence from the
  PTS proves nothing either. The three states have three different probes and no
  single one answers for all.
