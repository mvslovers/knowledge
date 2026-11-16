---
id: MVS-TSO-0010
title: Wally ISPF 2.2.000 — ISPEXEC SELECT CMD(%name parm) drops the last character of the parameters
status: tested
platform: [mvs38j]
sources:
  - "Reproduced 2026-11-16 in a throwaway MVS/CE 3.0.0 container over TN3270 with mbt's TSO test driver (`mbt test --tso`), user IBMUSER, Wally ISPF V2.2.000, primary option 6. CLIST ZZECHO (`PROC 1 P`, then writes `ECHO <&P>` to a file) was called from another CLIST by four `ISPEXEC SELECT CMD(...)` lines; the file was read back through the z/OSMF REST data-set interface"
  - "Reported measurement of the same cut from the SDSF clone project (mvslovers/sdsf), 2026-11-12, with the same four forms"
verified_on: 2026-11-16
verified_platforms: ["MVS/CE 3.0.0 (throwaway container)"]
applies_to: [sdsf]
tags: [ispf, wally, ispexec, select, cmd, clist, parameter, off-by-one, percent]
related: [MVS-TSO-0008, MVS-TSO-0009]
---

## The claim

`ISPEXEC SELECT CMD(%name parm)` hands the CLIST `name` its parameter string
**without the last character**. A blank before the closing parenthesis, or leaving
out the `%`, avoids the cut. RC 0 either way, so nothing signals it. `[tested]`

## The measurement

Called CLIST `ZZECHO`: `PROC 1 P`, then `OPENFILE`/`PUTFILE` of `ECHO <&P>`.
Lines read back:

| Call | `P` received |
|---|---|
| `SELECT CMD(%ZZECHO ABCDEF)` | `ABCDE` |
| `SELECT CMD(%ZZECHO ABCDEF )` | `ABCDEF` |
| `SELECT CMD(ZZECHO ABCDEF)` | `ABCDEF` |
| `SELECT CMD(%ZZECHO 'ABCDEF')` | `'ABCDEF` |

The quoted form loses the closing quote, so the cut is on the character, not on a
blank-delimited word. `[tested]`

## What this looked like in practice

The SDSF project reports that the cut made `ZPF07` read `HEL` for `HELP` and `U` for
`UP` in the first runs of the key measurement ([[MVS-TSO-0009]]), where the value
was handed over through `SELECT CMD(%name ...)`. Not re-run here. `[assumed]`
The cut is easy to mistake for a fault in whatever the parameter carries: check
the call form first.

## Not measured

- Only the four forms above, one CLIST, one parameter. CLISTs with more than one
  positional parameter, REXX execs and `SELECT CMD(...)` without a CLIST were not
  tried.
- The cut was not traced to its cause (the SELECT service or the CLIST
  parameter parser).
