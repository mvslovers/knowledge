# Hercules X'75' TCP/IP: the error words are stale (per socket) and shared (global)

Date: 2026-10-20. Source: libc370 #161, PR #692 (guard), probe `test/mvs/tst75err.c`
+ `jcl/tst75err.jcl`; Hercules hyperion `tcpip.c` at a742398 (= upstream develop);
fix commit 48b35a59 (mvslovers fork, branch fix/x75-cerr-reset), upstream
issue SDL-Hercules-390/hyperion#894, PR SDL-Hercules-390/hyperion#895. Measured in local MVS/CE containers (stock image
`ghcr.io/mvslovers/mvsce:latest` with Hercules a742398, and a local image
`mvsce:x75cerr` with 48b35a59).

## How the guest gets an error

A failing X'75' call returns -1 in R4. The error is fetched with a SECOND X'75'
instruction:

- GETERRORS (function 2, aux1 = socket): returns `Cerr[socket]`. A closed or
  invalid number gives ENOTSOCK (`check_not_sock`).
- GETERROR (function 3): returns `CerrGen`, ONE word for the whole emulator.
  Written by failing SOCKET (hEMFILE or host errno), GETHOSTBYNAME, GETHOSTBYADDR.

## Finding 1: `Cerr[]` is never reset (stale per-socket error)

Only `tcpip_init()` clears `Cerr[]`. SOCKET and ACCEPT hand out a free number
without clearing it, CLOSE does not clear it. Socket numbers are shared by all
address spaces.

- A new socket on a re-used number reads the previous holder's last error:
  98 of 98 (stock). With 48b35a59 (Cerr[m] = 0 in SOCKET, ACCEPT, CLOSE): 0.
- Within one address space: in the RED step, 2 extra fresh sockets (100 instead
  of 98) read the last errors left by the GREEN step that ran just before in the
  same job.
- Not every failure path writes `Cerr` first: SELECT with no select state
  (`Cselect == NULL`) and `check_not_sock` return -1 without it.

## Finding 2: `CerrGen` crosses address spaces

Between the failing call and GETERROR another address space can overwrite the
word. Measured with two concurrent jobs (GEN=1/GEN=2): 297 and 296 of 300 reads
crossed, also with NUMCPU 1 and a deliberate wait. The 48b35a59 fix does not
change this (297/296). Only an interface change can fix it (error returned with
the same call: `-errno` in R4 breaks guests that test `== -1`; an extra register
is risky because guest stubs such as libc370's `__75()` store R0-R15 back and
GETPEERNAME uses R6 as a buffer pointer). Not pursued.

## Finding 3: libc370's old select() error path never sent Finish

`@@75selx.c` read GETERRORS after a failed select run by overwriting the
function code in the parameter list (r7 = 2). The following calls of the run,
including Finish (which frees the select state in Hercules), went out as error
reads, so Hercules kept the select state until the socket was closed.

## select() on a socket closed and re-created while it waited (10 rounds)

| Hercules | libc370 | errno |
|---|---|---|
| a742398 | before #692 | 61 x5 (old holder's error), 48 x5 (new holder's) |
| 48b35a59 | before #692 | 0 x5 (errno 0 with -1), 48 x5 |
| either | #692 | ENOTSOCK (38) x10 |

## What libc370 does since #692 (released after 2.24.0)

- `select()`: any emulator select failure means a socket in it is gone ->
  ENOTSOCK, without reading GETERRORS (keeps r7, so Finish is sent).
- `socket()`: takes GETERROR only if socket() can produce it (EMFILE, ENFILE,
  ENOBUFS, ENOMEM, EACCES, EAFNOSUPPORT, EPROTONOSUPPORT, EPROTOTYPE, EINVAL),
  else ENOBUFS. A plausible foreign error (measured EAFNOSUPPORT <->
  EPROTONOSUPPORT swap) still gets through.
