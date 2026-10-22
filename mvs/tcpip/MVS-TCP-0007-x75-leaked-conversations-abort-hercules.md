---
id: MVS-TCP-0007
title: A guest that leaks X'75' conversations aborts the Hercules process after about 467 of them -- before the slot table is full
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #162 and PR #657 (merged 2026-10-19; probe and numbers in the PR body); probe test/mvs/tst75slt.c (header: mechanism, warning), jcl/recv75slt.jcl, jcl/tst75slt.jcl"
  - "MVS 3.8j (MVS/CE) in a throwaway local container; emulator SDL Hyperion at 16e62c4 (tcpip.c and tcpip.h identical to a742398); probe run on 2026-10-19"
  - "hyperion tcpip.c (find_slot, lar_tcpip, case 11 RECV) and x75.c at a742398; read 2026-10-22"
verified_on: 2026-10-19
applies_to: [libc370, ftpd, httpd, mvsmf]
tags: [hercules, x75, map32, find-slot, slot-leak, heap-corruption, sigabrt, tst75slt, emulator-crash]
related: [MVS-TCP-0001]
---

## The claim

If a guest starts X'75' calls and never issues the second instruction of the
pair, each such call leaves one conversation allocated in the emulator, using
two `map32` slots. After about 467 leaked conversations (about 934 slots) the
**Hercules process aborts** with a glibc heap-corruption assertion and every
guest is gone. `[tested]`

```
Fatal glibc error: malloc.c:2601 (sysmalloc): assertion failed ...
Aborted   hercules -f ...
```

The abort happens **before** the 1024-entry table is full. The failure that
the source suggests (`find_slot()` aliasing at `Ccom-1`, below) was therefore
never observed. The cause of the heap corruption is **not known**; it was not
investigated. `[tested]` for the abort, nothing is claimed for the cause.

## Mechanism of the leak

One guest call is two instructions (MVS-TCP-0001). The first one allocates a
`talk` and its input buffer, each registered in `map32[]` through
`find_slot()` (two slots), and then runs the host call. Only the second
instruction (direction 1) frees the talk, the buffers and the slots. The
emulator cannot know that the guest will not come back. A task that is
abended between the two instructions leaks the same way. `[source: tcpip.c
lar_tcpip @ a742398]` The abend case is the field scenario named in
libc370#162; the probe reproduces the same emulator-side state directly, and
the abend path itself was not run. `[inferred]`

## The table limit in the source

```c
while ((((signed) map32[i]) != -1) && (i < Ccom-1)) i++;
map32[i] = address;              /* assigned even when no entry is free */
```

When 0 ... `Ccom`-2 are used the walk stops at `Ccom-1` (1023) and assigns
there anyway, so later conversations overwrite each other's entry.
`map32[R14]` is how the second instruction finds the buffers of a transfer,
so an aliased entry would resolve to another conversation's structure.
`[source: find_slot @ a742398]` This was **not** reached from the guest (see
above), so what an aliased transfer does is untested.

## Evidence

The probe issues only the first instruction of a RECV on a freshly opened,
never-connected socket. The host `select()` times out at once and RECV returns
-2 before it allocates an output buffer, so exactly the talk and the input
buffer leak per call, no data moves and nothing blocks. R14 after the call is
the slot `find_slot()` gave the talk. `[source]` for why it is two slots;
`[tested]` for the following.

- Slot = 2 x (call - 1): **call 1 got slot 0, call 467 got slot 932**.
- The Hercules process aborted at about 467 leaks (about 934 slots).
- It reproduced across runs and with both high and minimal WTO volume, so it
  is the leak and not the logging.

Each probe step writes a WTO trail, because Hercules block-buffers its
console log and the tail is lost when the process dies. The results were read
from the container's console log, not from the job output (mvsMF is gone
with the emulator).

## What is not shown

- Normal open and close do not leak: a 26.7-hour soak with a probe opening
  four socket pairs per hour moved the emulator's open descriptor count only
  when unrelated HTTP traffic arrived, about 120 pairs and 120 talks
  without a leak. `[tested, per libc370#162; not repeated at ingest]`
- Whether any production program reaches the leak path was not measured.
- The slot limit is a compile-time constant (`Ccom` = 1024, `tcpip.h`); the
  empirical count (about 934 slots) is below it.
- Run the probe only in a disposable container: the table is shared by every
  address space and the abort takes the emulator down.
