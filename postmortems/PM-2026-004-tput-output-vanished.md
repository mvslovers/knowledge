---
id: PM-2026-004
title: SAY output vanished in the batch TMP — all tests green, because they checked pointers and RCs, not the output
status: tested
platform: [mvs38j]
sources:
  - "rexx370 issue #228, PR #229 (commit b9ce45c) — the fix and its measurements"
  - "MVS/CE LAB (mvsdev.lan:8082): JOB01181, JOB01185 (output lost), JOB01189 (fixed), JOB01192 (full suite) — 2026-09-24"
  - "mvs38src/src/IKT0009C.ASM; MVSSRC/mvs38_sources/jay/MVSSRC.SYM1-3/IKJEFT01"
verified_on: 2026-09-24
applies_to: [rexx370]
tags: [postmortem, tput, putline, tmp, background, systsprt, silent-failure, test-design, modnamet]
related: [MVS-TSO-0001, MVS-TSO-0002]
---

## Symptom

rexx370's new TSO I/O routine (IRXIOTSO, WP-33-TSO) wrote SAY output through TPUT.
On MVS, TSTIOTSO passed 12/12 in the TSO leg (a batch `IKJEFT01` step), and the
three SAY calls returned 0. The SAY text itself was **nowhere in the job's spool**:
`SYSTSPRT` held only the TMP's echo:

```
--- SYSTSPRT ---
 CALL 'IBMUSER.REXX370.V1R0M0D.TESTLIB(TSTIOTSO)' '1'
END
```

## Environment

MVS/CE 3.0.0 on Hercules 4.10 (MVSCE-LAB). The TMP (`IKJEFT01`) is patched to
initialise a REXX environment at start (`IKJ56942I`). rexx370 at commit 084be75
plus the uncommitted WP-33 work.

## Wrong turns

1. **Trusting the green test.** TSTIOTSO asserted the wiring: the MODNAMET names
   IRXIOTSO, the active slot is not the default, the RC is 0. It could not see the
   output. The test had been written to catch "a broken wiring leaves every RC at
   zero", and it fell into exactly that hole one level further down.
2. **The first MVS run looked like a pass for the wrong reason.** In JOB01181 the
   runtime LINKLIB was stale and IRXIOTSO was missing, so the LOAD failed and the
   stdio routine ran. The SAY lines *did* appear, under `SYSPRINT`. Only after a
   deploy did IRXIOTSO run for real, and the lines disappeared (JOB01185).
3. **Looking for the output in libc370's DD.** stdio output lands in `SYSPRINT`
   because the libc370 runtime opens stdout there. That is a C-runtime choice,
   not TSO's. `SYSTSPRT` belongs to the TMP.
4. **Grepping the reconstructed source.** `mvs38src/src/IKJEFT01.ASM` does not
   contain `SYSTSPRT` in clear text, and neither did Dave Kreiss' MVSBLD tree
   searched the same way. That briefly suggested that batch TSO support is not in
   the IBM code at all. It is: the original jay listing has `CL8'SYSTSPRT'` at
   line 3100.
5. **The foreground test collided with a real session.** A 3270 device keeps its
   TSO session after the TCP connection drops. The first scripted connection
   landed on a device with a live session and typed into it. The fix was a
   driver that types only into a fresh `TSO Logon ===>` screen, and a separate
   user ID (MVSCE01), because IBMUSER was in use (`IKJ56425I`).

## Root cause

TPUT does nothing in an address space without a TSB. SVC 93 (`IKT0009C`)
branches to a bare return when `ASCBTSB` is zero, and does not set R15. The
background TMP writes through STACK/PUTLINE to `SYSTSPRT`. See `MVS-TSO-0001`.

## Fix

IRXIOTSO writes through PUTLINE. The IOPL is built from LWA+24 → PSCB+52 (UPT)
and LWA+32 (ECT), see `MVS-TSO-0002`. rexx370 #228 / PR #229, commit b9ce45c.
Measured on the output: the SAY lines appear in `SYSTSPRT` (JOB01189) and on the
foreground terminal (s3270 session).

## Extracted

- `MVS-TSO-0001` — TPUT does nothing in the background TMP.
- `MVS-TSO-0002` — how to call PUTLINE without a CPPL.
- The lesson for test design: **when a test cannot read the output, it has not
  tested the output.** Read the spool, or drive a terminal.
