---
id: MVS-TCP-0003
title: gethostbyname() stops the whole emulated CPU for as long as the host resolver takes
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #163 and PR #655 (merged 2026-10-19; job output in the PR body); probe test/mvs/tst75dns.c, jcl/tst75dns.jcl"
  - "MVS 3.8j (MVS/CE) in a throwaway local container, NUMCPU 1; emulator SDL Hyperion develop a742398; probe run on 2026-10-19; the lookup time belongs to the resolver of the machine that ran Hercules"
  - "hyperion tcpip.c, case 4 GETHOSTBYNAME and case 18 GETHOSTBYADDR, and x75.c DEF_INST tcpip, at a742398 and at upstream develop cc555792; read 2026-10-22"
verified_on: 2026-10-19
applies_to: [libc370]
tags: [hercules, x75, gethostbyname, gethostbyaddr, dns, resolver, cpu-thread, stall, observer, tst75dns]
related: [MVS-TCP-0001, MVS-TCP-0004]
---

## The claim

A forward name lookup through X'75' stops the emulated CPU until the host
resolver returns. With one CPU, **the whole guest stands still** for that
time. The stall is as long as the lookup, so it depends on the resolver of
the machine that runs Hercules: a fast answer costs milliseconds, a lookup
that has to time out costs seconds. The defect is in Hercules' `tcpip.c`, not
in libc370. `[tested]`

## Mechanism

The lookup is not handed to another thread. `DEF_INST(tcpip)` calls
`lar_tcpip`, which calls `EZASOKET`, which calls the host's
`gethostbyname()` (function 4) and `gethostbyaddr()` (function 18) directly,
inside the instruction, on the CPU's thread. `[source: x75.c, tcpip.c @
a742398; unchanged in upstream develop cc555792]`

The probe header describes this as the same class as upstream hyperion #863 /
PR #864, where a blocking SEND froze the CPU until the Hercules watchdog
(`WATCHDOG_SECS 20`) ended the emulator. A lookup is not known to be long
enough to reach it; the probe header gives glibc's worst case as about 10 s
(`[inferred]`, from the probe header).

## Evidence

An observer subtask loops STCK, notes the gap since its last STCK, then
`STIMER WAIT` 0.01 s. The main task does one lookup, timed with STCK, and the
observer's largest gap around it is read. Slow cases use a fresh name per run
(`h<n>.<a>.<b>.6.in-addr.arpa`, built from the TOD clock) so that no cache
answers.

```
+TST75DNS ctl-name localhost -> 127.0.0.1 dur=2 gap=10 ticks=49
+TST75DNS slow-name1 h41845.148.14.6.in-addr.arpa -> NULL dur=5026 gap=5030 ticks=49
+TST75DNS slow-name2 h49807.179.14.6.in-addr.arpa -> NULL dur=4158 gap=4160 ticks=49
+TST75DNS RESULT BLOCKS: 2 of 2 slow lookups stalled the observer - RC 4
```

`dur` is the lookup as the lookup task measured it, `gap` the observer's
largest gap, in ms. The gap equals the lookup time within 4 ms in both slow
cases (5026/5030, 4158/4160). A fast lookup shows 2 ms against a 10 ms gap,
which is the dispatching noise of the observer. `[tested]`

## Limits of the measurement

- **Reverse lookups** (`gethostbyaddr`): PR #655 says they showed the same
  stall, but they are not counted, because the `gethostbyaddr` control on the
  loopback address returned NULL. The forward case is the measured one;
  the reverse case rests on the source (same inline call). `[tested]` for
  forward, `[source]` for reverse.
- **NUMCPU > 1:** MVS can dispatch the observer on another CPU, so the stall
  of one CPU thread need not show as an observer gap. The container ran
  NUMCPU 1. Whether the guest as a whole is stalled with more CPUs was not
  measured.
- Nothing here says how much CPU time the job is charged for the stalled
  interval; that was not checked.
- The host's `gethostbyname()` is also not thread-safe (libc370#163); that is
  a second problem on the same line and was not measured.
