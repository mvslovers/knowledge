---
id: MVS-OPEN-0001
title: OPEN on a missing DD issues IEC130I and returns — the DCB is simply not open
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE LAB, JOB01197 — rexx370 IRXBPAM opened with a DDNAME that was not allocated, 2026-09-25"
  - "rexx370 asm/irxbpam.asm — the DOOPEN path and its `TM DCBOFLGS,DCBOFOPN` test (GitHub rexx370#230, PR #232)"
verified_on: 2026-09-25
applies_to: [rexx370, libc370]
tags: [open, dcb, dcboflgs, dcbofopn, ddname, iec130i, bsam, bpam, error-handling, gotcha]
related: [MVS-BSAM-0001]
---

## The claim

`OPEN` against a DDNAME that is not allocated **does not abend.** It writes
`IEC130I <ddname> DD STATEMENT MISSING` to the job log, leaves the
`DCBOFOPN` bit in `DCBOFLGS` off, and returns to the next instruction.

`[tested: JOB01197, MVS/CE LAB, 2026-09-25]`

## Why this is a trap

The expectation that a bad DD is fatal is a reasonable one — plenty of other
allocation failures are — and it makes the `OPEN` look self-checking. It is
not: control comes back, R15 is not a reliable answer, and the very next
`READ` or `FIND` runs against a DCB that was never opened.

**The only reliable test is the bit:**

```asm
         OPEN  ((R4),(INPUT)),MF=(E,BAOPEN)
         TM    DCBOFLGS,DCBOFOPN
         BO    OPENOK
*        ... not opened: the DD is missing
```

`[source: rexx370 asm/irxbpam.asm]`

## The message is in the job log, not in your hands

`IEC130I` is written by OPEN itself. A caller that reports its own error
("DD not allocated") produces two different-looking diagnostics for one
cause, and a caller that reports nothing leaves only a line the operator sees
and the program does not. Say which DDNAME was tried, and expect `IEC130I`
beside it.
