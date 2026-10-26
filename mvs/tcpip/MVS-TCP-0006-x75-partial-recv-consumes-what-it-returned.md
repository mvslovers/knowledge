---
id: MVS-TCP-0006
title: A partial X'75' RECV consumes the bytes it returned -- the next call continues, nothing is delivered twice (no defect)
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #165 and PR #656 (merged 2026-10-19; job output in the PR body); probe test/mvs/tst75prt.c (header: method and output format), jcl/tst75prt.jcl"
  - "MVS 3.8j (MVS/CE) in a throwaway local container, NUMCPU 1; emulator SDL Hyperion develop a742398 (contains the restart fix hyperion#885); probe run on 2026-10-19"
  - "hyperion tcpip.c, case 11 RECV, at a742398; libc370 src/net/dyn75/@@75recv.c at v2.25.1; read 2026-10-22"
verified_on: 2026-10-19
applies_to: [libc370]
tags: [hercules, x75, recv, partial-read, short-count, loopback, tst75prt, negative-result]
related: [MVS-TCP-0001, MVS-TCP-0005]
---

## The claim

A guest RECV that asks for more bytes than are queued gets the short count,
**and those bytes are gone** from the socket. The next RECV continues at the
next byte. No replay, no corruption, no leftover bytes. Code that loops on
partial reads (libc370's `recv()` does) is not affected by this path.
`[tested]`

This is a **negative result**: a suspected second X'75' defect was looked for
and not found, on one setup (see Limits).

## Why it was suspected

A corruption report from another guest's socket test showed a 636-byte message
arriving as 256 bytes at offset 0, then 380 bytes at offset 256 that carried
the message **from its start**. It was read as "a partial RECV does not consume
what it returned". It had been cited as a sighting of the restart defect
(MVS-TCP-0005) in hyperion#884 and was retracted there: under the restart
mechanism the first bad byte would be at 512, not 256 (the first call moves a
single, immune 256-byte segment; the second moves two segments into
`buf+256`). `[per libc370#165]`

## Source: why it consumes

`RECV` runs the host `select()` with a zero timeout, then the host `recv()`
(no `MSG_PEEK`) into a freshly allocated output buffer, and sets
`len_out = size`, the count the host returned. The guest copy moves exactly
`len_out` bytes. Nothing is put back on the host socket.
`[source: tcpip.c case 11 @ a742398]`

libc370's `recv()` loops over X'75' calls of at most 256 bytes until the
requested length is read, so a short count from the host is normal and is
continued. `[source: @@75recv.c @ v2.25.1]`

## Evidence

The probe owns both ends of a loopback pair. The peer sends the first `P`
bytes of a 636-byte `i % 251` pattern, the guest waits (FIONREAD) until `P`
bytes are queued, then issues **one** RECV for 636 through `__75()` (one pair
of X'75' instructions, no retry loop), so the count is short by
construction. FIONREAD is read again, the peer sends the rest, one more RECV
for what is outstanding, and the whole buffer is compared. A replay would put
`PATTERN(0..)` at the continuation offset. Split points `P`: 256 (the reported
case), 1, 100, 255, 257, 380, 500, 635, 3 rounds each. Then 20 rounds that
send all 636 bytes and receive at once with no waiting, checking whatever
partial reads happen on their own. `[tested]`

```
+TST75PRT SUMMARY forced=24 short=24 replay=0 corrupt=0 leftover=0
+TST75PRT SUMMARY race=20 race_short=20 race_bad=0
```

- 24 of 24 forced rounds returned a short count and continued correctly;
  FIONREAD was 0 after the last call in every round.
- The 636 case at `P` = 256: first call 256 bytes, second 380, correct.
- A split that is not a multiple of 256 cannot be the restart defect, and
  none replayed.
- The probe's exit code distinguishes "no short count ever happened" (RC 4,
  no verdict) from a pass; here short counts happened in every round.

The receive buffer is written immediately before each RECV, so it is resident
and the restart path of MVS-TCP-0005 is not entered. This isolates the
consumption question from that defect. `[per the probe header]`

## Limits

- Both ends are in the **same guest** and the transport is host loopback. The
  reported case had an external sender; this result says the partial-RECV path
  consumes correctly, not that their setup cannot fail. What caused
  that report was not investigated.
- One emulator build (a742398), NUMCPU 1.
