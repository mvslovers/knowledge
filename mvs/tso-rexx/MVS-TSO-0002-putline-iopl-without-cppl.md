---
id: MVS-TSO-0002
title: Calling PUTLINE without a CPPL — the UPT via LWA+24 → PSCB+52, the ECT via LWA+32
status: tested
platform: [mvs38j]
sources:
  - "SYS1.MACLIB PUTLINE (MVS/CE 2.1.4 target) — PTPB control bytes, CVT+444 test, LINK EP=IKJPUTL"
  - "SYS1.MACLIB IKJIOPL, IKJPTPB, IKJPSCB, IKJCPPL; MVSSRC.SYM1-1/IKJEFLWA — layouts"
  - "IBM sources (jay MVSSRC): 342x 'PSCBUPT EQU PSCB+52', 15x 'LWAPSCB EQU LWA+24', 15x 'LWAPECT EQU LWA+32'"
  - "rexx370 asm/putlin.asm, src/irx#tsio.c (#228 / PR #229) — working implementation"
  - "MVS/CE LAB, JOB01189 (background) and s3270 session as MVSCE01 (foreground) — 2026-09-24"
verified_on: 2026-09-24
applies_to: [rexx370]
tags: [putline, ikjputl, iopl, ptpb, upt, pscb, lwa, ect, cppl, cvtputl, replaceable-routine, tso]
related: [MVS-TSO-0001, PM-2026-004]
---

## The problem

PUTLINE takes an IOPL containing the UPT, the ECT, an ECB and a PTPB. A command
processor gets the UPT and the ECT from its CPPL. A routine that is **called by
something else**, such as a REXX replaceable I/O routine, never sees a CPPL.
The ECT is easy to reach; the UPT is not in the ECT. `[manual: IKJECT, IKJIOPL]`

## The chain

```
PSA   +X'224' (PSAAOLD)  -> ASCB
ASCB  +X'6C'  (ASCBASXB) -> ASXB
ASXB  +X'14'  (ASXBLWA)  -> LWA
LWA   +24     (LWAPSCB)  -> PSCB  --> PSCB +52 (PSCBUPT) -> UPT
LWA   +32     (LWAPECT)  -> ECT
```

The offsets `LWA+24`, `LWA+32` and `PSCB+52` appear as EQUs throughout the IBM
sources (15×, 15× and 342×). `[source]` Counted from the `IKJPSCB` DS statements
the offset is also 52. That count must include the reserved `DS 2F` after
`PSCBSOUT`; skipping it gives 44. `[manual: IKJPSCB]`

The background TMP builds its own UPT, PSCB and LWA (IKJEFT01, "GET SPACE (IN
BACKGROUND MODE) FOR UPT, PSCB, RLGB"), so the chain holds in the foreground and in
the background. `[source: IKJEFT01]` `[tested: both]`

## The parameter block

For `OUTPUT=(line,TERM,SINGLE,DATA)` the macro sets PTPB byte 0 = X'30' (DATA +
SINGLE) and byte 1 = X'00' (TERM), and stores the line address at PTPB+4
(`PTPBOPUT`). `[manual: PUTLINE macro, .E7O]` The data line is a halfword LL that
counts itself, a halfword 0, and then the text.

## The call

The macro without `ENTRY=`: `[manual: PUTLINE macro, .E12]`

```asm
         L      15,16(0,0)          CVT
         TM     444(15),B'10000000' IKJPUTL resident?
         BNO    LINKIT
         L      15,444(0,15)        CVTPUTL
         BALR   14,15
         B      DONE
LINKIT   LINK   EP=IKJPUTL
```

R1 points at the IOPL itself, not at a list of addresses. IKJPUTL saves registers
into the area R13 points at, so a RENT caller has to supply that save area.
rexx370 passes it in from C. `[tested]`

## Result

The same code reaches the terminal in the foreground and `SYSTSPRT` in the
background. In the background, a 240-character line arrives as 132 + 108
characters (SYSTSPRT record width). In the foreground it wraps at 80 columns.
Nothing was lost in either case. `[tested]` A line of zero length was not
tried: rexx370 sends one blank for an empty SAY.
