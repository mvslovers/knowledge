---
id: MVS-VSAM-0001
title: SHOWCB FIELDS=FDBK delivers only the reason code on MVS 3.8j — the RPL feedback word at RPL+X'0C' has all three codes
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway container (image and Hercules version not recorded), 2026-10-20: probe test/mvs/tstvsfb.c, RECEIVE JOB00018, run JOB00019 (container-local job numbers)"
  - "libc370 PR #678 (merged 2026-10-19, closes #625; body carries the job output), issue #680, PR #688 (merged 2026-10-20)"
  - "libc370 tags v2.23.0 / v2.24.0: src/mvs/vsam/@@vsxerr.c, src/mvs/vsam/@@vsfdbk.c, include/mvs/vsam.h (struct rpl)"
  - "mvslovers/mvs38src, work/macros/mvsce-2.1.4-target: IFGRPL (RPLFDBWD, RPLRTNCD, RPLCMPON, RPLERRCD)"
verified_on: 2026-10-20
verified_platforms: ["MVS/CE"]
applies_to: [libc370]
tags: [vsam, showcb, rpl, fdbk, rplfdbwd, rplrtncd, rplerrcd, feedback, return-code, reason-code, libc370, vsfile]
related: [MVS-VSAM-0003]
---

## The claim

`SHOWCB RPL=...,FIELDS=FDBK` on MVS 3.8j delivers **only the feedback
(reason) code**, in the low-order byte of the four bytes it stores. The
return-code and component-code bytes come back 0. `[tested]`

The RPL's own feedback word, `RPLFDBWD` at **RPL+X'0C'**, holds all three:

| byte | field | meaning |
|---|---|---|
| RPL+X'0C' | `RPLSTAT` (also named `RPLFUNCD`) | current RPL status; not one of the three codes, varies (see below) |
| RPL+X'0D' | `RPLRTNCD` | return code, the value VSAM returns in R15 |
| RPL+X'0E' | `RPLCMPON` | component code |
| RPL+X'0F' | `RPLERRCD` | reason (feedback) code |

`[source: IFGRPL macro, MVS/CE 2.1.4 copy in mvslovers/mvs38src; libc370 include/mvs/vsam.h, struct rpl, offsets 0C-0F]`

VSAM sets the word on every request, so it always describes the last request
(libc370 PR #678 body; the four-case measurement below shows it).

## The measurement

Probe `test/mvs/tstvsfb.c` (libc370), JCL `jcl/recvvsfb.jcl` and
`jcl/tstvsfb.jcl`. IDCAMS defines a KSDS (`KEYS(8 0)`, `RECORDSIZE(80 80)`)
and REPROs KEY00001..KEY00003. One handle, dynamic access, update mode,
requests in this order: (b) missing key, (a) good read, (c) duplicate
write, (d) end of data. RECEIVE JOB00018, run JOB00019:

```
TSTVSFB GREEN 13/13   (__vsfdbk, reads RPL+X'0C')        CC 0000
TSTVSFB RED 7/13      (old interface, vs->rc etc.)        CC 0001

(b) r15 8 fdbk X'10'                   RPL feedback word X'14080010'
(a) r15 0 fdbk X'00' reclen 80 rba 80  RPL feedback word X'00000000'
(c) r15 8 fdbk X'08'                   RPL feedback word X'0A080008'
(d) r15 8 fdbk X'04' rba 160           RPL feedback word X'00080004'
```

In the RED step the handle's `rc` (from SHOWCB FDBK) was `r15 0` for (b), (c)
and (d). A first version of `__vsfdbk()` that also used SHOWCB FDBK got 0
there too. The top byte of the feedback word varies (X'14', X'0A', X'00', and
X'07' on a repeated end of data) and is not one of the three codes used.

**Caveat (component code).** In every measured feedback word the component
byte is 0 as well (X'14080010', X'0A080008', X'00080004'). The measurement
shows that SHOWCB FDBK drops the return code; whether it also drops a nonzero
component code is **not shown**. libc370 PR #688 says the same: its checks
"cannot tell old from new for `component`".

## The R15 a caller sees is not VSAM's return code

The library's LERAD, SYNAD and EODAD stubs return to the request with their
own C return value in R15 (8, 12, 4). An R15 captured after the request is
therefore synthetic: at end of data it is 4, while VSAM's own return code
(`RPLRTNCD`) is 8 (case (d) above). Read `RPLRTNCD`, not the R15 a wrapper
sees. `[tested; same statement in the comment of libc370 src/mvs/vsam/@@vsfdbk.c, v2.24.0]`

A request that VSAM does not accept at all (R15 4, RPL already active) leaves
the feedback word to the request that is active; libc370's locked `vs*`
forms avoid that case. `[inferred, not measured; stated in the libc370 PR #678 body]`

## What it means for callers

- Do not use `SHOWCB FIELDS=FDBK` to get a VSAM return code on 3.8j; read the
  RPL feedback word directly.
- libc370: up to and including 2.23.0, `@@vsxerr.c` took `vs->rc` from byte 1
  of the SHOWCB FDBK area, so `VSFILE.rc` and `component` were 0 after every
  failed request `[source: @@vsxerr.c at tag v2.23.0]`.
- Fixed in **libc370 2.24.0** (issue #680, PR #688): the error exits now copy
  `rplrtncd`, `rplcmpon` and `rplerrcd` from the RPL, so `rc` is 8 or 12 on
  an error `[source: @@vsxerr.c at tag v2.24.0]`. PR #688 red/green (its own
  container, container-local JOB00018/JOB00019): handle `rc 8 rsn X'10'` and `rc 8 rsn X'08'`
  after the fix, `rc 0` before.
- `__vsfdbk()` (`<mvs/vsam.h>`, PR #678, closes #625) reads return code,
  component code, reason code, RECLEN and RBA of the last request. It was
  first released in **2.24.0**. Release placement checked by comparing the
  merge commits of PR #678 and #688 with tags v2.23.0 and v2.24.0 (not
  in 2.23.0, in 2.24.0).
