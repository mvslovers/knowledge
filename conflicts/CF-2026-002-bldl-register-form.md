---
id: CF-2026-002
title: Does BLDL fail for every register-form list operand, or only for (1)?
status: disputed
platform: [mvs38j]
sources:
  - "MVS-BLDL-0001 — the measured RC=4 with LA R1,list / BLDL 0,(1)"
  - "mvs38-ibmsrc/macros/maclib/BLDL.asm, seq. 00100000 — &NAME IHBINNRA &DCB,&LIST"
  - "mvs38-ibmsrc/macros/maclib/IHBINNRA.asm — labels .NOPT, .CHKB, .REGB"
verified_on: 2026-09-25
applies_to: [rexx370, mvs38src]
tags: [bldl, ihbinnra, macro, register-notation, svc18]
related: [MVS-BLDL-0001]
---

## The two positions

**A.** `MVS-BLDL-0001` states the rule as *"the list address must be passed
symbolically. Register notation does not work."* The measurement behind it is
`LA R1,MYLIST` followed by `BLDL 0,(1)` → RC=4 for `IEFBR14` and `IKJEFT01`, and
`BLDL 0,MYLIST` → RC=0 (MVS/CE LAB, JOB01125/01127/01129/01131, 2026-09-23).
Only register 1 was measured.

**B.** The macro source says register 1 is the one case that breaks. `BLDL`
calls `IHBINNRA &DCB,&LIST`, so `&A` is the DCB and `&B` the list. For
`BLDL 0,(1)`, with `&E` empty, `IHBINNRA` goes to `.NOPT`. `&A='0'` is neither
empty, `(1)` nor a register, so it generates `LA 1,0`. At `.CHKB`, `&B='(1)'`
starts with `(`, so `.REGB` generates `LR 0,1`:

```asm
         LA    1,0          DCB operand into R1 — overwrites the list address
         LR    0,1          list register copied from R1, now 0
         LA    1,0(1)       from BLDL itself
         SVC   18
```

R0, which carries the list, is 0, so BLDL reads its FF/LL header from low
storage and finds nothing. `[source: IHBINNRA .NOPT/.CHKB/.REGB]`

By the same expansion, `BLDL 0,(2)` through `(12)` gives `LA 1,0` / `LR 0,n`
and keeps the list address, and `BLDL 0,(0)` generates nothing for R0
(`.CHKB` exits on `(0)`), so a preloaded R0 is used as is. `[inferred]`, not
measured.

## Why they cannot both be the whole story

A predicts RC=4 for every register form; B predicts RC=4 for `(1)` only. Both
agree with the one measurement. The *mechanism* in `MVS-BLDL-0001` ("the list
address does not arrive where BLDL expects it") fits B. The *rule* it states
does not.

## What would settle it

One job, in the same harness as JOB01125ff: the control probe from
`MVS-BLDL-0001` (`IEFBR14`, `IKJEFT01`, `LL=58`), called three ways —

1. `LA R2,list` / `BLDL 0,(2)`
2. `LA R0,list` / `BLDL 0,(0)`
3. `LA R1,list` / `BLDL 0,(1)`, as the negative control.

B predicts RC=0, RC=0, RC=4. Keep the assembler listing so the expansion is on
record next to the return codes.

## Status

Open, raised 2026-09-25 during a KB consistency pass. Until it is settled, the
symbolic form stays the safe advice either way.
