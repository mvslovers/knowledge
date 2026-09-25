---
id: MVS-BLDL-0001
title: BLDL returns RC=4 for modules that are certainly there — BLDL 0,(1) loses the list address
status: tested
platform: [mvs38j]
sources:
  - "rexx370/src_ptf/IKJEFTRX.ASM — the caller this was found in"
  - "rexx370/src_ptf/TODO_IKJEFT01.md — build recipe and the measured run log"
  - "mvs38-ibmsrc/ibm/IKJ/IKJEBECI.asm:320, 798-803 — IBM's own BLDL call and list"
  - "mvs38-ibmsrc/ibm/IKJ/IKJEBESA.asm:1637-1640 — a second IBM caller, same shape"
  - "mvs38-ibmsrc/macros/maclib/IHBINNRA.asm — .NOPT / .CHKB / .REGB"
  - "mvs38-ibmsrc/ibm/IGC/IGC018.asm — NOLNKSVC (search order), CLRENT (R zeroed), LIB / LINKSVC / JOBLIB (Z byte), :387 (minimum entry length)"
  - "MVS/CE LAB (mvsdev.lan:8082), jobs JOB01125/01127/01129/01131 — 2026-09-23"
  - "MVS/CE LAB (mvsdev.lan:8082), JOB01201 KBBLDL — 2026-09-25, six BLDL forms, listing kept in CF-2026-002"
verified_on: 2026-09-25
applies_to: [rexx370, mvs38src]
tags: [bldl, svc18, bpam, directory, pds, rc4, macro, ihbinnra, linklist, steplib, gotcha]
related: [CF-2026-002, CF-2026-003, PM-2026-001]
---

## Symptom

`BLDL` returns **RC=4 ("one or more names not found")** for module names that
are provably present. No abend, no message, no diagnostic. The caller
concludes the module is not installed and silently does nothing.

This is a *plausible* failure: RC=4 is exactly what "not installed" looks
like, so the natural next step is to go hunting through LINKLIST
concatenations, LLA, APF lists and library search order — none of which is
the problem.

## Root cause

**`BLDL dcb,(1)` loses the list address.** BLDL takes the list in **R0** and
the DCB in **R1**. `IHBINNRA` loads the DCB operand into R1 *first* and only
then copies the list register into R0 — so with `(1)` it copies the DCB it
just loaded. Assembled on MVS/CE (JOB01201):

```
DOB      LA    1,LIST1
         LA    1,0             LOAD PARAMETER REG 1      <- DCB=0 over the list
         LR    0,1             LOAD PARAMETER REG 0      <- R0 = 0
         LA    1,0(1)          CLEAR HIGH ORDER BYTE
         SVC   18
```

BLDL then reads its list header from address 0 and fills in nothing.

**Every other form works.** `(0)`, `(2)` and the symbolic form found
`IEFBR14` identically; only `(1)` left the list untouched. `[tested: JOB01201]`

```asm
         BLDL  0,MYLIST     symbolic      works
         BLDL  0,(2)        R2 -> list    works   (LA 1,0 / LR 0,2)
         BLDL  0,(0)        R0 -> list    works   (LA 1,0, R0 left alone)
         BLDL  0,(1)        R1 -> list    RC=4, nothing found
```

The assembler accepts `(1)` without complaint. IBM's own callers use the
symbolic form throughout — `IKJEBECI:320` (`BLDL 0,BLDLIST`),
`IKJEBESA:1640` (`BLDL SADCB,SABLDL`).

## Second trap in the same list: entry length

The list header is `FF` (halfword count) then `LL` (halfword entry length).
The minimum is 12 — SVC 18 checks against `PDS2LIBF-PDS2` (`IGC018:387`) —
which tempts you to write `DC H'2',H'12'`.

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
`LL=58` with `BLDL 0,(1)` still returned RC=4 on 2026-09-23, and JOB01201 ran
every form with `LL=58`. Whether `LL=12` works was not isolated. Use 58; it
is what IBM uses.

## Reading the result per entry

RC=4 means *one or more* names were not found, so R15 alone cannot say which.
The entry can:

- **SVC 18 zeroes the R byte of every entry before it searches** (`IGC018`,
  `CLRENT`: `MVI PDS2TTRP+2,0`). A not-found entry keeps its TT but has
  R=`00`. Measured: an entry prefilled with `X'FF'` came back
  `FFFF00FFFF…`. `[tested: JOB01201]` So test R, not "TTR changed".
- **The byte after K is Z, the library the name came from:** `01` = link
  library, `02` = JOBLIB/STEPLIB/TASKLIB, `00` = the DCB the caller passed
  (`IGC018`, `LIB`: `USERLIB 0`, `LINKSVC 1`, `JOBLIB 2`). JOB01201: `IEFBR14`
  → `01`, a module only in `//STEPLIB` → `02`.
- A list that SVC 18 never read — the `(1)` case — stays byte-for-byte as it
  was, R included.

## Two more things that bite around this

**Entries must be in ascending EBCDIC order.** BLDL searches the directory
once and walks the list in step with it. `IRXANCHR` before `IRXINIT` is
correct — they differ first at position 4, where `A`=X'C1' < `I`=X'C9'.

**BLDL writes into the list**, so in a RENT module the list cannot be a
static constant. Copy a pattern into GETMAINed storage and pass that. This
forces the `GETMAIN` ahead of whatever the BLDL was meant to guard.

## What BLDL with DCB=0 actually searches

**The current task's JOBLIB/STEPLIB first, then the link library** —
`IGC018` at `NOLNKSVC` takes `TCBJLB` of the current TCB and falls back to
`CVTLINK`. Measured: `BLDL 0,list` found a module that existed only in
`//STEPLIB` (Z=`02`); `BLDL (2),list` with R2 = `CVTLINK` did not.
`[tested: JOB01201]`

**The LPA is not searched.** On MVS/CE `IKJEFT01` is in `SYS1.LPALIB`, not
`SYS1.LINKLIB`, and `BLDL 0,list` reports it not found (R=`00`).
`[tested: JOB01201; member lists of SYS1.LINKLIB and SYS1.LPALIB, 2026-09-25]`
Only MVS/CE 3.0.0 was measured; TK5 was not.

For a TMP exit or anything that runs at logon, the consequence is still
"put it in the LINKLIST": there is no STEPLIB then, so the search falls
through to the link library. Putting the module in LPA alone is not enough
for a BLDL guard, and a test that runs with the module in `//STEPLIB` will
find it where logon will not.

## How to find this

The mistake is easy to make and hard to see, because RC=4 is indistinguishable
from a genuine "not installed". The cheap discriminator is a **control entry
with a name that is certainly in the link library** — `IEFBR14` — checked
by its R byte, not by R15:

```asm
         MVC   WBLDL(L),CTLPAT    IEFBR14 plus the names you care about
         BLDL  0,WBLDL
         CLI   CTLENT+10,0        R byte of the IEFBR14 entry
         BE    FORMAT_BAD         -> the list is the problem
         B     FORMAT_OK          -> look at the other entries' R bytes
```

Do not use `IKJEFT01` as the control: it lives in LPA on MVS/CE and is never
found by BLDL, so a probe relying on it reports RC=4 even with a correct
list. The list contents of the 2026-09-23 runs were not kept, so which
names they used can no longer be checked.
