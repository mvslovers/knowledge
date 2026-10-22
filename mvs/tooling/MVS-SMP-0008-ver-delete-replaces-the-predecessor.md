---
id: MVS-SMP-0008
title: ++VER DELETE(old) makes a new FUNCTION replace its predecessor — SMP deletes the old LMODs, ownership transfers, the APPLY ends RC 04 and each zone needs its own pass
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE system, SMP 4 HMASMP LVL 04.48, 2026-09-14 — predecessor installed JOB00296; successor with DELETE JOB00297 (HMA2240 x4 then HMA2380 x4); MOD ownership read JOB00298; the same install with the strict ACCEPT gate JOB00293 (ACCEPT skipped); fresh install carrying the same DELETE JOB00309 (output in mvslovers/mbt#98, mvslovers/ftpd#143)"
  - "ufsd docs/books/ex/ug-install/apply-upgrade.txt and apply-new.txt at commit 6804ee7 — APPLY output of an upgrade (RC 04) and of a fresh install (RC 00), UFSD 1.5.0 deleting 1.4.0"
  - "mbt scripts/mbt/distribution.py, function accept_cond and the ++VER assembly, origin/main b6f43e7"
  - "ufsd docs/installation.md section 10 at commit 6804ee7 — 'There is no UCLIN step any more'"
verified_on: 2026-09-14
verified_platforms: ["MVS/CE (3.0.0)"]
applies_to: [ufsd, ftpd, httpd, mvsmf, mbt]
tags: [smp, smp4, delete, ver, hma2240, hma2461, hma2380, accept, cond, upgrade, element-ownership, mbt]
related: [ECO-0007, MVS-SMP-0006, MVS-SMP-0007, MVS-SMP-0009, MVS-SMP-0010, MVS-SMP-0011, MVS-SMP-0014]
---

## The claim

A function SYSMOD that carries `++VER(Z038) DELETE(<old>)` replaces the function
`<old>`. This is what lets a release install over its predecessor without a
UCLIN step. `[tested]`

```
++FUNCTION(<new>) .
++VER(Z038) DELETE(<old>) .
```

## What SMP does

1. **APPLY deletes the predecessor's load modules from the target library, then
   copies the new ones in.**
   ```
   HMA2240    SUCCESSFULLY DELETED LMOD UFSD ON LINKLIB LIBRARY
   HMA2380    COPY SUCCESSFUL - MOD=UFSD - LMOD=UFSD - LIBRARY=LINKLIB - SYSMOD=TUFS150 - RETURN CODE=00
   ```
   (JOB00297: four `HMA2240`, then four `HMA2380 … SYSMOD=<new>`.)
2. **Element ownership transfers.** `MOD(x)` afterwards carries the new `FMID`
   and `RMID` (JOB00298). This is what defeats the ownership wall
   (`MVS-SMP-0006`): without the DELETE, the new function would print `NOT SEL`.
3. **Each zone is deleted by its own pass.** APPLY removes the old id from the
   CDS, ACCEPT removes it from the ACDS. If the ACCEPT is skipped, the old id
   survives as `REC APP ACC RGN` in the ACDS (JOB00293, ACCEPT skipped, against
   JOB00297, ACCEPT run).
4. **On an upgrade the APPLY ends RC 04, after reporting success.** A deleted id
   has no SMPSCDS backup entry:
   ```
   HMA2270    APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TUFS150
   HMA2461    SYSMOD TUFS140 NOT FOUND ON SMPSCDS LIBRARY
   HMA2050    APPLY PROCESSING COMPLETED - HIGHEST RETURN CODE IS 04
   ```
   That RC 04 is the expected result and must not stop the job.
5. **On a fresh install carrying the same DELETE the APPLY ends RC 00** and
   prints no `HMA2461`: nothing was deleted, so no backup entry is missed
   (JOB00309; UFSD 1.5.0 fresh install in `apply-new.txt`). A RC 00 on a system
   that held the predecessor is therefore not a sign that the DELETE worked, and
   RC 04 is not a sign that it failed — read the `HMA2240` / `HMA2380` pairs.

## The ACCEPT gate

A job that gates the ACCEPT on `COND=(0,NE,APPLY.HMASMP)` skips it *without a
word* after the RC 04 of point 4, leaving the old id alive in the ACDS (point 3).
mbt relaxes the gate to `COND=(4,LT,APPLY.HMASMP)` whenever `delete` is set and
keeps the strict `(0,NE,…)` otherwise. `[source: mbt accept_cond, b6f43e7]` An
APPLY that ends RC 8 or higher still stops the job. The relaxed gate is
load-bearing on an upgrade and harmless on a first install.

## What it replaces

An upgrade of consecutive releases needs **no UCLIN step**: the predecessor's
module entries move to the new id by themselves. `[source: ufsd
docs/installation.md §10, 6804ee7; mvslovers/mbt#98]` `ECO-0007` named UCLIN
as the way to cut a minor bump before this existed; see its correction note.

Two things the DELETE does **not** do:

- It deletes only the id it names. A release that deletes only its immediate
  predecessor leaves an older owner of the module in place, and then SMP installs
  nothing (`MVS-SMP-0006`).
- It does not remove the predecessor's data set, and it can fail on a renamed
  library (`MVS-SMP-0010`). It does not free the id: the predecessor stays as a
  tombstone (`MVS-SMP-0009`).

## Not covered

- A DELETE of an id whose modules are link-edited into shared LMODs. The
  measurements used LMODs whose names equal their module names.
