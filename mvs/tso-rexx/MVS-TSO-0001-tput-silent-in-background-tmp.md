---
id: MVS-TSO-0001
title: TPUT does nothing in the background TMP — SVC 93 returns without work when ASCBTSB is zero
status: tested
platform: [mvs38j]
sources:
  - "mvs38src/src/IKT0009C.ASM (SVC 93 entry, reconstructed) — L R9,60(,R8) / LTR R9,R9 / BE A000236; A000236 is a bare return"
  - "MVSSRC/mvs38_sources/jay/MVSSRC.SYM1-3/IKJEFT01:3099-3100 — INPUT DC CL8'SYSTSIN ', OUTPUT DC CL8'SYSTSPRT'"
  - "MVSSRC/mvs38_sources/jay/MVSSRC.SYM1-3/IKJEFT01:905-925 — background mode, INDD/OUTDD open failure after STACK"
  - "MVS/CE LAB (mvsdev.lan:8082), JOB01185 (TPUT, output lost) and JOB01189 (PUTLINE, output in SYSTSPRT) — 2026-09-24"
verified_on: 2026-09-24
applies_to: [rexx370]
tags: [tput, svc93, ikt0009c, putline, tmp, ikjeft01, background, batch, systsprt, ascbtsb, tsb, silent-failure]
related: [MVS-TSO-0002, PM-2026-004]
---

## Claim

In a TMP running as a batch job (`EXEC PGM=IKJEFT01`), **TPUT writes nothing,
anywhere, and does not report it.** The line is not in `SYSTSPRT`, not in
`SYSPRINT`, not in any DD of the job. `[tested: JOB01185]`

The belief it replaces: "in TSO background, TSO routes TPUT output to
SYSTSPRT". rexx370 carried that sentence in its source until #228. On MVS 3.8j it
is false. `[tested]` Whether TSO/E on z/OS behaves differently was not checked.

## Why — SVC 93

The SVC 93 entry (TGET/TPUT, `IKT0009C`) loads the ASCB's TSB pointer and leaves
early when it is zero: `[source: IKT0009C]`

```asm
A00005A  SLR   R7,R7
         L     R3,16                 CVT
         C     R7,1012(,R3)          no TCAS at all?
         BE    A000236
         L     R8,548                PSAAOLD -> ASCB
         L     R9,60(,R8)            ASCB+X'3C' = ASCBTSB
         ...
A0000DE  LTR   R9,R9                 no TSB?
         BE    A000236
         ...
A000236  LR    R1,R2
         L     R14,108(,R5)
         B     A000058               A000058: BR R14
```

`A000236` does no work and **does not set R15**. The "return code" the caller
sees is whatever R15 held before the SVC. A caller that checks it may see 0.
`[source: IKT0009C]`

A batch TMP address space has no TSB, so every TPUT from it takes this exit.
`[inferred: from the branch above + the measured loss]`

## Where background output does go

In background mode the TMP issues STACK with `INDD=SYSTSIN` / `OUTDD=SYSTSPRT`
(it reports an INDD/OUTDD open failure right after the STACK). `[source:
IKJEFT01]` PUTLINE writes through that stack, so PUTLINE output lands in
`SYSTSPRT`. `[tested: JOB01189]` TPUT bypasses the stack. See `MVS-TSO-0002` for
building the PUTLINE call without a CPPL.

The TMP's own command echo in `SYSTSPRT` (`CALL '…'`, `END`) is a quick
control: it shows that the stack is in place, whatever your own routine does.
`[tested]`

## Foreground is fine

In a TSO foreground session TPUT reaches the terminal. Lines longer than the
screen wrap at 80 columns with nothing lost. `[tested: s3270 session, user
MVSCE01, MVSCE-LAB, 2026-09-24]` So a routine tested only in the foreground
looks correct.

## How to recognise it

- The routine returns 0 (or a leftover value) and every test that checks RCs
  or pointers passes.
- The output is simply absent. **Check the output itself**, for example by
  grepping the job's spool for the text, never the RC.

## Grep hint

The reconstructed `mvs38src/src/IKJEFT01.ASM` does not show `SYSTSPRT` in clear
text. Grep the original jay listing (`MVSSRC.SYM1-3/IKJEFT01`) instead.
