---
id: ECO-0020
title: libc370 racf_auth and racf_login — what the return codes mean, why a denial is silent, and what each call needs from APF
status: tested
platform: [mvs38j]
sources:
  - "libc370 v2.25.1 (commit 82016ba, tag of 2026-10-21): include/mvs/racf.h (return-code contract), src/racauth.c (LOG=NONE flag, TESTAUTH FCTN=0/1, MODESET only when APF), src/raclogin.c (supervisor-state test, then MODESET KEY=ZERO,MODE=SUP)"
  - "mvslovers/libc370#63 (LOG=NONE flag byte; closed 2026-08-07, fix in v1.0.2 of 2026-08-12), mvslovers/libc370#197 (racf_auth without APF; closed 2026-09-29, first release v1.0.7)"
  - "mvslovers/ftpd#82 (treat racf_auth RC 4 as allowed before #63 lands; closed)"
  - "RAKF v2.0.0 (commit 019acf4): SRCLIB/ICHSFR00.hlasm, label RACHCHK (WORKNLOG from ACHKLOGS), the ENTYWARN and ENTYFAIL paths, WTOUNKN"
  - "MVS/CE throwaway container, 2026-10-21 (container-local): small libc370 2.25.1 probe programs (racf_get_acee, racf_auth, racf_login) linked AC(0) and AC(1), run from a load library that is not on the APF list and, as a control, from SYS2.LINKLIB; RAKF 2.0.0 installed from the release deck"
  - "MVS/CE throwaway container, 2026-10-21: FTPD 1.2.0 started in the same non-APF state (APF SETUP FAILED RC=4), client session timed against it"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf, httpd]
tags: [libc370, racf_auth, racf_login, saf, rakf, apf, s047, log-none, return-code, rakf0005]
related: [MVS-SEC-0001, MVS-SEC-0004, MVS-SEC-0010, MVS-SEC-0012, ECO-0008, ECO-0021, ECO-0022]
---

Two libc370 calls front the SAF router: `racf_auth()` (RACHECK) and `racf_login()` (RACINIT). Programs
that use them (FTPD, mvsMF through httpd, anything that asks "may this user do that?") have to read the
return codes the same way and have to know what each call needs from the program's authorization. All
checks below ran against RAKF 2.0.0 (see MVS-SEC-0010 for how that differs from the RAKF in the image).

## The claims

- **`racf_auth()` returns the SAF return code unmodified.** `[source: libc370 v2.25.1 include/mvs/racf.h]`
  0 = permitted; 4 = the resource is not protected (no profile, or no matching profile); 8 = not
  authorized. The header's advice for callers is to test `rc <= 4` for "may proceed". `[tested]` against
  RAKF 2.0.0: empty class 4, profile with NONE 8, with enough access 0, undefined class 8
  (MVS-SEC-0004, MVS-SEC-0010).
