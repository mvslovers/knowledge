---
id: MVS-TSO-0003
title: BREXX/370 overwrites ECTENVBK and leaves it pointing at freed storage — never read through ECTENVBK unchecked
status: tested
platform: [mvs38j]
sources:
  - "brexx370 source, commit 794b701: asm/rxinit.hlasm UPDENV (ST R4,48(,R6) 'IN THE ECTENVBK FIELD'), asm/rxterm.hlasm (FREEMAIN of the user area, no ECT reset), maclib/#ENVCTX.hlasm (ENVCTX starts with SYSPREF, no ENVBLOCK eye-catcher)"
  - "MVSCE-LAB 2026-09-25, BREXX/370 V2R5M3, batch TMP with the rexx370 TSO integration (usermod ZMG0002): JOB01315 (S0C4-010 after BREXX), JOB01316 (COMMAND NOT FOUND after BREXX exec)"
  - "Fix and regression: rexx370 PR #244 (IKJCT437 checks ECTENVBK against IRXANCHR); JOB01319, JOB01324, JOB01333; foreground s3270 run 2026-09-26"
verified_on: 2026-09-26
verified_platforms: ["MVS/CE 3.0.0 (mvsdev)"]
applies_to: [rexx370, brexx370, httprexx]
tags: [tso, rexx, brexx, ectenvbk, ect, envblock, irxanchr, coexistence, s0c4, dangling-pointer]
related: [MVS-TSO-0001, MVS-TSO-0002]
---

## The claim

**BREXX/370 writes its own context block into ECTENVBK (ECT+X'30')
unconditionally, whatever was there before, and never resets it.** When BREXX
ends it frees that block, so ECTENVBK is left pointing at storage that is no
longer allocated. `[source: brexx370 rxinit.hlasm UPDENV, rxterm.hlasm]`
`[tested]`

In BREXX's `UPDENV`, for TSO foreground and background alike:

```
           L     R6,USRPECT    SET REXX ENVIRONMENT CONTEXT
           ST    R4,48(,R6)      IN THE ECTENVBK FIELD
```

`R4` is BREXX's `ENVCTX`. That is not an IBM ENVBLOCK: it starts with
`SYSPREF` and carries no `ENVBLOCK` eye-catcher. `rxterm.hlasm` frees BREXX's
storage and contains no store into the ECT.

## What it does to another REXX in the same session

Measured with the rexx370 TSO integration, whose TMP creates an ENVBLOCK at
logon and anchors it in ECTENVBK:

| After | ECTENVBK then | A later implicit REXX exec |
|---|---|---|
| `BREXX` (no exec) | dangling pointer into freed storage (`X'208458'`) | **S0C4 reason 010** on the first read through it: a CLC of the eye-catcher (JOB01315) |
| `BREXX exec` | BREXX's `ENVCTX` (no `ENVBLOCK` eye-catcher) | no environment found, falls back to CLIST: `COMMAND … NOT FOUND` (JOB01316) |

The rexx370 environment itself is intact the whole time. It is simply no longer
reachable through ECTENVBK. A new logon cures it.

## Consequences

- **An eye-catcher check is not validation.** Reading 8 bytes through a
  foreign pointer is exactly what faults when the storage is gone. Compare the
  pointer with something you own before you dereference it.
- **Keep your own registry and treat ECTENVBK as a hint.** rexx370 compares the
  value with the live environments in `IRXANCHR`. If it is not one of them,
  rexx370 takes this ECT's newest TSO-attached environment from there
  (`envblock_ectptr` = the ECT, flag `TSO_ATTACHED`). The slot is **not**
  written back: a BREXX exec that issues an implicit EXEC still owns it.
  (rexx370 `tso/IKJCT437.ASM` FINDENV, PR #244.)
- **Every consumer of ECTENVBK needs the same care**, not just the EXEC path.
  That includes any code that uses "the current environment" from ECTENVBK, for
  example a service called without an explicit ENVBLOCK, and any further
  product anchoring there (such as a BREXX TSO integration).
- Not a BREXX bug report yet: BREXX predates any other REXX environment on
  MVS 3.8j, so nothing else ever lived in that slot. A reset in `rxterm`
  (restoring the value `UPDENV` found) would make it a good neighbour.
