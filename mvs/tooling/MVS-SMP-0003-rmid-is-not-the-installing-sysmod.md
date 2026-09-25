---
id: MVS-SMP-0003
title: RMID is not the SYSMOD that installed the element, and RMID numbers are not ordered
status: myth
platform: [mvs38j]
sources:
  - "MVSTK5-BLD (TK5 Update 5) SMPACDS, 2026-09-22 — 2.047 distinct RMIDs, 696 with an installed status, 1.351 SUPERSEDED-only, 1.349 of those superseded by an FMID"
  - "TK3 build listings, MVS_Turnkey_Volker_V3.zip prt/*.lst (Volker Bandke, April 2001) — 7.245 HMA2380/HMA4090 copy lines, every one naming an FMID; 48 successful ACCEPTs of which 17 are PTFs"
  - "MVSCE-LAB, 2026-09-23 — ACCEPT of UZ47575 left IKJEGSYM at RMID UZ47575, replacing UZ52521"
  - "MVSHIST docs/03-tk3-vermessen.md, docs/03-zielzone-dlib.md"
verified_on: 2026-09-23
verified_platforms: ["TK5 Update 5", "MVS/CE 3.0.0 (mvsdev)", "TK3 (build listings only)"]
applies_to: [mvs38src, mvsmf]
tags: [smp, smp4, rmid, fmid, sysmod, hma2380, hma4090, supersede, relfile, myth, model-priors, comparison]
related: [ECO-0007, MVS-SMP-0001, MVS-SMP-0002, MVS-SMP-0004]
---

## The myth

> *"An element's `RMID` tells you which SYSMOD put it there, so comparing two
> systems' RMIDs tells you which elements differ."*

**Both halves are false, and the error is large.** Applied to a TK3 ↔ TK5
comparison it produced **2.133 false differences out of 3.068** — 70 %.
`[tested]`

## Half one: the copy message does not report the RMID

SMP logs each element it copies:

```
HMA2380  COPY SUCCESSFUL - MOD=IFCCRNDR - LMOD=IFCCRNDR - LIBRARY=AOSCD - SYSMOD=EER1400
HMA4090  COPY SUCCESSFUL - MAC=SGIFB400 - LIBRARY=AGENLIB - SYSMOD=EER1400
```

`SYSMOD=` is **the SYSMOD whose processing performed the copy**. During a SYSGEN
that is always the FMID. It is a different field from the zone's `RMID`.

Measured: across all 7.245 copy lines in TK3's sysgen listings, **every single
one names an FMID** — and only 31 distinct ones, although 48 SYSMODs were
accepted, 17 of them PTFs. The 17 leave no copy line at all. `[tested]`

## Half two: an RMID need never have been installed

Of 2.047 distinct RMIDs in TK5's distribution zone, only **696** carry an
installed status. The other **1.351 are `SUPERSEDED` and nothing else** — never
received, never applied, never accepted on that system. `[tested]`

**1.349 of those 1.351 are superseded by an FMID:**

```
UZ25504   TYPE     = SUPERSEDED
          LASTSUP  = EBB1102
```

`EBB1102` is the base function. The PTF was **integrated into the function's
RELFILE** and never distributed separately. Anyone who installs that RELFILE has
the fix, and the zone records the finer id — so the element carries an RMID for
a PTF the system never processed.

## Why the comparison breaks

A build log says `SYSMOD=EBB1102`. The other system's zone says `RMID=UZ48441`.
They look different. If `UZ48441 SUP EBB1102`, they are the **same RELFILE and
the same bytes**, wearing two labels.

The correct test is not equality of identifiers:

```
same  :=  RMID_a = RMID_b                      -- or --
          LASTSUP(RMID_b) = SYSMOD_a           -- label artifact
```

After applying it, TK3 ↔ TK5 went from "2.666 of 5.304 modules differ" to
**839**, and the count of distribution levels actually needed from 1.993 to 650.

## Half three: RMIDs are not ordered

**A later ACCEPT can leave a numerically lower RMID.** `[tested]` Measured on
MVS/CE, 2026-09-23:

```
IKJEGSYM   UZ52521 → UZ47575
IGC0006A   UZ78104 → UZ47871
```

The new value is simply the SYSMOD that last replaced the element. A higher
number standing there before means some other PTF touched it more recently, not
that the level was newer in any content sense. **Ordering by PTF number is
meaningless; the zone records identity, not sequence.**

## Rules

- Never conclude "different level" from differing identifiers without resolving
  supersession first.
- Never conclude "newer" from a higher number.
- `HMA2380`/`HMA4090` `SYSMOD=` answers *who copied it*, not *what level it is*.
- A zone entry is a list of questions, never a list of findings.
