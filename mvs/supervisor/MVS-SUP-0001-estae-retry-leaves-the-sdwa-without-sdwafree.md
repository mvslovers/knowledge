---
id: MVS-SUP-0001
title: An ESTAE exit that retries leaves the SDWA allocated unless it sets SDWAFREE — SETRP does not do it by itself
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/oftpd#13, comment of 2026-10-19: same code, 51 recovered abends with and without sdwa->SDWAACF2 |= SDWAFREE, region free storage summed to the byte (MVS/CE container, throwaway, local)"
  - "libc370 v2.23.0 include/ibm/mvs/ihasdwa.h:467 — 'SDWAFREE 0x04 ... ON,SDWA/RTCA TO BE FREED PRIOR TO RETRY. ONLY VALID FOR ESTA EXITS' (SDWAACF2 bit)"
  - "libc370 v2.21.0 and v2.23.0 src/mvs/recovery/@@@try.c, failed(); mvslovers/libc370#640"
verified_on: 2026-10-19
applies_to: [libc370]
tags: [estae, sdwa, sdwafree, setrp, retry, fresdwa, rtm, recovery, storage-leak]
related: [ECO-0012]
---

## The claim

An ESTAE exit that asks for a retry (`SETRP RC=4,RETADDR=...`) **does not get the SDWA
freed for it**. Unless the exit sets the `SDWAFREE` bit in `SDWAACF2` (what
`SETRP ...,FRESDWA=YES` does), the SDWA stays allocated after the retry and the
retry routine owns it. Each recovered abend then loses the SDWA's storage for the
rest of the task's life. `[tested]`

Measured size on MVS 3.8j: **about 520 bytes per recovered abend**. The SDWA's own
length (`SDWALNTH`) was not read; 520 is what the region lost.

## The evidence

The A/B is one exit, one program, one container, 51 recovered abends of the same S0C4;
the only difference is one statement before `SETRP`. The region's total free storage
was summed down to 64-byte pieces (calibrated against a held `malloc(102400)`: −102,464,
back to the byte on release).

| Exit | Total free per abend |
|---|---|
| `SETRP(sdwa,4,retry,1)` only | about 520 bytes lost (5,200-5,280 per 10 abends) |
| `sdwa->SDWAACF2 \|= SDWAFREE;` then `SETRP(sdwa,4,retry,1)` | 0; final reading equal to the start, byte for byte |

With the bit set the retry still worked 51 times of 51, and the retry registers
(`SDWAUPRG`, taken from `SDWASR00`) were correct. So RTM loads them before it frees
the SDWA. `[tested]` The full table and the libc370 consequence are in **ECO-0012**.

## What the header says

`include/ibm/mvs/ihasdwa.h:467` in libc370 (its copy of IBM's IHASDWA) reads:

```
SDWAFREE    0x04   ... ON,SDWA/RTCA TO BE FREED PRIOR TO RETRY. ONLY VALID FOR ESTA EXITS
```

`[source: libc370 v2.23.0 ihasdwa.h:467]`

## Not re-read

IBM's `SETRP` macro setting this bit only for `FRESDWA=YES` (`OI SDWAACF2-SDWA(1),SDWAFREE`,
SETRP.asm) is stated in the inbox note and in the libc370 issue; the listing was not
re-read at ingest. `[inferred]` Whether the SDWA is freed by RTM at the retry, or only
made freeable, is likewise not derived from a listing; the measurement shows the
region does not shrink when the bit is set.

libc370's own `SETRP` macro (`include/mvs/recovery.h:26`) sets `SDWARCDE`, `SDWARTYA`
and `SDWAUPRG` only. `[source: libc370 v2.23.0]` An exit written with that macro
inherits the leak.
