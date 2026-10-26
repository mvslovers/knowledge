---
id: MVS-TCP-0004
title: X'75' error words -- GETERRORS reads the previous holder's error, GETERROR reads one word shared by every address space
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #161, PR #656 (merged 2026-10-19: probe and numbers), PR #692 (merged 2026-10-20: library guard and red/green matrix); probe test/mvs/tst75err.c, jcl/tst75err.jcl, jcl/tst75erx.jcl"
  - "MVS 3.8j (MVS/CE) in throwaway local containers, NUMCPU 1: stock image ghcr.io/mvslovers/mvsce:latest with Hercules a742398 (banner 4.10.0.11783-SDL-DEV-ga7423980) and a local image with 48b35a59 (mvslovers/hyperion, branch fix/x75-cerr-reset); runs of 2026-10-19 and 2026-10-20"
  - "hyperion tcpip.c at a742398 and 48b35a59 (diff: three lines), upstream develop cc555792 (2026-10-21); read 2026-10-22"
  - "SDL-Hercules-390/hyperion issue #894 and PR #895 (merged 2026-10-20, merge commit 193efe8b)"
  - "libc370 CHANGELOG [2.24.1] 2026-10-20; src/net/dyn75/@@75selx.c and @@75sock.c at v2.24.0 and v2.25.1; read 2026-10-22"
verified_on: 2026-10-20
applies_to: [libc370]
tags: [hercules, x75, errno, geterror, geterrors, cerr, cerrgen, stale-error, select, socket, tst75err, hyperion-894]
related: [MVS-TCP-0001, MVS-TCP-0002, MVS-TCP-0003]
---

## The claim

The emulator keeps socket errors in two places, and neither is safe to read
back from the guest the way libc370 did before 2.24.1. `[tested]`

- **GETERRORS (code 2), `Cerr[socket]`:** the entry is never cleared when a
  socket number is handed out again, so a new socket reads the **last error
  of the previous holder of the number** -- which can be another address
  space's.
- **GETERROR (code 3), `CerrGen`:** one word for the whole emulator. Between
  the failing call and the second instruction that reads it, **another address
  space can overwrite it**.

