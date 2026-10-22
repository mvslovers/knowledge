---
id: MVS-TCP-0008
title: The X'75' SELECT bound aux2 is never checked -- a hand-built value of 2048 ends the Hercules process with SIGSEGV
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #164 and PR #657 (merged 2026-10-19; probe output in the PR body); probe test/mvs/tst75bnd.c (header: mechanism, warning, how to read), jcl/recv75bnd.jcl, jcl/tst75bnd.jcl"
  - "MVS 3.8j (MVS/CE) in a throwaway local container; emulator SDL Hyperion at 16e62c4 (tcpip.c and tcpip.h identical to a742398); probe run on 2026-10-19"
  - "hyperion tcpip.c, case 17 SELECT, at a742398 and at upstream develop cc555792 (2026-10-21); libc370 src/net/dyn75/@@75selx.c at v2.25.1; read 2026-10-22"
verified_on: 2026-10-19
applies_to: [libc370]
tags: [hercules, x75, select, aux2, maxsock, ccom-han, out-of-bounds, sigsegv, tst75bnd, emulator-crash]
related: [MVS-TCP-0001, MVS-TCP-0002]
---

## The claim

SELECT takes `aux2` (the guest's `maxsock`) from a register and uses it as a
loop bound over `Ccom_han[1024]` without comparing it to `Ccom`. A guest that
builds the parameter list by hand and passes a large `aux2` makes the emulator
read beyond the array; at 2048 it ends the **whole Hercules process** with
SIGSEGV. `[tested]` No libc370 wrapper passes such a value on its own.

## Evidence

The probe builds the parameter list through the low-level `__75()` entry:
subcode 0 (Start), then subcode 5 (Read Outputs) with a growing `aux2`, then
subcode 8 (Finish). After each value it opens and closes an ordinary socket
to see whether the emulator is alive. The legitimate socket number handed out
was 3. `[tested]`

```
+TST75BND FLUSH aux2=8 rc=0 alive=Y
+TST75BND FLUSH aux2=1025 rc=0 alive=Y
+TST75BND FLUSH aux2=1032 rc=0 alive=Y
Hercules has crashed! (Segmentation fault)      exit code 139 (signal 11)
```

- 8, 1025 and 1032 returned rc 0 and the emulator lived: a few entries past
  the 1024-entry array still land in mapped memory.
- 2048 crashed the emulator: the loop reads about 4 KB past the array into an
  unmapped page.
- Values above 2048 (65536, 0x40000, 0x1000000) were never tried. This is the
  highest value measured, not a proof that smaller ones are safe: the reads
  at 1025 ... 1032 were out of bounds even though they survived.

## Where the bound is used

`[source: tcpip.c case 17 @ a742398]`

- Subcodes 1, 2 and 3 (read inputs): `while (i < aux2)` indexes
  `Ccom_han[i]`.
- Subcodes 5, 6 and 7 (read outputs): the same loop, and on a hit
  `hercFD_SET (i, ...)` writes into the output bitmap, whose size is
  `Cselect[m]->len`, the length the guest gave. The write was not exercised
  separately; a guest-chosen index and a guest-chosen length are both
  unchecked in the source, so the probe's own header calls it a possible
  out-of-bounds write. `[inferred]`
- Subcode 4 (run): `select (Ccom_han [aux2 - 1] + 1, ...)`: the index is
  `aux2 - 1`, also unchecked. This is the line MVS-TCP-0002 is about.

Upstream develop (cc555792, 2026-10-21) still has all of these lines.
`[source]`

## What libc370 passes

libc370's `select()` passes the caller's `maxsock` unchanged as `aux2`, and
the select bitmaps are at most 128 bytes at the usual `FD_SETSIZE` of 1024. A
caller within `FD_SETSIZE` stays within the array; libc370 does not clamp a
larger `maxsock`. So "libc370 is not exposed" holds for callers that respect
`FD_SETSIZE`, not unconditionally. `[source: @@75selx.c @ v2.25.1]`

Direct `__75()` users outside libc370 were not checked.

## Handling

The probe's own header and PR #657 say it can damage the emulator and, via an
out-of-bounds write, state belonging to other address spaces before it
crashes. Run it only in a disposable container with its own instance, never
on a shared system, and never as an automatic test entry. The console log is
lost when the process dies, so the probe writes a WTO line before each
riskier value and the results are read from the container's log directly.
