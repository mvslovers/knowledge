---
id: MVS-BSAM-0002
title: EODAD and SYNAD are entered from CHECK with the caller's registers, and only SYNAD returns
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE LAB, JOB01197 — rexx370 IRXBPAM: READ/CHECK to end of member and through a SYNAD error, 2026-09-25"
  - "rexx370 asm/irxbpam.asm — labels EOD and SYN, and the AFTERCHK re-entry (GitHub rexx370#230, PR #232)"
verified_on: 2026-09-25
applies_to: [rexx370, libc370]
tags: [bsam, bpam, read, check, eodad, synad, dcb, exit-routine, registers]
related: [MVS-BSAM-0001]
---

## The claim

Both DCB exits taken by `CHECK` run **with R2–R13 exactly as they were at the
`CHECK`**, so a module that keeps its base and work registers there can use
them in the exit without saving anything. The two differ in how they leave:

| Exit | Entered when | Leaves by |
|---|---|---|
| `EODAD` | end of the data set / member reached | **branching into your own code**; it does not return to CHECK |
| `SYNAD` | the access method reports an I/O error | `BR R14`, after which `CHECK` returns to its caller normally |

`[tested: JOB01197]`

## Why it matters that only one of them returns

The natural reading — "two exits, both called, both return" — is wrong for
`EODAD`, and the failure is structural rather than visible: code written after
the `CHECK` never runs at end of file, because control never comes back to
it.

The shape that works is to set a flag in each exit and give both a single
re-entry point after the `CHECK`:

```asm
         READ  (R3),SF,(R4),(R5),'S',MF=E
         CHECK (R3)
AFTERCHK DS    0H                 <- SYNAD lands here by returning
         TM    BPFLAGS,FEOD
         BO    READEOD
         TM    BPFLAGS,FERR
         BO    RETURN
*  ...  normal path: compute the block length
*
EOD      OI    BPFLAGS,FEOD
         B     AFTERCHK           <- EODAD branches here itself
*
SYN      OI    BPFLAGS,FERR
         BR    R14
```

`[source: rexx370 asm/irxbpam.asm]`

## The consequence for a RENT module

Because the exits keep the caller's registers, the flag byte can live in the
caller-owned work area the base registers already address — no static, no
GETMAIN of its own, and the module stays reentrant. The DCB's `EODAD`/`SYNAD`
addresses point back into the CSECT and are copied in with the DCB model when
the work area is built.
