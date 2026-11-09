---
id: MVS-SMP-0017
title: The REJECT indicator of the PTS SYSTEM entry decides whether RESTORE removes the SYSMOD from SMPPTS for good — UCLIN PTS DEL SYS REJECT switches it off
status: tested
platform: [mvs38j]
sources:
  - "Reproduced 2026-11-09 on two fresh throwaway TK5 containers (ghcr.io/mvslovers/tk5@sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf593d5258dd612325c29c14c6), SMP4 HMASMP LVL 04.48, one per column of the table; the only difference between them is the UCLIN. SYSMODs ZP60014 and ZP60038, which the image ships applied and not accepted"
  - "First measured 2026-11-05/06 (usermod ZMG0003 removal, mvslovers/usermods, zmg0003/), as reported in the inbox note; the manual passages below are quoted from that note and were not checked against GC28-0673-6"
verified_on: 2026-11-09
verified_platforms: ["TK5 Update 5 throwaway container"]
applies_to: [rexx370]
tags: [smp, smp4, restore, reject, purge, uclin, pts, smppts, system-entry, hma4012, hma2391, usermod]
related: [MVS-SMP-0005, MVS-SMP-0013]
---

## The claims

1. **The PTS SYSTEM entry carries a `REJECT` indicator that can be switched off
   with UCLIN.** `[tested]`

   ```
   UCLIN PTS .
   DEL SYS REJECT .
   ENDUCL .
   ```

   RC 0. `LIST PTS .` before, after `DEL SYS REJECT .`, and after `ADD SYS REJECT .`
   (a second UCLIN of the same shape):

   ```
   SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=YES
   SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=NO
   SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=YES
   ```

   This is the syntax that `MVS-SMP-0013` could not find with `REP` (seven failed
   variants, HMA2032): `DEL` and `ADD` of the option on `SYS`, not `REP`.

2. **With `REJECT=YES` (as distributed), `RESTORE` of an applied SYSMOD also deletes
   it from the SMPPTS. A later `APPLY` then cannot find it.** `[tested]`
3. **With `REJECT=NO`, `RESTORE` leaves the SYSMOD received (`STATUS = REC`) and
   `APPLY` works again.** `[tested]`

| | `REJECT=YES` (as distributed) | `REJECT=NO` |
|---|---|---|
| `RESTORE SELECT(ZP60014,ZP60038)` | RC 4 | RC 4 |
| `LIST PTS SYSMOD(...)` afterwards | both "not found" | both there, `STATUS = REC` |
| `APPLY SELECT(ZP60014,ZP60038) DIS(WRITE)` | RC 12 | RC 0 |

Both runs: before the RESTORE `STATUS = REC  APP`. The `REJECT=YES` APPLY:

```
HMA4012 ** SYSMOD ZP60014 SELECTED FOR APPLY NOT FOUND ON SMPPTS LIBRARY
HMA4012 ** SYSMOD ZP60038 SELECTED FOR APPLY NOT FOUND ON SMPPTS LIBRARY
```

**The indicator has to be off before the RESTORE**, not after: afterwards the MCS is
gone. How to get it back (RECEIVE from the original job stream) was not measured.

The RC 4 of the RESTORE is the same under both settings: the job shows
`HMA2391 LINK SUCCESSFUL - MOD=IKJCT433 - LMOD=IKJPTGT - LIBRARY=LPALIB ... RETURN
CODE=04` (and the same for `IKJEFT56`). That the link-edit RC is the cause of the
RC 4 is a reading, not shown. `[inferred]`

## Where this fits

- It is the first part of an answer to the open point of `MVS-SMP-0013`: that
  document asks for the way to change PTS SYSTEM options. The **syntax** is now
  established, for `REJECT`. `PURGE` was **not** measured here; whether
  `DEL SYS PURGE` gives `REJECT` after an ACCEPT a chance remains open.
  `[assumed]` that it works the same way.
- It explains one half of `MVS-SMP-0005`: the later `REJECT` fails with `HMA2462`
  because RESTORE took the MCS away. That is the `REJECT=YES` behaviour above;
  under `REJECT=NO` the MCS stays, so a later `REJECT` has something to work on.
  Not run here.
- The indicator is a property of the whole system, not of a SYSMOD. A site that
  switches it off changes what RESTORE means for every SYSMOD it restores.

## From the inbox note, not reproduced here

The note reports the following; it is not claimed as tested. `[assumed]`

- The manual (OS/VS SMP System Programmer's Guide, GC28-0673-6) says the REJECT
  indicator is set when the SYSTEM entry is created, that resetting needs
  `DEL SYS REJECT.`, and that a successfully restored SYSMOD is also rejected from
  the PTS when the indicator is on.
- Full cycle under `REJECT=NO` for a usermod with a full `++MOD(IKJCT441)`, ending
  in a library line-identical to the one before the install.
- On a fresh MVS/CE, RESTORE of a usermod chain whose requisites are applied but
  not accepted ended RC 12 with `HMA3022`, reason `MISSING/NOGO REQUISITES`, and
  restored nothing; on TK5 the same kind of RESTORE did not stop (as in the table
  above). The note reads this as: RESTORE wants every unaccepted requisite in the
  select list.

## Limits

- One run per column, TK5 only. MVS/CE not run for this document.
- Job streams ran in separate jobs; `DEL SYS REJECT` and `RESTORE` in one job was
  not run.
- The RESTORE needed `HMASMP.LPALIB`, `CMDLIB`, `AOST4` and `AGENLIB` DDs; without
  them it ended RC 12 with `HMA2832` (DDCARD missing).
