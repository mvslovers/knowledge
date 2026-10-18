---
id: MVS-FIND-0001
title: FIND expands through IHBINNRA too, so it loses an operand passed in R1 exactly as BLDL does
status: source
platform: [mvs38j]
sources:
  - "mvs38-ibmsrc/macros/maclib/FIND.asm — `&NAME IHBINNRA &DCB,&AREA` for TYPE=D; the `.REG` / `.CONT` path for TYPE=C"
  - "mvs38-ibmsrc/macros/maclib/IHBINNRA.asm — labels .NOPT, .REGA, .NAMEIT, .CHKB, .REGB, .END"
  - "rexx370 asm/irxbpam.asm — the caller that hit this and documents the avoidance (GitHub rexx370#230, PR #232)"
verified_on: 2026-10-18
applies_to: [rexx370, mvs38src]
tags: [find, bldl, ihbinnra, macro, register-notation, svc18, bpam, directory, gotcha]
related: [MVS-BLDL-0001]
---

## The claim

`BLDL` is not the only macro with the register trap of `MVS-BLDL-0001`.
**`FIND` expands through the same inner macro and loses an operand passed in
R1 the same way** — and `MVS-BLDL-0001` cannot say so, because it was written
and measured on `BLDL` alone.

## Why

`FIND dcb,area,D` generates `IHBINNRA &DCB,&AREA` and nothing else before the
SVC. `[source: FIND.asm]`

```asm
&NAME    IHBINNRA &DCB,&AREA
         LCR   1,1                               INDICATE TYPE D
         SVC   18                                ISSUE FIND SVC
```

That is byte-for-byte the shape `BLDL` uses, so the order
`IHBINNRA` imposes applies unchanged: **the first operand (the DCB) is loaded
into R1, and only then is the second operand (the area) loaded into R0.**
`[source: IHBINNRA.asm, .NOPT → .REGA → .CHKB → .REGB]`

## The precise rule, which is narrower than "avoid R0 and R1"

Reading the macro rather than the habit:

| Form | Generated | Verdict |
|---|---|---|
| `FIND (4),(5),D` | `LR 1,4` then `LR 0,5` | safe |
| `FIND (4),(1),D` | `LR 1,4` then `LR 0,1` | **broken** — R1 already holds the DCB |
| `FIND (1),(5),D` | nothing for R1 (`.NAMEIT`), `LR 0,5` | safe — R1 is where the DCB belongs |
| `FIND (0),(5),D` | `LR 1,0` then `LR 0,5` | safe |
| `FIND dcb,(0),D` | `LA 1,dcb`, nothing for R0 (`.CHKB` exits on `(0)`) | safe — a preloaded R0 is used as is |

So the single dangerous case is **the second operand in R1**, not "register
notation", and not R0. `[source: IHBINNRA.asm]` The same holds for `BLDL`,
where it was measured: `(0)`, `(2)` and the symbolic form all work and only
`(1)` fails (`MVS-BLDL-0001`, JOB01201).

**`TYPE=C` has the same shape for a different reason.** It generates
`IHBINNRA &DCB` — one operand, so R1 — and reads the area register *after*
that:

```asm
.REG     LR    15,&AREA(1)                       LOAD AREA ADDRESS
.CONT    MVC   0(4,1),0(15)                      MOVE RELAD TO DCB
```

`FIND (4),(1),C` therefore picks up the DCB address as the area address.
`[source: FIND.asm]`

## Status, honestly

This is read in the macro source, **not measured for `FIND`**. The
corresponding `BLDL` case is measured (`MVS-BLDL-0001`, `CF-2026-002`,
JOB01201) and the expansion is the same text, which is why this is `source`
and not `assumed` — but no job has yet run `FIND …,(1),D` and watched it fail.

## What a caller should do

rexx370's `irxbpam.asm` writes `FIND (R4),(R5),D` and states the rule in its
header as "registers 0 and 1 are unusable for either operand". That is
stricter than the macro requires and is the right habit to keep in code: the
table above is the explanation, not a licence to use R0 and R1 in a macro
whose expansion the next reader will not have in front of them.