- **An unprotected resource answers 4, not 0, since libc370#63.** `racf_auth()` sets the LOG=NONE bit
  `RACHECK_FLAG1_LOG_NONE` (0x02) in the RACHECK flag byte. Before the fix the byte was 0x10, which is
  `DSTYPE=V` in that position: the unprotected resource answered 0 and the audit was not suppressed.
  `[source: libc370 v2.25.1 src/racauth.c, and the issue text of libc370#63]` The fix is in libc370
  v1.0.2 (2026-08-12). A caller written before it (FTPD, mvslovers/ftpd#82) accepted RC 4 as "allowed";
  that remains correct. An older libc370 than 2.25.1 was not measured. `[tested]` for 2.25.1 only.
- **A denial from `racf_auth()` writes no RAKF message.** With the LOG=NONE bit set, ICHSFR00 turns the
  bit into its WORKNLOG flag and writes neither RAKF0005/000A (denial) nor RAKF0008/000B (undefined
  resource, RC 4). The silence belongs to the call, not to the profile: a real OPEN of a data set that
  the same user is denied does write RAKF0005/000A. The ENTYWARN and ENTYFAIL paths are silent as well.
  `[source: RAKF v2.0.0 ICHSFR00 RACHCHK]` `[tested]` (MVS-SEC-0004).
- **RAKF0012 `UNDEFINED CLASS` is not suppressed.** WTOUNKN ignores WORKNLOG, so a `racf_auth()` against a
  class that is not in the CDT returns 8 and the message goes to the log every time it is called.
  `[source: RAKF v2.0.0 ICHSFR00 WTOUNKN]` `[tested]` (probe class `NOSUCHCL`: 8/8/8 and
  `RAKF0012 UNDEFINED CLASS NOSUCHCL`).
- **`racf_auth()` works from a program that is not APF-authorized, since libc370#197** (first release
  v1.0.7). `[source: libc370 v2.25.1 src/racauth.c: TESTAUTH FCTN=0/1, MODESET only when authorized]`
  `[tested]` with 2.25.1: the probe linked AC(0) and AC(1) and run from a load library that is not on the
  APF list got the address space's own ACEE from `racf_get_acee()` and the same return-code triples
  (READ/UPDATE/ALTER) as the authorized control run: empty class 4/4/4, NONE 8/8/8, READ 0/8/8, UPDATE
  0/0/8, ALTER 0/0/0. There was no false 0 for "no profile" or NONE.
- **An AC(1) module in a library that is not on the APF list simply runs unauthorized.** No S047 at load.
  `[tested]`
- **`racf_login()` abends S047 from a program that is not authorized; it does not return an error code.**
  The call does a MODESET to supervisor state unconditionally (SVC 107, INTC 006B inside `racf_login`), so
  no ACEE for another user can be built in that state. `[source: libc370 v2.25.1 src/raclogin.c: the
  supervisor-state test followed by MODESET KEY=ZERO,MODE=SUP]` `[tested]`
- **A started task that is not authorized sees its own ACEE, not the STC user's.** Under RAKF 2.0.0 a
  started task whose user is in a group other than `STCGROUP` gets that group (MVS-SEC-0012): the probe's
  own ACEE showed user `JSPROBS`, group `USER`, `FACILITY SVC244` = 8; the same probe in `STCGROUP` got 0.
  `[tested]`
- **A server that depends on `racf_login()` hangs rather than refusing when it is not authorized.** The
  FTPD 1.2.0 release, started in the non-APF state, answered the connect and `USER` (`220`, `331`),
  gave **no reply at all** to `PASS` for 100 s (the client timed out), and answered `530 Not logged in`
  to the next command; login never reached `230`. `[tested]` FTPD main (commit e039c02, 2026-10-21)
  answers `530` at once in that state (ECO-0021).

## The evidence

Return-code and flag contract (libc370 v2.25.1, `include/mvs/racf.h`): "0 permitted; 4 the resource is not
protected ... Test rc <= 4 for 'may proceed'; 8 not authorized" and "No APF needed (#197)". `[source]`

Probe results (MVS/CE container, container-local, 2026-10-21; RAKF 2.0.0), `racf_auth(acee, "JESSPOOL", ...)`
for READ/UPDATE/ALTER, own ACEE, unauthorized (AC(0) and AC(1) from a non-APF library) equal to the
authorized control:

| JESSPOOL state | READ | UPDATE | ALTER |
|---|---|---|---|
| empty class | 4 | 4 | 4 |
| profile with NONE | 8 | 8 | 8 |
| READ | 0 | 8 | 8 |
| UPDATE | 0 | 0 | 8 |
| ALTER | 0 | 0 | 0 |
| class `NOSUCHCL` (not in the CDT) | 8 | 8 | 8, plus `RAKF0012 UNDEFINED CLASS NOSUCHCL` |

`racf_login(user, NULL, NULL, &rc)` from the same non-APF program: `S047` (MODESET SVC 107, INTC 006B).

## What was not established

- The behaviour of libc370 older than 2.25.1 with the flag byte is a source fact only (libc370#63);
  nothing older was run.
- Why the FTPD 1.2.0 release hangs on `PASS` rather than failing was not traced; the observation is the
  silent 100 s, and the later `530 Not logged in`.
