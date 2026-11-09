---
id: MVS-TSO-0007
title: ISPF V2R2M0 — VGET after VPUT with no DISPLAY between them sometimes does not fetch, and returns RC 0 either way
status: tested
platform: [mvs38j]
sources:
  - "Measured 2026-11-05 on a throwaway TK5 container, ISPF V2R2M0, one logon, ISPEXEC SELECT CMD(%name), BREXX/370 feature/irxexcom 9dbcf46 with ZMG0001 and the REXX-capable IKJCT441 (usermod ZMG0003, then named ZMG0004) installed; the CLISTs run through its unchanged CLIST path"
  - "mvslovers/usermods, branch zmg0003/ispf-test: zmg0003/test/ispf/results-after.txt, case NESTCTL (members XU, XC, XB, XA, XV, XR); member sources in zmg0003/test/ispf/lib/. Every row of the tables below was read back from there"
verified_on: 2026-11-05
verified_platforms: ["TK5 throwaway container (ISPF V2R2M0)"]
applies_to: [brexx370, rexx370]
tags: [ispf, vput, vget, shared-pool, rexx, clist, ispexec, rc-0, silent-failure, ikjct441]
related: [MVS-TSO-0006]
---

## The claim

A dialog that does `VPUT (V) SHARED`, changes `V`, and does `VGET (V) SHARED`
**without a `DISPLAY` between them** gets the old value back in two of four
measured cases and the changed value in the other two. `VGET` ends **RC 0 in all
four**, so the return code does not show it. `[tested]`

| Member | Language | V at VPUT | V at VGET | V after VGET | VGET RC |
|---|---|---|---|---|---|
| `XU` | REXX | `INNER` | `CLOBBER` | `CLOBBER` — not fetched | 0 |
| `XB` | CLIST | `INNER` | `CLOBBER` | `CLOBBER` — not fetched | 0 |
| `XA` | REXX | `FROMXA` | `OLD` | `FROMXA` — fetched | 0 |
| `XC` | CLIST | `FROMXC` | `OLD` | `FROMXC` — fetched | 0 |

The members ran in the order `XU`, `XC`, `XB`, `XA`, so the two outcomes alternate:
it is not the order and not the language. In both failing cases the value at
`VGET` is **longer** than the value at `VPUT`, in both working ones **shorter**.
That is a pattern in four lines, not a measured cause: the lengths were not varied
on their own. `[assumed]`

The `CLISTs` go through `IKJCT441`'s unchanged CLIST path. The unchanged ZP60038
`IKJCT441` was not run for exactly these four members, and neither was MVS/CE.

## A VGET that fails blanks the variable

`SET &NOVAR = OUTER`, then `VGET (NOVAR) SHARED` for a variable that is not in the
pool: **RC 8**, and `NOVAR` is empty afterwards — in a CLIST (`XV`) and in REXX
(`XR`). `[tested]`

## What this is not

`zmg0003/README.md` records another defect ("Open defect"): a variable that first
appears after the first `ISPEXEC` of a dialog does not get its value back from
`VGET`. That is a different condition — in all members above the variable exists
before the first `ISPEXEC`. The two were not shown to be the same mechanism.
