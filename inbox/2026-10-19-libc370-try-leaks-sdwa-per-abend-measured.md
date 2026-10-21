# libc370 try() before 2.23.0: each abend that is retried leaves the SDWA allocated (measured, oftpd#13; fixed in 2.23.0)

Source: oftpd session, 2026-10-19; ticket mvslovers/oftpd#13 (comment of
2026-10-19 with the full table). Platform: MVS 3.8j, MVS/CE in a throwaway
container (`mvsce-target`, local, Apple `container`). libc370 2.21.0, cc370 1.6.3.

## Finding

libc370's `try()` (`src/mvs/recovery/@@@try.c`, reached through `try()` ->
`___try()`; twin `@@try.c` / `__try`) recovers an abend with an ESTAE whose exit
`failed()` requests a retry with libc370's `SETRP(sdwa,4,retry,1)`. That macro
sets `SDWARCDE`, `SDWARTYA` and `SDWAUPRG` (`include/mvs/recovery.h`) and **never
`SDWAFREE`**. IBM's `SETRP` macro sets this bit only for `FRESDWA=YES`
(`OI SDWAACF2-SDWA(1),SDWAFREE`, SETRP.asm in mvs38-ibmsrc; IHASDWA:
`SDWAFREE EQU X'04' ON,SDWA/RTCA TO BE FREED PRIOR TO RETRY. ONLY VALID FOR ESTA
EXITS`). Without it the retry routine owns the SDWA, and libc370's retry path does
not free it either. So, **before libc370 2.23.0, every abend caught by try() in a task that lives on
cost about 520 bytes of the region, until the address space ended**.

## Measurement

OFTPD (an STC whose OFTP sessions run under `try()` in subtasks) received one file
per session. A debug trigger stored to address 0 (S0C4) in the first data write, so
the session abended and was retried. The instrument summed the free storage of the
region: largest piece, then the next, to 8 bytes, down to 64-byte pieces, using a
bare `GETMAIN RC` + `FREEMAIN`, all freed again. It was calibrated by holding a
`malloc(102400)`: the total fell by 102,464 (102,400 + 8-byte header, rounded to 64)
and came back to the same byte.

| Run | Sessions | Total free per session |
|---|---|---|
| normal sessions | 50 | 0 (identical to the byte after 1 and after 50) |
| abends, LRECL 32760, libc370's try() | 50 | about 520 bytes (5,200-5,280 per 10); free pieces +0.9 per abend |
| abends, LRECL 8000, libc370's try() | 50 | about 520 bytes (independent of the record buffer) |
| abends, LRECL 32760, the same @@@try.c with `sdwa->SDWAACF2 \|= SDWAFREE;` before SETRP | 51 | 0; final reading equal to the start, byte for byte |

All 152 abends were confirmed on the console (`OFTP203I ... ENDED BY ABEND`, counted
in the JES-prefixed lines). The SDWA's own length (`SDWALNTH`) was not read; about
520 bytes is what the region lost.

## Side results

- A "largest free block" probe at 4 KB steps overstates a leak: in the same runs it
  fell by about 34 KB per abend when the real loss was 33,288 bytes (buffer + SDWA),
  and on dev1 earlier by 38 KB. Measure the total to tell a leak from fragmentation.
- libc370's `getmain()` writes a WTO on every failed request, so any probing loop
  built on it floods the console; probe with a bare `GETMAIN RC`.
- An ended cthread subtask keeps its TCB and 64 KB stack until it is DETACHed;
  readings right after a session include it (65,664 bytes).

## Fix: libc370 2.23.0 (mvslovers/libc370#640)

Proposed from the measurement: set `SDWAFREE` in `failed()` before `SETRP`, in
`@@@try.c` and `@@try.c`. With `SDWAUPRG` the retry registers come from `SDWASR00`,
which RTM copies before it frees the SDWA; the measured run with the bit set retried
correctly 51 times.

libc370 **2.23.0** (released 2026-10-19, tag v2.23.0 on b452cdb) contains the fix: `try()`
frees the SDWA of every abend it recovers. **Use 2.23.0 or later in any long-running
task that recovers abends with `try()`.** The same release also changed `try()`'s
return when it cannot set up its ESTAE, from +1 to -1 (libc370#476). A caller that
tests `< 0` for "no recovery" is correct with 2.23.0. Before 2.23.0 this case returned
+1, which a caller could not tell from an abend code.

### Confirmed by measurement, 2026-10-20 (MVS time 2026-10-19)

The same instrument and series, OFTPD debug build against libc370 2.23.0 (cc370 1.6.3),
fresh MVS/CE container `oftp13c` (local, Apple `container`):

| Reading | Total free in the region (bytes) |
|---|---|
| start | 7,739,416 (12 pieces) |
| holding `malloc(102400)` | 7,636,952 (−102,464, as before) |
| released | 7,739,416 |
| after normal sessions 1, 10, 20, 30, 40, 50 | 7,673,744 each |
| after abend sessions 1, 10, 20, 30, 40, 50 (LRECL 32760, S0C4) | 7,673,744 each |
| end, ended subtask detached | 7,739,416 |

The console showed 51 `OFTP203I ... ENDED BY ABEND S0C4` and 51 `OFTP209E` (one trial
call plus the 50) and 50 normal ends. These were counted in the JES-prefixed lines
(`FFFF hh.mm.ss STC ...`); the Hercules "/ " lines dropped some again. There was no
`OFTP216E`, `OFTP208W` or `OFTP096W`. Loss per abend: **0 bytes** (was about 520 with
2.21.0). While sessions ran, the total stood 65,672 bytes below the idle value: that is
the ended subtask's TCB and 64 KB stack, kept until DETACH (see the side results). The
free-piece count varied between 15 and 16 and no longer grew with each abend.
oftpd took 2.23.0 as its floor (oftpd PR #43, issue #13 closed).