The first is fixed in upstream Hercules since 2026-10-20 (hyperion#895). The
second is not fixed and cannot be without an interface change.

## How the guest gets an error

A failing X'75' call returns -1 in R4. The error comes from a SECOND call:
`[source: tcpip.c @ a742398]`

- GETERRORS (aux1 = socket) returns `Cerr[socket]`. A closed or invalid number
  gives ENOTSOCK (`check_not_sock`).
- GETERROR returns `CerrGen`. Only a failing SOCKET (`hEMFILE`, or the host
  errno), GETHOSTBYNAME and GETHOSTBYADDR write it.

## Finding 1: `Cerr[]` is never reset

Only `tcpip_init()` clears `Cerr[]`. SOCKET and ACCEPT hand out a free number
without touching it; CLOSE resets `Ccom_opn`, `Ccom_han`, `Ccom_blk` and the
select state, but not `Cerr`. Socket numbers are shared by all address spaces.
`[source: tcpip.c @ a742398]`

```
+TST75ERR SUMMARY rounds=50 provoked=50 notprov=0 crossed_slot=0
+TST75ERR SUMMARY stale_slot=98 (=prev holder 98) gen_provoked=50 crossed_global=0
```

- A new socket on a re-used number read the previous holder's last error:
  **98 of 98** (stock emulator). `[tested]`
- No crossing between two live sockets: 0 of 50. `[tested]`
- In the second step of the same job, 2 extra fresh sockets (100 instead of
  98) read the last errors left by the first step's program, which ran before
  it in the same address space. `[tested]`
- That the previous holder can be another address space follows from the
  source and was not measured across address spaces. `[source]`
- Not every failure path writes `Cerr` first: SELECT without a select state
  (`Cselect[m] == NULL`) and `check_not_sock` return -1 without it. `[source]`

**Fix.** `Cerr[m] = 0` in SOCKET and ACCEPT when `m` is handed out, and in
CLOSE (three lines, no interface change; mvslovers/hyperion 48b35a59, upstream
issue hyperion#894, PR #895, merged 2026-10-20). With it the stale reads went
from 98 of 98 to **0**. `[tested]` The stock image of 2026-10-13 (a742398)
does not contain it. `[source: diff of tcpip.c a742398 vs 48b35a59 and vs
upstream develop cc555792]`

## Finding 2: `CerrGen` crosses address spaces

Two jobs ran at the same time (two class A initiators), each provoking a
different global error through a raw `socket()` with a bad argument, waiting
0.16 s, then reading GETERROR. Each job counted the rounds in which it read
the other's error: `[tested]`

```
+TST75ERR SUMMARY GEN=PROTO rounds=300 provoked=300 crossed_global=297 (43=0 47=297 22=0 other=0)
+TST75ERR SUMMARY GEN=AF rounds=300 provoked=300 crossed_global=296 (43=296 47=0 22=0 other=0)
```

(43 EPROTONOSUPPORT, 47 EAFNOSUPPORT, 22 EINVAL.) NUMCPU was 1, with a
deliberate wait, so the crossing is a task switch between the two
instructions, not a multi-CPU race. 297 / 296 of 300 reads crossed. The
48b35a59 fix does not change this (297 / 296 again). The probe's header says a
negative result would only mean the window was missed.

**Why it stays.** The state is one variable and the error and its query are
two instructions; per-thread storage would not help. SOCKET would have to
return its error with the same call: `-errno` in R4 breaks guests that test
`== -1`; an extra register is risky because guest stubs such as libc370's
`__75()` store R0-R15 back and GETPEERNAME uses R6 as a buffer pointer. The
issue hyperion#894 declares it out of scope. `[tested]` for the crossing,
`[inferred]` for the reasoning (from libc370#161).

## Finding 3: libc370's old `select()` error path never sent Finish

Before 2.24.1 `@@75selx.c`, after a failed select run, read GETERRORS by
overwriting the function code in the parameter list (`pl.r7 = 2`, the socket
in `r8`). The calls after it -- result subcodes and Finish -- then went out
with function code 2, as error reads. Finish is the call that frees the
select state in the emulator, so the state stayed until the socket was
closed. `[source: @@75selx.c @ v2.24.0]`

`select()` on a socket that was closed and re-created while it waited, 10
rounds per row (errno that `select()` reported): `[tested]`

| Hercules | libc370 | errno |
|---|---|---|
| a742398 | before 2.24.1 | 61 x5 (old holder's error), 48 x5 (new holder's) |
| 48b35a59 | before 2.24.1 | 0 x5 (errno 0 with -1), 48 x5 |
| either | 2.24.1 | ENOTSOCK (38) x10 |

So the Cerr reset alone does not repair `select()`: on this path (the
select state went with the CLOSE) the emulator fails the poll without writing
an error word, and the old library read the new holder's.

## What libc370 does since 2.24.1 (2026-10-20, PR #692)

`[source: @@75selx.c, @@75sock.c @ v2.25.1; CHANGELOG [2.24.1]]`

- `select()`: any emulator failure of a select run means a socket of the run
  is gone, so `errno = ENOTSOCK` without reading GETERRORS. `r7` stays a
  select call, so Finish is sent.
- `socket()`: reads GETERROR, and keeps the value only if `socket()` can
  produce it (EMFILE, ENFILE, ENOBUFS, ENOMEM, EACCES, EAFNOSUPPORT,
  EPROTONOSUPPORT, EPROTOTYPE, EINVAL); anything else becomes ENOBUFS. This
  catches a lookup's code, or 0, leaking in. A plausible foreign `socket()`
  error (the measured EAFNOSUPPORT / EPROTONOSUPPORT swap) still gets
  through; only an emulator interface change can stop that.
- The other wrappers (`connect`, `bind`, `accept`, `send`, `recv`,
  `ioctlsocket`, `getsockname`, `getpeername`) read GETERRORS for their own
  socket after their own failing call; they are not changed. `[source]`

Which release: PR #692 was merged 2026-10-20 11:59 UTC and is first in
libc370 v2.24.1 (released 2026-10-20 13:36 UTC). It was not in v2.24.0.
`[source: gh release / compare of the merge commit against the tags]`
