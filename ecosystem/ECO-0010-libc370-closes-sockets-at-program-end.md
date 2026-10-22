---
id: ECO-0010
title: libc370 2.20.0 closes a program's sockets when it ends — a cancelled server gives its port back, a LINKed module's abend does not close its caller's socket
status: tested
platform: [mvs38j]
sources:
  - "Two HTTPD instances side by side as batch jobs in one local MVS/CE container (image sha256:a6096e33...), 2026-10-19: T303HTTP JOB00035 (httpd 4.4.0-dev c8faa0e + fix, libc370 2.20.0 D5D2B53) and T303CTRL JOB00036 (httpd 4.3.0 32F2A0F, libc370 2.12.1 0C5E84F). Job numbers are container-local."
  - "mvslovers/httpd PR #306 (merged), the 'libc370 pin' section: after a CANCEL the 2.20.0 instance's port refuses at once, the 2.12.1 control's port hangs"
  - "mvslovers/libc370#601 and the v2.20.0 release notes (2026-10-19, tag v2.20.0 = d5d2b53): the measured table for S0C1, S322, S222, LINKed-under-try()"
  - "libc370 v2.20.0: src/net/@@soadd.c (__soend, soexit, __soestae, __soexit, __soadd), src/net/@@soupd.c (__soupd), src/net/dyn75/@@75sock.c, @@75acce.c, @@75bind.c, @@75conn.c, src/mvs/crt/@@start.c (__soestae call), @@exit.c (__soexit call), @@ppahrv.c (__soend call), @@crtset.c (GRT inherited from TCBOTC)"
  - "mvslovers/httpd#307 (closed, fixed by httpd PR #317) — the keep-alive difference seen in the same run"
verified_on: 2026-10-19
applies_to: [libc370, httpd, ftpd, oftpd, ufsd, mvsmf]
tags: [libc370, socket, close, estae, abend, cancel, s222, s322, grt, listening-port, link, try, hercules-socket-table]
related: [ECO-0003, ECO-0006, MVS-TCP-0001]
---

## The claims

1. **Before libc370 2.20.0 a socket outlived its program.** The Hercules socket
   emulation keeps one socket table for the whole system, so a socket a program did
   not close stayed open after the program ended. A server that abended or was
   cancelled kept its listening port until Hercules was restarted. `[tested]`
   `[source: libc370 v2.20.0 release notes]`
2. **From 2.20.0 a program closes the sockets its `socket()` and `accept()` returned
   when it ends** — on a normal end, on an abend nothing in the program recovers
   (S0C1, a step time limit S322, an operator CANCEL S222), and when a LINKed program
   abends under its caller's `try()`. The server's port is free again at once.
   `[tested]` on 2.20.0 against 2.12.1, `[source]` for the mechanism below.
3. **A socket belongs to the program (GRT) whose `socket()` or `accept()` created
   it.** `bind()` and `connect()` no longer make an unknown socket the program's own.
   A LINKed module that only uses its caller's socket never closes it. `[source]`
4. **A LINKed module's abend does not close the client socket the server accepted.**
   The module's harvest closes only the module's own list, which is empty.
   `[tested]` `[source]`
5. **Cost and limits:** the program's start-up establishes one ESTAE (one of the ten
   levels `estae()` provides), about 0.2 ms per program start; a program that does not
   link the socket functions pays nothing. A socket stays open when the program was
   not started as a C program (for example a function called through `@@CCALL`) or when
   the task ended without any recovery running. `[source: v2.20.0 release notes,
   libc370#601 measurement of 1000 ESTAE CREATE/DELETE pairs: 167 to 218 ms]`

Use libc370 2.20.0 or later for any server that must give its port back on CANCEL or
abend. A server built before 2.20.0 blocks its port until Hercules restarts.

## Mechanism `[source: libc370 v2.20.0]`

