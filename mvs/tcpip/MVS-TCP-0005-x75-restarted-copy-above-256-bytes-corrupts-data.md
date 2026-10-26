---
id: MVS-TCP-0005
title: On an emulator without hyperion#885 a restarted X'75' copy above 256 bytes corrupts SEND and RECV data -- libc370 caps both at 256
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #160 (closed 2026-10-20) and PR #683 (merged 2026-10-20; full job output in the PR body): the SEND measurement; probe test/mvs/tst75sst.c, jcl/recv75sst.jcl, jcl/tst75sst.jcl"
  - "libc370 issue #154 and PR #166 (merged 2026-09-07): the RECV side, probe test/mvs/tst75rst.c; SDL-Hercules-390/hyperion issue #884 and PR #885 (merged 2026-09-06, commit 4675e7e1): the emulator fix and its RECV measurement"
  - "SEND job: JOB00019 (container-local), MVS 3.8j (MVS/CE) in a throwaway local container; Hercules from mvslovers/hyperion branch diag/x75-restart-trace f1f1f9d1 (no host-side fix, plus a restart trace); control on ghcr.io/mvslovers/mvsce:latest with Hercules a742398 (contains #885). Run of 2026-10-19/20."
  - "hyperion x75.c (lar_offset, DEF_INST tcpip) at a742398; libc370 src/net/dyn75/@@75send.c, @@75recv.c at v2.25.1 and CHANGELOG [2.24.0]; releases of mvslovers/libc370 (gh release list, compare of merge commits against tags); read 2026-10-22"
verified_on: 2026-10-20
applies_to: [libc370, ftpd, mvsmf]
tags: [hercules, x75, send, recv, restart, 256-byte-segment, pgrlse, page-fault, corruption, hyperion-884, hyperion-885, libc370-154, libc370-160, tst75sst]
related: [MVS-TCP-0001, MVS-TCP-0006]
---

## The claim

X'75' copies data in 256-byte segments and the instruction is restartable.
On an emulator **without** upstream hyperion PR #885, a page fault on the
guest buffer after at least one completed segment makes the host side resume
at the **start** of its own buffer. The result is silent corruption, in both
directions: `[tested]`

- **SEND:** the peer receives the right length with the wrong content -- the
  tail shifted down over the head, leftover host memory where the tail
  belonged. No error is reported.
- **RECV:** the guest buffer gets the head of the message again where the
  tail belongs.

A copy of 256 bytes or less is immune. A guest cannot tell whether the
emulator has the fix, so libc370 caps every X'75' SEND and RECV at 256 bytes.

## Mechanism

`[inferred: from hyperion#884 / #885 and libc370#154; consistent with the code of a742398 that fixes it]`

A page translation exception on the guest buffer is nullifying: MVS resolves
the page and the instruction runs again. The guest side resumes correctly
(R1 = bytes left, the base register was advanced before the exception, R0 = 1
stops the native call from running twice). Before #885 the host pointer was
recomputed from `map32[R2]` on every entry, and R2 is a slot index that never
advances. A copy of 256 bytes or less either faults having copied nothing,
where restarting from the start is correct, or completes. The defect needs
one **completed** segment before the fault, so it needs more than 256 bytes,
and its likelihood grows with the number of guest pages the copy touches.
That explains why every larger cap looked like a fix and then failed (4096 in
libc370 since December 2024, 2048 in mvsMF, which failed five days later,
per libc370#154).

The fix in a742398: `lar_offset()` returns `len - R1` and the copy starts at
`map32[R2] + lar_offset()`. `[source: x75.c @ a742398]`

## Evidence: SEND (libc370#160, PR #683)

Probe `tst75sst.c`: each round fills a send buffer with an `i % 251`
pattern, releases one page `bound` bytes into it with PGRLSE (SVC 112; its
effect was verified first), sends the whole buffer with `send()` over a
loopback pair the probe owns both ends of, and the receiving end (a `recv()`
that is itself capped, so it cannot add a fault) compares. 6 cases
(len/bound 1024/0 as control, 300/256, 1000/512, 1000/600, 4096/2048,
32000/16384), 5 rounds each. One job, two steps: GREEN = `send()` capped,
RED = the library before the cap. Emulator without the host-side fix:

```
RED:   +TST75SST len=1024 b=0 intact first=1024 calls=1   (control)
       +TST75SST len=300 b=256 r=0 first_bad=1 replay_from=256:Y
       +TST75SST len=1000 b=600 r=0 first_bad=0 replay_from=512:Y
       +TST75SST len=32000 b=16384 r=0 first_bad=1 replay_from=16384:Y
       +TST75SST FAILED (25 of 30 rounds)                  RC 0008
GREEN: +TST75SST len=300 b=256 intact first=256 calls=2
       +TST75SST len=32000 b=16384 intact first=256 calls=125
       +TST75SST PASSED (30 rounds)                        RC 0000
```

`replay_from=N:Y` = the peer's bytes from offset 0 are the send buffer from
offset N on, the signature of a restart. Bound 600 replays from 512: the
segment straddling the boundary faults before it copies a byte. `first_bad`
is 0 or 1, not a multiple of 256, because the released source page reads as
zeros and the pattern starts at 0. The 25 failed rounds are all 25 rounds
with a fault inside the buffer; the 5 control rounds were clean. `[tested]`

The emulator's restart trace for the same job (trace line, format as in the
probe header: `X75 restart 7 (3 after a completed segment): dir=0 left=488
done=512 ...`): RED had **25 SEND restarts after a completed segment**
(`dir=0 done=256/512/2048/16384`), one per failed round. GREEN had about 29
SEND restarts, **all `done=0`**: the fault still happens, the cap only moves
it to the start of a segment, where restarting is correct. So a green guest
result is not "never faulted". `[tested]`

