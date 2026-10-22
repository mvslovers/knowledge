---
id: ECO-0013
title: libc370 2.15.0 to 2.24.0 — an authorized program's first fopen() inside a key-0 window puts the file table in key-0 storage, and the next fopen() in its own key abends S0C4
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/ufsd#107 (closed 2026-10-20) and mvslovers/libc370#693 (closed 2026-10-20): the report and bisect, measured in a throwaway MVS/CE container as started tasks (STC00032 to STC00051, container-local), UFSD main d10d40c plus debug code, libc370 built privately per tag"
  - "mvslovers/ufsd PR #108 (merged 2026-10-20): the workaround in ufsd_ssi_load()"
  - "libc370 v2.24.1 release notes (2026-10-20), the 'Fixed' table: the same test program linked with 2.24.0 and 2.24.1, APF, key 8"
  - "libc370 v2.24.0 and v2.24.1: src/stdio/@@fpopn.c (arrayadd under tskey() from 2.24.1), src/ext/array/@@aradd.c, src/mvs/link/@@loadhi.c, src/internal/tskey.h"
  - "mvslovers/libc370#564 and the v2.15.0 release (2026-10-16): the lazy start-up"
verified_on: 2026-10-20
applies_to: [libc370, ufsd]
tags: [libc370, fopen, grtfile, lazy-start-up, stdlazy, key-0, psw-key, super, loadhi, s0c4, s30a, sysenv, authorized, apf]
related: [ECO-0003, ECO-0006, MVS-SUP-0002]
---

## The claims

1. **On libc370 2.15.0 to 2.24.0, a program that runs in a non-zero PSW key (for
   example an AC(1) started task in key 8) and makes its first `fopen()` inside a
   `__super(PSWKEY0, ...)` window ends with S0C4 at its next `fopen()` in its own
   key.** `[tested]` The release notes give the same for `__loadhi()`, which opens a
   file inside such a window itself.
2. **The cause is lazy start-up.** From 2.15.0 (libc370#564, `GRTFLAG1_STDLAZY` 0x20)
   the file table `grt->grtfile` is NULL at start; through 2.14.0 the start created a
   table with three slots (stdin, stdout, stderr) in the program's key. The first
   `fopen()` calls `arrayadd(&grt->grtfile, fp)` (`@@fpopn.c`); `arrayadd()` makes the
   table with `calloc()`, i.e. a GETMAIN under the caller's current PSW key. Inside the
   window that is **key-0 storage**. `fclose()` empties the table (count 0) and leaves
   it. `[source: libc370 v2.24.0]`
3. **The abend** comes when the program, back in key 8, makes its next `fopen()`:
   `arrayadd()` stores the new `FILE *` into the key-0 table. UFSD showed S0C4 (INTC
   0004, PSW key 8) at `ST 6,0(3,4)`, offset X'168' in `@@aradd` (PSW address X'16C').
   `[tested]`
4. **Other state created on first use is affected the same way.** From 2.16.0 the
   `SYSENV` environment is lazy too. On 2.24.0: `setenv()` of a new name after the first
   `getenv()` inside the window S0C4; `setenv()` of a name the `SYSENV` DD set S30A;
   the first `fputs()` to `stdout` inside the window, then one in key 8, S0C4.
   `[tested]` (release-note table)
5. **Growing the table does the same in a window, in earlier releases too:** the 21st
   `fopen()` inside the window with 20 files open abends S30A on 2.24.0. `[tested]`
   (release-note table)
6. **Fixed in libc370 2.24.1** (libc370#693, release of 2026-10-20). The table, the
   standard streams and the `SYSENV` environment are created in the task's own key
   even in a key-0 window: `@@fpopn.c` brackets `arrayadd()` with `tskey()` /
   `tsrestore()`, which switch a supervisor-state caller to the TCB's key (`TCBPKF`)
   with SPKA and back. The cost is one authorization test per `fopen()`.
   `[source: libc370 v2.24.1]` `[tested]` (all seven rows below). The workaround is
   not needed from 2.24.1.

## The evidence

**UFSD start, libc370 built per tag, same container, same JCL** (UFSD `d10d40c` plus
debug code), started task, key 8, load module AC(1). In `ufsd_ssi_load()` the
`__loadhi()` call runs in the key-0 window and does `fopen("DD:STEPLIB(member)","rb")`
and `fclose()`; `ufsd_cfg_read()` then opens `DD:UFSDPRM` in key 8.

| libc370 | UFSD start |
|---|---|
| 2.10.3 | READY |
| 2.12.1 | READY |
| 2.14.0 | READY |
| 2.15.0 | S0C4 |
| 2.22.0 | S0C4 |
| 2.23.0 | S0C4 |
| 2.24.0 | S0C4 |

2.16.0 to 2.21.0 were not measured; 2.15.0 is the first lazy release. `[tested]`

**Dump reading, 2.24.0 run.** SYSUDUMP has neither module storage nor the program's
registers, so the failing instruction was found from the module base (CDE entry
address minus the entry offset in the `ld370 --map`) and a disassembly of `@@aradd.o`
(section length X'1D0', as in the map). `grt` was at X'BBC90' (key 8, heap), the empty
`grtfile` table at X'FC384' (key 0), and `calloc` blocks from key-8 code at X'FD448',
writable. `[tested]`

**Fixed, same test program linked with 2.24.0 and 2.24.1**, APF, key 8
(release notes of v2.24.1, measured on MVS):

| | 2.24.0 | 2.24.1 |
|---|---|---|
| `fopen()` in key 8 after a first `fopen()`/`fclose()` inside a key-0 window | S0C4 | opens |
| `setenv()` of a new name after the first `getenv()` inside the window | S0C4 | works |
| `setenv()` of a name the `SYSENV` DD set | S30A | works |
| `fputs()` to `stdout` in key 8 after its first use inside the window | S0C4 | writes |
| 21st `fopen()` inside the window, 20 files open | S30A | opens |
| server start that loads a module with `__loadhi()`, then opens its parameter file | S0C4 | starts |

## The workaround for 2.15.0 to 2.24.0 `[tested]` on 2.23.0 and 2.24.0

Before the first key-0 window, in the program's own key, open and close a DD so the
table is made in key 8:

```c
{ FILE *wf = fopen("DD:STEPLIB", "rb"); if (wf) fclose(wf); }
```

UFSD put it at the top of `ufsd_ssi_load()` (ufsd PR #108). Any other DD that is
allocated will do.

## What stays true on every release

Storage a program gets with `malloc()` or `fopen()` **inside** a key-0 window is key-0
storage. Free it, or close the file, inside the window (see **MVS-SUP-0002**). The
2.24.1 fix is about what the library creates for itself.

## Not examined

- Other AC(1) products that load with `__loadhi()` and run on 2.15.0 to 2.24.0 were not
  tested; the release notes name the pattern, not the products.
- The time zone, the third item #564 made lazy, was not tested for the same pattern.
- This note covers a program that runs in a non-zero key. A task already in key 0 is not
  affected (`tskey()` does nothing for it).

The start-up background (the GRT, the lazy streams) is in **ECO-0003** and **ECO-0006**.
