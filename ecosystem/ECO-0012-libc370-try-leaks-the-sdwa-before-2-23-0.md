---
id: ECO-0012
title: libc370 try() before 2.23.0 leaves the SDWA allocated — about 520 bytes of the region per recovered abend, until the address space ends
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/oftpd#13, comment of 2026-10-19: the full measurement table, one MVS/CE container (throwaway, local), libc370 2.21.0, cc370 1.6.3, OFTPD debug build"
  - "A second series, 2026-10-19 (MVS time), fresh MVS/CE container, OFTPD debug build against libc370 2.23.0 — quoted in mvslovers/oftpd PR #43 (merged, closes #13) and in a comment on mvslovers/libc370#640"
  - "libc370 v2.21.0 and v2.23.0: src/mvs/recovery/@@@try.c, failed() and ___try(); @@try.c (twin, __try()); include/mvs/recovery.h:26 (SETRP macro); include/ibm/mvs/ihasdwa.h:467 (SDWAFREE)"
  - "libc370 release notes v2.23.0 (2026-10-19, tag v2.23.0 = b452cdb): #640 and #476; the library's own measurement 'region after 50 abends recovered with try(): 25,640 bytes fewer (2.22.0), unchanged (2.23.0)'"
verified_on: 2026-10-19
applies_to: [libc370, oftpd, httpd, ftpd, ufsd]
tags: [libc370, try, estae, sdwa, sdwafree, setrp, retry, leak, region, abend, storage]
related: [ECO-0015, MVS-SUP-0001]
---

## The claims

1. **Before libc370 2.23.0, every abend caught by `try()` in a task that lives on
   costs about 520 bytes of the region, until the address space ends.** A server
   whose connections run under `try()` loses that much per abended connection. `[tested]`
   on libc370 2.21.0.
2. **The cause is that `try()`'s recovery exit never asks RTM to free the SDWA.**
   `failed()` in `src/mvs/recovery/@@@try.c` (reached through `try()` → `___try()`;
   the twin `@@try.c` / `__try()` has the same line) requests the retry with
   `SETRP(sdwa,4,retry,1)`. libc370's `SETRP` macro (`include/mvs/recovery.h:26`) sets
   `SDWARCDE`, `SDWARTYA` and, with the register flag, `SDWAUPRG`, and **never**
   `SDWAFREE`. Without it the retry routine owns the SDWA, and libc370's retry path
   does not free it. `[source: libc370 v2.21.0]` The general rule is **MVS-SUP-0001**.
3. **libc370 2.23.0 sets `SDWAFREE` in `failed()` before `SETRP`** (libc370#640), in
   both copies. The retry registers still come from `SDWASR00`; with the bit set the
   retry worked 51 times of 51. `[source: libc370 v2.23.0]` `[tested]`
4. **2.23.0 also changes `try()`'s return when it cannot set up its ESTAE**, from +1 to
   -1 (libc370#476). The same applies to `__try()`, `__linkt()` and `__linkds()`. Before
   2.23.0 the +1 could not be told from user abend 1. A caller that tests `< 0` for
   "no recovery" is correct on 2.23.0. `[source]` (v2.23.0 `@@@try.c`, where the
   positive code is negated, and the release notes.) The cases are: no task anchor,
   or all ten `estae()` levels in use.

Use 2.23.0 or later in any long-running task that recovers abends with `try()`.
oftpd took 2.23.0 as its floor (oftpd PR #43, issue #13 closed).

## The evidence

OFTPD is a started task whose OFTP connections run under `try()` in subtasks. A debug
trigger stored to address 0 (S0C4) in the first data write of a connection, so the connection
abended and was retried. The instrument summed the region's free storage: take the
largest free piece, then the next, to 8 bytes, down to 64-byte pieces, using a bare
`GETMAIN RC` + `FREEMAIN`, everything freed again. Calibration: holding a
`malloc(102400)` lowered the total by 102,464 (102,400 + 8-byte header, rounded to 64)
and it came back to the same byte.

**libc370 2.21.0** (oftpd#13):

| Run | Connections | Total free per connection |
|---|---|---|
| normal connections | 50 | 0 (identical to the byte after 1 and after 50) |
| abends, LRECL 32760, libc370's `try()` | 50 | about 520 bytes (5,200-5,280 per 10); free pieces +0.9 per abend |
| abends, LRECL 8000, libc370's `try()` | 50 | about 520 bytes (independent of the record buffer) |
| abends, LRECL 32760, the same `@@@try.c` with `sdwa->SDWAACF2 \|= SDWAFREE;` before `SETRP` | 51 | 0; final reading equal to the start, byte for byte |
| abends, LRECL 32760, the old state of OFTPD (record buffer not freed), libc370's `try()` | 21 | 33,288 bytes = 32,768 (the buffer) + 520 |

All 152 abends were confirmed on the console (`OFTP203I ... ENDED BY ABEND`). The
SDWA's own length (`SDWALNTH`) was not read; about 520 bytes is what the region lost.
The library's own test program measured 25,640 bytes after 50 recovered abends on
2.22.0 (about 513 per abend) and none on 2.23.0 (release notes).

**libc370 2.23.0**, same instrument, fresh container, OFTPD debug build:

| Reading | Total free in the region (bytes) |
|---|---|
| start | 7,739,416 (12 pieces) |
| holding `malloc(102400)` | 7,636,952 (−102,464, as before) |
| released | 7,739,416 |
| after normal connections 1, 10, 20, 30, 40, 50 | 7,673,744 each |
| after abend connections 1, 10, 20, 30, 40, 50 (LRECL 32760, S0C4) | 7,673,744 each |
| end, ended subtask detached | 7,739,416 |

The console showed 51 `OFTP203I ... ENDED BY ABEND S0C4`, 51 `OFTP209E` (one trial call
plus the 50) and 50 normal ends, no `OFTP216E`, `OFTP208W` or `OFTP096W`. Loss per
abend: **0 bytes** (about 520 with 2.21.0). The free-piece count varied between 15 and
16 and no longer grew with each abend.

## Side results of the same measurement `[tested]`

- A "largest free block" probe at 4 KB steps **overstates** a leak: the largest block
  fell by about 34 KB per abend (38 KB on an earlier system) when the real loss was
  33,288 bytes. Where a leaked block lands in the free regions depends on the layout.
  Measure the **total** to tell a leak from fragmentation.
- libc370's `getmain()` writes a WTO on every failed request, so a probing loop built
  on it floods the console; probe with a bare `GETMAIN RC`.
- An ended cthread subtask keeps its TCB and 64 KB stack until it is DETACHed. Readings
  taken right after a connection include it (65,664 to 65,672 bytes below the idle value).
