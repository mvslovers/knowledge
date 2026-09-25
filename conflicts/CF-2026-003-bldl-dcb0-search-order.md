---
id: CF-2026-003
title: Does BLDL with DCB=0 search the caller's JOBLIB/STEPLIB, or only the link library?
status: disputed
platform: [mvs38j]
sources:
  - "MVS-BLDL-0001, section 'What BLDL with DCB=0 actually searches' — no source given"
  - "rexx370/src_ptf/TODO_IKJEFT01.md:270-272 — the same statement, as a design note"
  - "mvs38-ibmsrc/ibm/IGC/IGC018.asm, seq. 00920002-00960002 — prologue, condition 2"
  - "mvs38-ibmsrc/ibm/IGC/IGC018.asm, seq. 08740002-09120002 — NOLNKSVC: TCBJLB, else CVTLINK"
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

## Status

Open, raised 2026-09-25. Until it is settled, the link list is still the
right place for modules that must be found at logon.
