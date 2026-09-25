---
id: CF-2026-002
title: Does BLDL fail for every register-form list operand, or only for (1)?
status: tested
platform: [mvs38j]
sources:
  - "MVS-BLDL-0001 — the measured RC=4 with LA R1,list / BLDL 0,(1)"
  - "mvs38-ibmsrc/macros/maclib/BLDL.asm, seq. 00100000 — &NAME IHBINNRA &DCB,&LIST"
  - "mvs38-ibmsrc/macros/maclib/IHBINNRA.asm — labels .NOPT, .CHKB, .REGB"
  - "MVS/CE LAB (mvsdev.lan:8082), JOB01201 KBBLDL — 2026-09-25, IFOX00 listing and WTO output"
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

## Resolution — position B

Settled by experiment on MVS/CE LAB, JOB01201, 2026-09-25. **Only `(1)`
fails.** Steps A (symbolic), C (`(2)`) and D (`(0)`) produced byte-identical
entries: `IEFBR14` found in the link library. Step B (`(1)`) left the list
untouched.

The listing (IFOX00, `SYSLIB SYS1.MACLIB`) shows the expansion predicted
above:

```
DOB      LA    1,LIST1
         LA    1,0                  LOAD PARAMETER REG 1
         LR    0,1                  LOAD PARAMETER REG 0
         LA    1,0(1)               CLEAR HIGH ORDER BYTE ZA00734
         SVC   18
DOC      LA    2,LIST1
         LA    1,0                  LOAD PARAMETER REG 1
         LR    0,2                  LOAD PARAMETER REG 0
         LA    1,0(1)               CLEAR HIGH ORDER BYTE ZA00734
         SVC   18
DOD      LA    0,LIST1
         LA    1,0                  LOAD PARAMETER REG 1
         LA    1,0(1)               CLEAR HIGH ORDER BYTE ZA00734
         SVC   18
```

Output:

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

The prediction "RC=0, RC=0, RC=4" did not hold for R15 — every step using
`LIST1` returned RC=4. That was not the question being tested: `IKJEFT01` is
in `SYS1.LPALIB` on MVS/CE and BLDL does not search the LPA (see
`MVS-BLDL-0001`). The per-entry bytes answer the question.

## Status

Closed 2026-09-25 by JOB01201. Outcome B; `MVS-BLDL-0001` corrected.
