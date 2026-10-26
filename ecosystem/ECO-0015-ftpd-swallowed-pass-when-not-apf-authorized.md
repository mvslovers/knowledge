---
id: ECO-0015
title: FTPD before ftpd#258 gives no reply to PASS when it is not APF-authorized — racf_login() abends S047, and the recovery abends again at its first step and ends without a message or a reply
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway container, 2026-10-21 (container-local), RAKF 2.0.0: FTPD built from mvslovers/ftpd main 5f5734b (1.3.0-DEV) and started from a library that is not APF-authorized, with FACILITY SVC244 READ for STCGROUP removed from the RAKF profiles and RAKF refreshed"
  - "mvslovers/ftpd tag v1.2.0 and commit 5f5734b: src/ftpd#ses.c (the command loop with try(ftpd_run_command), recover_count and FTPD_MAX_RECOVER; ftpd_session_recover and its first step racf_set_acee), src/ftpd#aut.c (ftpd_auth_pass: racf_login before the attempt counter), include/ftpd.h (FTPD_MAX_RECOVER 3)"
  - "mvslovers/ftpd#258, fixed by PR #259 (commit e039c02, 2026-10-21, an ancestor of tag v1.3.0): src/ftpd#aut.c (authorized flag test before racf_login), src/ftpd#ses.c (ftpd_session_reset_identity, FTPD077E)"
  - "libc370 v2.25.1: src/mvs/racf/raclogin.c and src/mvs/racf/racsacee.c (TESTAUTH, then MODESET KEY=ZERO,MODE=SUP)"
verified_on: 2026-10-21
applies_to: [ftpd, libc370]
tags: [ftpd, pass, racf_login, racf_set_acee, s047, try, recovery, re-abend, apf, ftpd-258, ftpd071e]
related: [ECO-0012, ECO-0020, ECO-0021]
---

## The claims

1. **An FTPD that is not APF-authorized gives no reply to `PASS`.** The client gets `220`
   and `331`; `PASS` is never answered. `[tested]` (main 5f5734b; 240 s without a reply,
   not a delay.) The same silence was seen with the v1.2.0 release (ECO-0020).
2. **The session is not hung.** The next command on the same connection is answered at once
   (`NOOP` 200, `PWD` 530 Not logged in). A repeated `PASS` is silent again, and the failed-login
   counter does not advance. `[tested]`
3. **Only the idle timeout ends it.** `421 Idle timeout, closing connection` after 303 s with
   `IDLETIMEOUT 300`. `[tested]`
4. **Three `PASS` commands in a row close the connection without a reply** and put
   `FTPD071E SESSION SOCKET=n CLOSED AFTER 3 CONSECUTIVE ABENDS` on the console. Any other
   command in between resets the count, so a client that alternates is never closed. `[tested]`
   `[source: src/ftpd#ses.c, recover_count reset after a command that did not abend; FTPD_MAX_RECOVER is 3]`
5. **There is no trace of the failure.** The started task's STDOUT has no "RAKF login failed"
   line and the console has no `FTPD070E`. `[tested]`
6. **Other sessions are not affected.** Greeting and `USER` work, the listener and the worker
   pool run. `[tested]`
7. **With `FACILITY SVC244` READ restored for STCGROUP and a restart of the same load module from
   the same non-APF library,** FTPD prints `FTPD008I AUTHORIZED BY SVC (MODULE KEY 8)` and `PASS`
   is answered `230` in 0.09 s. `[tested]`

## Why: two S047 in a row, the second one inside the recovery

`[source]`

- `racf_login()` does `MODESET KEY=ZERO,MODE=SUP` unless `TESTAUTH` says the caller is already in
  supervisor state. An unauthorized task gets abend S047 there, not an error code (ECO-0020).
- The command runs under `try(ftpd_run_command, ...)`. The abend is caught, `recover_count` is
  incremented, and `try(ftpd_session_recover, ...)` runs. Its first step is
  `racf_set_acee(sess->server->stc_acee)`, and `racf_set_acee()` has the same
  `TESTAUTH` / `MODESET KEY=ZERO,MODE=SUP` sequence. It abends S047 again.
- The outer `try()` around the recovery contains this second abend (comment in the code: "Contain a
  re-ABEND during recovery itself") and returns an abend code that nobody reads. The steps that
  would tell somebody, the `FTPD070E` message (step 3) and the reply to the client (step 4), come
  after step 1 and are never reached. The loop then continues with the next command.
- `auth_attempts` is incremented only after `racf_login()` returns, so the abended `PASS` never
  counts as a failed login.
- The v1.2.0 tag has the same structure (`ftpd_session_recover` with `racf_set_acee` as step 1,
  `try(ftpd_session_recover, ...)` in the command loop, `FTPD_MAX_RECOVER 3`) and calls
  `racf_login()` unconditionally in `ftpd_auth_pass()`. The release's silent `PASS` (ECO-0020) is
  this mechanism. The v1.2.0 container run itself did not trace it; the link is by reading both
  versions of the source.

## The fix

`[source]` mvslovers/ftpd#258, PR #259, commit e039c02, in tag v1.3.0 (published 2026-10-22):

- `ftpd_auth_pass()` answers `530` naming the cause before it calls `racf_login()` when the task is not
  authorized, logs it once per server, and does not count the attempt.
- `ftpd_session_recover()` resets the STC identity only on an authorized task, and under a `try()` of
  its own (`ftpd_session_reset_identity`), so the `FTPD070E` message and the client reply follow even
  if the reset abends. A failed reset is reported as `FTPD077E`.

The main-branch answer after the fix was read in the code, not measured on MVS.

## The general rule

For any program, not only FTPD:

- `racf_login()` and `racf_set_acee()` end with S047 in an unauthorized caller instead of returning an
  error code. Test authorization before calling them.
- Do not call either of them from a recovery routine of a program that may run unauthorized. A second
  abend inside a `try()` recovery path is swallowed by the enclosing `try()`; if the code that reports
  the failure comes after the call that abends, the failure is never reported.
- The return value of a `try()` around a recovery routine is the only sign of the second abend.

## What was not established

- The libc370 version linked into the measured main build is not recorded; the libc370 source above is
  v2.25.1.
- The release v1.2.0 was not re-run with the idle-timeout and three-`PASS` sequences; claims 3 and 4 are
  measured on main 5f5734b and read in the v1.2.0 source only.