| Step | Where | What |
|---|---|---|
| registration | `__soadd()` in `@@soadd.c`, called from `@@75sock.c` (socket) and `@@75acce.c` (accept) | adds a `CLIBSOCK` to `grt->grtsock` |
| no adoption | `__soupd()` in `@@soupd.c`, called from `@@75bind.c`, `@@75conn.c`, `@@75acce.c` | updates name/peer only if `__sofind()` knows the socket |
| normal end | `__exit()` in `@@exit.c` calls `__soexit(grt)` (weak reference) | deletes the start-up ESTAE and calls `__soend(grt)` |
| abend under `try()` of a LINKed program | `__ppahrv()` in `@@ppahrv.c`, on the dead program's GRT | `__soend(grt)` |
| unrecovered abend | `__start()` in `@@start.c` calls `__soestae()` first (weak reference) → `estae(ESTAE_CREATE, soexit, grt)` | `soexit` validates the GRT eyecatcher, calls `__soend(grt)` and returns 0 (percolate) |

`__soend()` issues the X'75' close for each listed socket (`__75clr`) and frees the
entry. `__soestae()` runs before anything else of the program, so it is the program's
**oldest** recovery routine: the program's own `estae()` or `try()` sees an abend
first, and if it retries, the socket exit does not run. `[source: @@start.c comment]`

`__soexit()` deletes the ESTAE with `ESTAE_DELETE` only when `crt->crtestct == 1`,
i.e. when no newer `estae()` of the program is still established. `[source:
@@soadd.c]` What a module that ends with its own `estae()` still set leaves behind was
not examined (from the inbox note: not measured).

**Threads.** All threads of a program share its socket list: CTHREAD subtasks inherit
the parent's GRT through `__crtset` (`TCBOTC` at `tcb[0x84/4]`, `@@crtset.c`). A thread
that ends or abends closes nothing; the sockets close when the program ends.
`[source: @@crtset.c, v2.20.0 release notes]` A LINKed module is a different program
with its own GRT (see **ECO-0006**), which is why its harvest is separate from the
server's.

## The evidence

Setup: local MVS/CE container, two HTTPD instances as batch jobs with in-stream
HTTPPRM.

| job | build | libc370 (HTTPD005I) | instance |
|---|---|---|---|
| T303HTTP JOB00035 | httpd 4.4.0-dev (c8faa0e + fix) | 2.20.0 (D5D2B53) | A |
| T303CTRL JOB00036 | httpd 4.3.0 (32F2A0F), installed HTTPD.LINKLIB | 2.12.1 (0C5E84F) | B (control) |

**Measurement 1 — the port after CANCEL.** `C T303HTTP` and `C T303CTRL`; both jobs end
with ABEND S222. Then `curl --max-time 8` against each instance's port:

- instance A (2.20.0): curl rc 7, connection refused at once. The listening socket was
  closed when the job ended.
- instance B (2.12.1): curl rc 28, timeout. The socket outlived the job; the port stayed
  occupied until Hercules restarted.

The libc370 release notes carry the same result for five ends of a program that
held a listening port (S222 among them), each measured as "a step or job binds the same port right
afterwards": ends without `closesocket()`, LINKed under `try()` and abends S0C1,
abends S0C1 with nothing recovering, step time limit S322, operator CANCEL S222 —
2.19.0 "port in use", 2.20.0 "port free" in every row. `[tested]`

**Measurement 2 — a LINKed module's abend leaves the client socket alone.** On instance A
(2.20.0), a curl keep-alive sequence `/.abend` (module ABEND0C1, S0C1 under `try()`,
HTTPD908E) followed by `/.dm` (HTTPDM) on the **same** connection gave 503, then 200
with the connection reused. The client socket that the server `accept()`ed survived
the module's abend. `[tested]` The same row appears in the httpd#307 table
(`/.abend` `/.dm`: 503, then 200, `num_connects=0`).

Not caused by libc370: a module abend as the second or later request of a keep-alive
connection got no response (curl 000), on 4.3.0/2.12.1 and on 4.4.0-dev/2.20.0 alike.
That was an httpd defect (`httpc->resp` not cleared between requests), reported as
httpd#307 and fixed by httpd PR #317.
