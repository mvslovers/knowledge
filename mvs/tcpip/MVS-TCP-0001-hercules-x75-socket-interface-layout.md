---
id: MVS-TCP-0001
title: How Hercules' X'75' socket interface works -- two instructions per call, a conversation slot table, a socket table, 256-byte copy segments
status: source
platform: [mvs38j]
sources:
  - "SDL-Hercules-390/hyperion x75.c (DEF_INST tcpip, lar_offset) and tcpip.c (lar_tcpip, EZASOKET, find_slot, tcpip_init), tcpip.h (Ccom, talk) at a742398 (develop, 2026-10-13); read 2026-10-22"
  - "tcpip.c at upstream develop cc555792 (2026-10-21) differs from a742398 only by the three Cerr[] clears of MVS-TCP-0004; every statement below holds there too"
  - "mvslovers/libc370 v2.25.1, src/net/dyn75/@@75*.c: the guest side that issues the instruction (read 2026-10-22)"
verified_on: 2026-10-22
applies_to: [libc370, ftpd, httpd, mvsmf]
tags: [hercules, x75, tcpip, dyn75, ezasoket, socket, map32, ccom, find-slot, talk, r0-restart, hyperion]
related: [MVS-TCP-0002, MVS-TCP-0003, MVS-TCP-0004, MVS-TCP-0005, MVS-TCP-0006, MVS-TCP-0007, MVS-TCP-0008, ECO-0010]
---

## The claim

The guest's sockets (libc370's `socket()`, `send()`, `select()`, ...) are not
a network stack in the guest. Each call is a short sequence of the Hercules
instruction X'75' that runs the host's socket call inside the emulator. The
defects of this emulator layer are in MVS-TCP-0002 ... MVS-TCP-0008; this
document is the shared mechanism they refer to. Everything here is
`[source: tcpip.c / x75.c @ a742398]` unless marked.

## Registers

From the header of `x75.c`:

| Reg | Use |
|---|---|
| R0 | 0 on the first entry, set to 1 once the native call has been made (the restart flag) |
| R1 | byte counter of the copy |
| R2 | on entry to the copy: a slot index into `map32[]`, not an address |
| R3 | direction, 0 = guest to host, 1 = host to guest |
| R4 | returned value |
| R7 / R8 / R9 | function code / aux1 / aux2 (`lar_tcpip`) |
| R14 | the conversation identifier |
| R15 | 0, or -1 if `lar_tcpip` fails |

libc370 clears a 64-byte parameter list, fills R1/R5/R6/R7/R8/R9, issues the
instruction through `__75()`, which stores R0-R15 back into the list, and
reads the result from R4 (`src/net/dyn75/@@75*.c`). `[source]`

## One guest call is two instructions

1. **Direction 0.** On the first entry (R0 = 0) `lar_tcpip` mallocs a `talk`
   and a buffer for the input, and puts both pointers into `map32[]` through
   `find_slot()`: **two slots**. R14 = the talk's slot, R2 = the input
   buffer's slot. R0 becomes 1. The input bytes are then copied from the
   guest, and `EZASOKET(func, aux1, aux2, talk)` runs the host call **inside
   the instruction**, on the emulated CPU's thread.
2. **Direction 1.** `lar_tcpip` loads the answer (R1 = `len_out`,
   R2 = the output buffer's slot, R4 = `ret_cd`). The result is copied to the
   guest, and then the talk, both buffers and their `map32` slots are freed.

A call that issues only the first instruction leaves the talk and its two
slots allocated (MVS-TCP-0007). A restart of either instruction is described
under "256-byte segments" below.

## Two tables, not one

- **Socket numbers** `1 ... Ccom-1` (`Ccom` = 1024, `tcpip.h`: "maximum number
  of concurrent connections + 1") index `Ccom_opn[]`, `Ccom_han[]` (the host
  descriptor), `Ccom_blk[]`, `Cselect[]` and `Cerr[]`. SOCKET hands out the
  lowest number with `Ccom_opn[m] == 0`. The host descriptor comes from the
  host kernel. The two orders are independent (MVS-TCP-0002).
- **`map32[Ccom]`** holds the pointers of live conversations. `find_slot()`
  returns the lowest index whose entry is -1 and, when none is free, stops at
  `Ccom-1` and assigns there anyway (MVS-TCP-0007).

Both tables are emulator-wide: every address space on the system shares them.
`[source]`

## Function codes

1 INITAPI, 2 GETERRORS, 3 GETERROR, 4 GETHOSTBYNAME, 5 SOCKET, 6 BIND,
7 CONNECT, 8 LISTEN, 9 ACCEPT, 10 SEND, 11 RECV, 12 CLOSE, 13 EBCDIC2ASCII,
14 ASCII2EBCDIC, 15 IOCTL, 16 GETSOCKNAME, 17 SELECT (R8 = subcode 0 ... 8),
18 GETHOSTBYADDR, 19 GETPEERNAME. For SELECT the socket number is
`func >> 16`, aux1 the subcode, aux2 the guest's `maxsock`. `[source]`

## 256-byte segments and restart

The copy loop moves at most 256 bytes per iteration. A page translation
exception on the guest buffer nullifies the instruction; MVS resolves the
page and runs it again from the top. R0 = 1 stops `lar_tcpip` from calling
the native routine twice, R1 and the guest base register carry the
progress. The host side has no register of its own: R2 is a slot index that
never advances. `[source]`

A copy of 256 bytes or less is atomic against the exception, because
`vstorec()` resolves both page addresses through `MADDRL` before the
`memcpy`. `[inferred: upstream hyperion#884 / #885 and libc370#154 state it;
`vstorec` itself was not read at ingest]`

Before upstream hyperion PR #885 (merged 2026-09-06) the host pointer was
recomputed from `map32[R2]` on every restart, which corrupts any transfer
above 256 bytes (MVS-TCP-0005). `[inferred: from the description of #885]`
Since #885 `lar_offset()` derives the resume point from `len - R1`.
`[source: x75.c @ a742398]`

## What libc370 builds on this

`recv()` loops over chunks of at most 256 bytes; `send()` passes at most 256
bytes and returns the short count; `select()` keys its state by the highest
socket number it was given; `socket()` reads GETERROR after a failure. The
reasons are in MVS-TCP-0005, 0002 and 0004. `[source: libc370 @@75recv.c,
@@75send.c, @@75selx.c, @@75sock.c @ v2.25.1]`