Control: the stock image (Hercules a742398, with #885) passes RED and GREEN,
30 of 30 each. `[tested]`

## Evidence: RECV (libc370#154, hyperion#885)

The RECV probe `tst75rst.c` places a page boundary at a chosen multiple of
256 inside a 1024-byte receive buffer, releases the page beyond it, and
receives over a loopback pair, through `__75()` directly. Emulator side
count of bytes already copied equals the guest's first bad byte, and the tail
is a clean replay of the host buffer from its start: `[tested, per hyperion#885 and libc370 PR #166]`

| Boundary | before #885: copied / first bad byte | after #885 |
|---|---|---|
| 0 (control) | 0 / none | none |
| 256 | 256 / 256 | none |
| 512 | 512 / 512 | none |
| 768 | 768 / 768 | none |

(Red JOB03045 RC=8, green JOB03046 RC=0, container-local.) The same defect
was sighted in production in FTPD 1.0.1 (libc370 PR #166 cites mvslovers/ftpd#122):
a 4577-byte upload arrived as `orig[0:2560] + orig[0:1536] + orig[4096:4577]`.

## What it means for callers

- A guest cannot detect the fix: no return value, status or function code
  distinguishes it. Code that must be correct on any Hercules caps every X'75'
  SEND and RECV at 256 bytes. The cap can never be raised on the strength of
  a fixed host.
- A passing guest-side test does not prove a fixed emulator: it also passes
  when no fault fell after a completed segment. Only the emulator-side trace
  separates the two.
- **`recv()`** (libc370) loops over chunks of at most 256 bytes until `len`
  bytes are read or a call returns 0 or -1, and returns the count it read.
  Cap since libc370 #154 (PR #166, merged 2026-09-07), first released in
  **v1.0.5** (2026-09-13). `[source: @@75recv.c @ v2.25.1; releases]`
- **`send()`** passes at most 256 bytes per call and returns that short
  count; it never returns 0 for a non-empty request (a request of 256 bytes
  or less, including 0 or a negative length, goes through as before).
  It does not loop over the rest itself: callers must loop on a short
  positive return. The `-2` retry of libc370#120 is unchanged and reissues
  the capped request. PR #683 was merged 2026-10-20 08:54 UTC and first
  released in **v2.24.0** (2026-10-20 11:15 UTC); it was not in v2.23.0.
  `[source: @@75send.c @ v2.25.1, CHANGELOG [2.24.0]; releases]`
- **Cost:** 16 times as many X'75' pairs per byte for `recv()` as the old
  4096 cap (libc370#154).
- FTPD's data send path already loops on short positive returns and treats
  `rc <= 0` as fatal, so a cap that returned 0 would have been the
  dangerous variant (libc370#160, comment).
