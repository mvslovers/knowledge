---
id: MVS-SUP-0002
title: Storage got while the PSW key is 0 is key-0 storage — the program's own key (8) then cannot store into it, or free it
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/libc370#693 and ufsd#107, 2026-10-20: S0C4 (INTC 0004, PSW key 8) storing into a calloc block that was GETMAINed inside a key-0 window; measured in a throwaway MVS/CE container, container-local STC numbers"
  - "libc370 v2.24.1 release notes: the same test program on 2.24.0, APF, key 8 — S0C4 on a store, S30A on a free / growth"
  - "libc370 v2.24.1 src/internal/tskey.h, header comment (the library's reading of IEAVGM00 / PGTSPQE; the IBM listing was not re-read at ingest)"
verified_on: 2026-10-20
applies_to: [libc370, ufsd]
tags: [storage-key, psw-key, key-0, spka, ipk, getmain, subpool-252, s0c4, s30a, super, tcbpkf]
related: [ECO-0013]
---

## The claim

On MVS 3.8j, a program in supervisor state that sets PSW key 0 and then issues GETMAIN
for subpool 0 gets **key-0 storage**. When it returns to its own key (8 for a started
task), a store into that block is a protection exception, **S0C4**, and the library's
attempts to free or grow such a block ended **S30A**. `[tested]`

This is not special to libc370. It shows in any program that allocates in a key-0
window and keeps the pointer past it. libc370 hit it because its lazy start-up
(**ECO-0013**) allocated its file table at the first `fopen()`, wherever that happened.

## The evidence

- **S0C4 on a store.** The UFSD start-up allocated the file table with
  `calloc()` in a key-0 window (a `fopen()` from `__loadhi()`); the next `fopen()` in key 8
  stored into it and abended. In the dump the table sat at X'FC384' (key 0) while key-8
  `calloc` blocks sat at X'FD448' and were writable. `[tested]` (ECO-0013)
- **S30A on growth.** On libc370 2.24.0 the 21st `fopen()` inside the window with 20
  files open (the table grows by a new allocation) ended S30A; so did `setenv()` of a
  name the `SYSENV` DD set. `[tested]` (libc370 v2.24.1 release notes) The release
  notes do not say which instruction raised S30A, and it was not read from a dump.
- **Only the block made in the window is affected.** `calloc` blocks that key-8 code
  allocated in the same run were writable by key-8 code.

## Why (from the library's note, not re-read)

libc370's `tskey.h` states that in supervisor state with PSW key 0 GETMAIN turns subpool
0 into subpool 252, key-0 storage ("IEAVGM00, PGTSPQE: key 0 and supervisor state
both"). `[inferred]` from the libc370 source comment; the IBM listing was not re-read
at ingest. The measurement above shows the effect, not the subpool.

## What to do

1. **Release inside the window what you got inside it.** Free the block, or close the
   file, before you switch back. (libc370's `__super()` reference entry says so since
   2.24.1.)
2. **Or get the storage in the task's key**: switch the PSW key to the TCB's key before
   the GETMAIN with SPKA. libc370 does this in `tskey()` (`IPK` to read the PSW key,
   `SPKA` with the key at `TCBPKF`, X'1C' in the TCB) around the allocations it keeps
   for itself, and restores the key afterwards. `[source: libc370 v2.24.1]`
3. **A pointer that must outlive the window is a request for key-8 storage**, made in
   key 8, before the window opens (the pre-2.24.1 workaround in ECO-0013 does exactly that).
