---
id: MVS-TSO-0006
title: ISPF logical screens share one ECT — ECTIOWA is swapped per screen, ECTENVBK is not, so two live BREXX/370 dialogs lose input
status: tested
platform: [mvs38j]
sources:
  - "Measured 2026-11-04 on a throwaway TK5 container (ISPF V2R2M0, unchanged ZP60038), one run per case. Probe program and raw lines: mvslovers/usermods, branch zmg0003/ispf-test, zmg0003/test/ispf/ZMGWHO.ASM, results-screens.txt (READY and two-screen sections), results-twoscreens.txt (cases A, C, D, E), results-attention.txt"
  - "BREXX/370 feature/irxexcom b6862b0 with ZMG0001 and the REXX-capable IKJCT441 (usermod ZMG0003, then named ZMG0004), no trace; every address and every RC in the tables was read back from the raw lines above"
verified_on: 2026-11-04
verified_platforms: ["TK5 throwaway container (ISPF V2R2M0)"]
applies_to: [brexx370, rexx370]
tags: [ispf, split-screen, ect, ectiowa, ectenvbk, envblock, input-stack, iostelm, brexx, attention, s0c1, ikjct441]
related: [MVS-TSO-0003, MVS-TSO-0007, MVS-SUP-0003]
---

## The claim

On ISPF V2R2M0, all logical screens of one session run under **one ECT**.
**`ECTIOWA` (ECT+4) is per screen** — ISPF changes it inside the one ECT when it
switches screens — but **`ECTENVBK` (ECT+X'30') is not**: one word serves every
screen. A product that publishes a REXX environment there therefore sees the
environment of whichever screen published last. `[tested]`

Not measured on MVS/CE; the setup was TK5 only.

## The measurement

Probe `ZMGWHO` printed `LWAPECT`, `CPPLECT`, ECT+X'30', ECT+4 and the top input
stack element (IOSTELM). First column is the case, values are hexadecimal:

| Where | LWAPECT = CPPLECT | ECTIOWA (ECT+4) | ECTENVBK (ECT+X'30') |
|---|---|---|---|
| READY | A7CF4 | A9FC8 | 0 |
| ISPF screen 1 | A7CF4 | A9F98 | marker stored by the probe in screen 1 |
| ISPF screen 2 | A7CF4 | 187FD0 | same marker, unchanged |
| screen 2 after a store there | A7CF4 | 187FD0 | screen 2's marker |
| back in screen 1 | A7CF4 | A9F98 | screen 2's marker |

- Each screen has its own **task tree**: a command in screen 1 had parent and
  grandparent X'994D88' and X'9A2780', one in screen 2 X'98F6A8' and X'98FDD8'.
- The current TCB does not identify a screen: in the READY section one TCB
  address (X'9A87D8') serves a whole series of commands.

## Input stack elements are an array — the address says the depth, not the instance

READY, TK5, ISPF not running: terminal element X'A9FD8' (first byte X'80'), a
CLIST at depth 1 X'A9FDC', a nested CLIST X'A9FE0' (first byte X'4A' for a CLIST).
Every later CLIST at the same depth got the **same address**, also after an abend
in a CLIST and after an attention. `[tested]`

- An IOSTELM value recorded earlier cannot tell whether the same procedure is still
  running. A word "an exec is running" that holds IOSTELM is only as good as its
  cleanup after an abend. `[inferred]`
- The value does separate the screens at one moment, because each screen has its
  own stack (ECTIOWA above). `[inferred]`

At a CLIST `READ`, an attention (PA1) left the input stack element in place: the
same IOSTELM X'A9FDC' before and after, in two successive probes.

## Two live BREXX/370 dialogs

BREXX/370 execs started with `ISPEXEC SELECT CMD(%name)` publish their environment in
ECTENVBK. Two screens, each with an exec waiting in a panel:

| Case | ECTENVBK when screen 1 continues | Result |
|---|---|---|
| A: both execs alive, back to screen 1, `NEW1` typed into the field | X'3A20A0', the environment of exec 2 | `DISPLAY` RC=0, but the variable stays `OLD1`: **the input is lost silently**. The next `VGET` abends **S0C1** in ISPEXEC, registers 12–15 `00153000 002A0128 40153564 00000028`, caught by BREXX's ESTAE (`BRX0003E`) |
| C: exec 1 ends while exec 2 is alive, then exec 2 ends | after both: X'24C0A0', the environment of exec 1, which has ended | a **stale pointer** stays in ECTENVBK; whether reading it abends depends on the storage, not settled here |
| D: exec 2 ended before the return | X'24C0A0', the environment of screen 1 | input arrives (`FLD=NEW3`) |
| E: a CLIST dialog waits on screen 2 | X'24C0A0' | input arrives; the CLIST continues |

The S0C1 with R15 = X'28' (40) is probably ISPF's reaction to RC=40 from
`IKJCT441`; ISPF was not disassembled. `[inferred]` Only two live REXX dialogs
fail, and exec 1's first return shows no error at all.

A single anchor in ECTENVBK does not fit exec runs in two screens. Derived from the
table, not measured with more than these two execs. `[inferred]`

## Attention during a running exec

BREXX/370 b6862b0 has no STAX exit. PA1 during a loop in a published exec:

- **READY:** `READY` appears and the next command runs under a new task (TCB
  X'9A83E8' before, X'9A84D0' after). The exec is gone, but ECTENVBK still holds its
  environment (X'1720A0'), also several commands later.
- **ISPF, option 6:** `COMMAND TERMINATED`. ECTENVBK still holds the environment
  (X'24C0A0'). The next plain CLIST dialog ends with `PROCESS HAS ABENDED`; the
  abend code was not captured. The same kind of dialog ran normally in case E, in a
  session without an attention.

So BREXX's ESTAE path does not clean ECTENVBK here: any product that publishes in
ECTENVBK needs its own attention handling. `[inferred]` This extends
`MVS-TSO-0003`, which records the same stale pointer after a normal exit of BREXX
in plain TSO.

## Limits

- One run per case, TK5 only; ISPF and the usermod were not disassembled.
- BREXX/370 was a development build (`feature/irxexcom`), not a release.
