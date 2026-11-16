---
id: MVS-TSO-0008
title: Wally ISPF 2.2.000 — the Help key shows the .HELP panel and nothing more; without .HELP it returns to the dialog with RC 0
status: tested
platform: [mvs38j]
sources:
  - "Reproduced 2026-11-16 in a throwaway MVS/CE 3.0.0 container over TN3270 with mbt's TSO test driver (`mbt test --tso`), user IBMUSER, Wally ISPF V2.2.000 started with `ISPF`, primary option 6 (TSO command processor), probe panels uploaded to SYSGEN.ISPF.PLIB, a CLIST looping on `ISPEXEC DISPLAY PANEL(...)` that wrote LASTCC, `.PFKEY`, ZVERB (after `VGET (ZVERB) SHARED`) and ZCMD to a file after each return. Probe panels: ZZHT1 (`)INIT .HELP = ZZHH1`, `&ZHTOP`, `&ZHINDEX`), ZZHH1 (`)PROC &ZSEL = TRANS(&ZCMD 1,ZZHHA *,'?')`, `&ZCONT = ZZHH2`, `&ZUP = ZZHT0`), ZZE1 (no `.HELP`, `&ZZPFK = .PFKEY`)"
  - "Wally's own documents in SYSGEN.ISPF.DOC, read 2026-11-16: COMMANDS (HELP: Supported), CONTVARS (`.HELP`: Supported), ZVARS (ZCONT, ZHINDEX, ZHTOP, ZIND listed as function variables), FUTURE (\"HELP Panels - The author is struggling to get excited writing these\")"
  - "Reported measurement of the same behaviour on a throwaway TK5 container, 2026-11-11, from the SDSF clone project (mvslovers/sdsf, issue #11); the TK5-only parts are listed under 'Not reproduced'"
verified_on: 2026-11-16
verified_platforms: ["MVS/CE 3.0.0 (throwaway container)"]
applies_to: [sdsf]
tags: [ispf, wally, help, tutorial, zsel, zcont, zup, zhtop, pfkey, zverb, dialog]
related: [MVS-TSO-0009, MVS-TSO-0010]
---

## The claim

In Wally ISPF V2.2.000 the Help key is a **single panel**. With `.HELP` set,
PF1 displays that panel, and on it none of `ZSEL`, `ZCONT`, `ZUP`, `ZHTOP` or
`ZHINDEX` has any effect. Without `.HELP`, the Help key is not handled by ISPF
at all: it ends the `DISPLAY` with RC 0, as Enter does. `[tested]`

## With `.HELP`: one panel, no navigation

Panel ZZHT1 set `.HELP = ZZHH1`, `ZHTOP = ZZHT0`, `ZHINDEX = ZZHIX`. ZZHH1 set
`ZSEL` from its command field, `ZCONT = ZZHH2` and `ZUP = ZZHT0`. Keys pressed
in order, each time after PF1 had shown ZZHH1:

| On ZZHH1 | Screen afterwards |
|---|---|
| Enter | ZZHT1, the application panel |
| `1` then Enter | ZZHT1 (`ZSEL` would have selected ZZHHA) |
| PF3 | ZZHT1 |

The next Enter on ZZHT1 then ended the `DISPLAY` with RC 0, `.PFKEY` PF00 and
ZCMD blank; PF3 ended it with RC 8. So the help panel is shown once and left on
any key; the chain ZCONT, ZUP, ZSEL, ZHTOP, ZHINDEX that IBM's tutorial driver
follows is not evaluated. `[tested]`

This agrees with Wally's own documents: HELP and `.HELP` are marked Supported,
ZCONT, ZHINDEX, ZHTOP and ZIND are listed among the system variables, and the
FUTURE document lists "HELP Panels" as work not done. The documents do not
say that the variables are inert; the measurement does.

## Without `.HELP`: the key comes back to the dialog

Panel ZZE1 has no `.HELP` and reads `.PFKEY` in `)PROC`. Return values after each key:

| Key | DISPLAY RC | `.PFKEY` | ZVERB | ZCMD |
|---|---|---|---|---|
| PF1 | 0 | PF01 | blank | blank |
| PF13 | 0 | PF13 | blank | blank |
| `HELP` typed into ZCMD | 0 | PF00 | blank | blank |
| Enter | 0 | PF00 | blank | blank |
| PF3 | 8 | PF03 | see below | `END` |

- Only `.PFKEY` tells PF1 or PF13 apart from Enter. ZVERB is blank, unlike
  RETRIEVE, which carries the verb. To learn what command a key stands for, the
  dialog reads the system variable `ZPFnn` of the key `.PFKEY` names
  (see [[MVS-TSO-0009]]). `[tested]`
- `HELP` typed into **ZCMD** is consumed by ISPF: the dialog sees nothing in ZCMD
  and `.PFKEY` PF00. `[tested]`
- ZVERB after PF3 was `END` in one run and blank in two earlier runs with a
  slightly different logging CLIST. It is not established. Do not rely on ZVERB
  to recognise END; ZCMD `END` and RC 8 were the same in every run.

## Not reproduced

- The report says a command field of another name than ZCMD (SDSF's ISFCMD)
  receives a typed `HELP` as text. Not run here: the probe panel has no second
  command-field panel for that case.
- The report describes TK5's tutorial driver (`LBTUTOR`, `ISPTUTOR`, `LBHELP`
  in SYS2.ISP.LLIB, by Larry Belmontes) and its keys: topic number, Enter, PF10,
  PF7, PF3 work; `T` fails because it insists on `ISP00000`; `I` does nothing.
  The MVS/CE image used here has no such members, no TK5 container was started,
  and the report was not confirmed. `[assumed]`
- The report says neither the stand it worked on nor MVS/CE has `SYS2.ISP.LLIB`
  or LBTUTOR. The MVS/CE half was seen: SYSGEN.ISPF.LLIB lists no LB* member.
- Whether IBM's ISPF differs is not stated here; nothing about it was measured.

## What follows for a dialog

A product that wants IBM-style help with ZSEL, ZCONT and ZUP chains on Wally ISPF
has to display the help panels itself, in its own loop, with its own back stack.
The SDSF clone project reports that it does this: it catches PF1/HELP and TUTOR
itself and does not depend on a tutorial driver being installed. That is a
design statement from the project, not something checked here.
