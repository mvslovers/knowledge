---
id: MVS-BLDL-0001
title: BLDL returns RC=4 for modules that are certainly there — the list must be passed symbolically, not in a register
status: disputed
platform: [mvs38j]
sources:
  - "rexx370/src_ptf/IKJEFTRX.ASM — the caller this was found in"
  - "rexx370/src_ptf/TODO_IKJEFT01.md — build recipe and the measured run log"
  - "mvs38-ibmsrc/ibm/IKJ/IKJEBECI.asm:320, 798-803 — IBM's own BLDL call and list"
  - "mvs38-ibmsrc/ibm/IKJ/IKJEBESA.asm:1637-1640 — a second IBM caller, same shape"
  - "MVS/CE LAB (mvsdev.lan:8082), jobs JOB01125/01127/01129/01131 — 2026-09-23"
verified_on: 2026-09-23
applies_to: [rexx370, mvs38src]
tags: [bldl, svc18, bpam, directory, pds, rc4, macro, ihbinnra, linklist, gotcha]
related: [CF-2026-002, PM-2026-001]
---

## Symptom

`BLDL` returns **RC=4 ("one or more names not found")** for module names that
are provably present — including `IEFBR14` and `IKJEFT01`, which are in
`SYS1.LINKLIB` on every system. No abend, no message, no diagnostic. The
caller concludes the module is not installed and silently does nothing.

This is a *plausible* failure: RC=4 is exactly what "not installed" looks
like, so the natural next step is to go hunting through LINKLIST
concatenations, LLA, APF lists and library search order — none of which is
the problem.

## Root cause

> **Disputed — see `CF-2026-002`.** Only `(1)` was measured. The `IHBINNRA`
> expansion suggests only `(1)` breaks, not register notation in general.

**The list address must be passed symbolically. Register notation does not
work.**

```asm
         LA    R1,MYLIST
         BLDL  0,(1)        <-- assembles clean, finds NOTHING, RC=4
```
```asm
         BLDL  0,MYLIST     <-- correct
```

The macro expands through `IHBINNRA &DCB,&LIST` to load R0 and R1 before
`SVC 18`. With the `(1)` form the list address does not arrive where BLDL
expects it, and BLDL reports every entry as not found. The assembler accepts
the syntax without complaint.

IBM's own callers use the symbolic form throughout — `IKJEBECI:320`
(`BLDL 0,BLDLIST`), `IKJEBESA:1640` (`BLDL SADCB,SABLDL`).

## Second trap in the same list: entry length

The list header is `FF` (halfword count) then `LL` (halfword entry length).
Documentation gives 12 as the minimum, which tempts you to write

```asm
         DC    H'2'
         DC    H'12'              8-byte name + 4 bytes returned
```

IBM's own callers use **58** — 8 bytes of name plus 50 bytes BLDL fills in
(`IKJEBECI:798-803`):

```asm
BLDLIST  DS    0H
BLDLNO   DS    H                  number of entries
BLDLLEN  DS    H                  length of each entry
BLDLNAME DS    CL8                name of module
         DS    CL50               info filled in by BLDL
ENTRYLEN EQU   *-BLDLNAME         = 58
```

**Measured scope:** the decisive variable was the list form, not the length —
`LL=58` with `BLDL 0,(1)` still returned RC=4, and `LL=58` with the symbolic
form returned RC=0. Whether `LL=12` works with the symbolic form was not
isolated. Use 58; it is what IBM uses and it costs 92 bytes.

## Two more things that bite around this

**Entries must be in ascending EBCDIC order.** BLDL searches the directory
once and walks the list in step with it. `IRXANCHR` before `IRXINIT` is
correct — they differ first at position 4, where `A`=X'C1' < `I`=X'C9'.

**BLDL writes into the list**, so in a RENT module the list cannot be a
static constant. Copy a pattern into GETMAINed storage and pass that. This
forces the `GETMAIN` ahead of whatever the BLDL was meant to guard.

## What BLDL with DCB=0 actually searches

The link library — *not* the caller's STEPLIB or JOBLIB. For a TMP exit or
anything that runs at logon this is the right semantic (there is no STEPLIB
then), but it means a module reachable in test via `//STEPLIB` will not be
found in production. Put it in the LINKLIST or LPA.

## How to find this

The mistake is easy to make and hard to see, because RC=4 is indistinguishable
from a genuine "not installed". The cheap discriminator is a **control probe
with names that are certainly present**:

```asm
         MVC   WBLDL(L),CTLPAT    IEFBR14 and IKJEFT01
         BLDL  0,WBLDL
         LTR   R15,R15
         BZ    FORMAT_OK          -> the search path is the problem
         B     FORMAT_BAD         -> the list is the problem
```

RC=4 on `IEFBR14` means the list is wrong, full stop. That one probe
separates "my list is malformed" from "the module really isn't there" and
saves an afternoon of looking at library concatenations.
