---
id: CF-2026-003
title: Does BLDL with DCB=0 search the caller's JOBLIB/STEPLIB, or only the link library?
status: tested
platform: [mvs38j]
sources:
  - "MVS-BLDL-0001, section 'What BLDL with DCB=0 actually searches' — no source given"
  - "rexx370/src_ptf/TODO_IKJEFT01.md:270-272 — the same statement, as a design note"
  - "mvs38-ibmsrc/ibm/IGC/IGC018.asm, seq. 00920002-00960002 — prologue, condition 2"
  - "mvs38-ibmsrc/ibm/IGC/IGC018.asm, seq. 08740002-09120002 — NOLNKSVC: TCBJLB, else CVTLINK"
  - "MVS/CE LAB (mvsdev.lan:8082), JOB01201 KBBLDL — 2026-09-25, steps E and F"
verified_on: 2026-09-25
applies_to: [rexx370, mvs38src]
tags: [bldl, svc18, igc018, joblib, steplib, tasklib, linklib, tcbjlb, search-order]
related: [MVS-BLDL-0001]
---

## The two positions

**A.** `MVS-BLDL-0001` says BLDL with DCB=0 searches *"the link library —
not the caller's STEPLIB or JOBLIB"*, and concludes that a module reachable
in test via `//STEPLIB` will not be found in production. The document gives
no source, and none of its jobs (JOB01125/01127/01129/01131) put a module
only in a STEPLIB. The claim comes from a design note in
`rexx370/src_ptf/TODO_IKJEFT01.md`, which gives no source either.

**B.** The SVC 18 routine says the opposite. `IGC018`'s prologue, condition 2:

```
*           2. THE USER HAS NOT SUPPLIED A DCB.  IN THIS CASE
*              EITHER JOBLIB OR STEPLIB, (THEMSELVES PERHAPS
*              CONCATENATED) FOLLOWED BY LINKLIB WILL BE SEARCHED.
```

The code does the same thing at `NOLNKSVC` (the `USING`/`DROP` lines and the
SVCLIB test before it are left out):

```asm
NOLNKSVC LTR   RDCB,RDCB          DID USER SUPPLY DCB ADDRESS
         BP    SETCCWS            YES, NOT LINKLIB/TASKLIB DEFAULT
         MVI   LIB,TASKLIB        START JOBLIB SEARCH
         L     RZ,CVTTCBP         FIND TCB POINTERS
         L     RZ,TCBPTRC         FIND CURRENT TCB
         L     RDCB,TCBJLB        JOBLIB DCB ADDR
         LTR   RDCB,RDCB          IF A JOBLIB DCB EXISTS,
         BP    SETCCWS            GO PROCESS THE LIBRARY
         L     RDCB,CVTLINK       OTHERWISE GET LINKLIB DCB ADDR
```

`[source: IGC018 NOLNKSVC]`

## Why they cannot both be the whole story

B says a module that is only in the STEPLIB *is* found. A says it is not.
Both give the same practical advice for the rexx370 case: at logon there
is no STEPLIB, so `IRXANCHR`/`IRXINIT` have to be in the link list anyway.
A's *reason* is contradicted by the source, though, and the
generalisation to "not found in production" is not supported by it.

A second, smaller point: `MVS-BLDL-0001` says an RC=4 on `IEFBR14` means
the list is wrong. That holds under either position, because LINKLIB is
searched in both cases.

## What would settle it

One batch job: a scratch PDS with a member that is in no link-list library,
named in `//STEPLIB`, plus a `BLDL 0,list` for that member together with the
`IEFBR14` control. B predicts RC=0. A predicts RC=4, with the `IEFBR14`
entry filled in.

## Resolution — position B

Settled by experiment on MVS/CE LAB, JOB01201, 2026-09-25. **DCB=0 searches
the task's STEPLIB before the link library.**

- Step E, `BLDL 0,LIST2`: `KBBLDLT1`, which exists only in the step's
  `//STEPLIB` (`&&LOAD`), was found with Z=`02` (JOBLIB/STEPLIB, `IGC018`
  `LIB`). RC=0.
- Step F, `BLDL (2),LIST2` with R2 = `CVTLINK`: the same name was not found
  (R=`00`), and `IEFBR14` was, with Z=`01`. The name is not in the link list,
  so step E found it through STEPLIB and nowhere else.

```
+KBBLDLT1 A RC=00000004 1=01261600012C012704000000 2=FFFF00FFFFFFFFFFFFFFFFFF
+KBBLDLT1 C RC=00000004 1=01261600012C012704000000 2=FFFF00FFFFFFFFFFFFFFFFFF
+KBBLDLT1 D RC=00000004 1=01261600012C012704000000 2=FFFF00FFFFFFFFFFFFFFFFFF
+KBBLDLT1 E RC=00000000 1=01261600012C012704000000 2=00000400022C000009000000
+KBBLDLT1 F RC=00000004 1=01261600012C012704000000 2=FFFF00FFFFFFFFFFFFFFFFFF
+KBBLDLT1 B RC=00000004 1=FFFFFFFFFFFFFFFFFFFFFFFF 2=FFFFFFFFFFFFFFFFFFFFFFFF
```

Each line is the BLDL return code and 12 bytes of each entry from the TTR on
(TT R K Z C …). Entries were prefilled with `X'FF'`. `LIST1` = `IEFBR14`,
`IKJEFT01`; `LIST2` = `IEFBR14`, `KBBLDLT1`, `LL=58`. `KBBLDLT1` is the probe
itself, linked into `&&LOAD` and run from `//STEPLIB DD DSN=&&LOAD`.

The job's step condition codes (0411, 0011, 0400) encoded "entry found" as
"TTR no longer `FFFFFF`". That test is wrong — SVC 18 zeroes R in every
entry — so the codes are not evidence. The hex above is.

## Status

Closed 2026-09-25 by JOB01201. Outcome B; `MVS-BLDL-0001` corrected. The
same claim is still in `rexx370/src_ptf/TODO_IKJEFT01.md` (Offen, item 3)
and in the comment on `IKJEFTRX.ASM:82`. Their conclusion (put the modules
in the link list) still holds, but the reason they give does not.
