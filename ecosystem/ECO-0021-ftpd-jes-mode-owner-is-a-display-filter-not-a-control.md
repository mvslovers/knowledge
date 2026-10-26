---
id: ECO-0021
title: FTPD in JES mode — the owner is a client-set display filter, any logged-in user can fetch or purge any job; login is gated by FACILITY FTPAUTH
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01) throwaway containers, 2026-10-21 (container-local), two users per system, twelve jobs per user and system (IEBGENER; TYPRUN=HOLD for the waiting ones; job names with and without the userid prefix, owner and name prefix crossed). FTPD built from main of 2026-10-21; JOB/STC numbers are container-local (an FTPD started task, a job purged with DELE: 250)"
  - "mvslovers/ftpd origin/main d9c88fa (2026-10-22): src/ftpd#jes.c (job_matches_owner, ftpd_jes_list, ftpd_jes_retrieve, ftpd_jes_delete: jescanj, CANJ_ICAN), src/ftpd#sit.c (site_keywords, JESOWNER, JESINTERFACELEVEL comment), src/ftpd#aut.c (FACILITY FTPAUTH check, unauthorized-server answer; commit e039c02, 2026-10-21)"
  - "mvslovers/ftpd release v1.2.0 (2026-10-13): src/ftpd#jes.c, src/ftpd#aut.c"
  - "mvslovers/ftpd#90 (open): JES spool access has no authorization model; mvslovers/ftpd#82 (closed): racf_auth RC 4 treated as allowed"
verified_on: 2026-10-21
applies_to: [ftpd]
tags: [ftpd, jes, spool, authorization, jesowner, jescanj, ftpauth, facility, rakf, ftpd-90]
related: [MVS-SEC-0003, MVS-SEC-0005, MVS-JES2-0001, MVS-JES2-0002, ECO-0015, ECO-0020, ECO-0022]
---

## Which FTPD this is

The latest FTPD release is **v1.2.0** (2026-10-13). No 1.3.0 release exists. **Correction
2026-10-26:** FTPD v1.3.0 was published on 2026-10-22 (tag commit 6b6367d); it contains commit
`e039c02` and so the unauthorized-server answer below. `[source: git tag v1.3.0 and release page]`
The JES behaviour below was
measured with the main branch of 2026-10-21 and is true of main `d9c88fa` (2026-10-22) as read in source;
the v1.2.0 tag has the same spool code. `[source: v1.2.0 and d9c88fa, src/ftpd#jes.c]` The one visible
difference between the tag and main is the unauthorized-server answer (below).

## The claims

- **The owner is only a display filter.** `jes_owner` defaults to the login userid; `SITE JESOWNER=*`
  lists every job and `SITE JESOWNER=<prefix>` filters on a prefix of the owner field (the compare is
  `strncmp` over the filter's length; a job with an empty owner is matched by `*` only, see
  MVS-JES2-0002). The value is stored upper-case. `[source: src/ftpd#jes.c job_matches_owner]` `[tested]`
- **`RETR` of any spool document and `DELE` of any job work for any logged-in user,** operator or not.
  `DELE` calls `jescanj(jobname, jobid, 1)` (purge) and answers `250 Cancel successful`. The default
  listing is filtered by owner; the by-jobid paths are not. `[tested]` (a TK5 user purged a job owned by
  another user with `DELE`: 250). `[source: ftpd_jes_delete]`
- **The only refusal is for an active started task:** `550 Access denied - cannot cancel STC00033`, which
  is FTPD's mapping of the `CANJ_ICAN` return of `jescanj`; FTPD itself makes no authorization check.
  TSO refuses the same cancel to the operator too (MVS-SEC-0003). `[tested]` `[source: ftpd_jes_delete]`
- **Nothing in the path asks RAKF.** There is no JESSPOOL check; the class is not consulted by FTPD, so
  the profiles of MVS-SEC-0004 and MVS-SEC-0005 have no effect on it. The open decision is
  mvslovers/ftpd#90. `[source: src/ftpd#jes.c at d9c88fa and v1.2.0: no racf_auth call in the spool
  functions]`
- **Login is gated by the FACILITY profile `FTPAUTH`.** The check is `racf_auth(acee, "FACILITY",
  "FTPAUTH", READ)`; RC 4 (no profile) counts as allowed (mvslovers/ftpd#82, ECO-0020). The default in
  both images grants ADMIN READ only, so a user in group USER gets `530 Not authorized for FTP access.`
  `[tested]` on MVS/CE and TK5 (the test user was given `FTPAUTH` READ for group USER in the container's
  `SYS1.SECURE.CNTL(PROFILES)` to get in).
- **An FTPD that is not APF-authorized: the release hangs, main answers.** The v1.2.0 release gives no
  reply to `PASS` for 100 s and then `530 Not logged in`; the unauthorized `racf_login` abends S047
  (ECO-0020), which is what main's comment in `aut.c` names as the reason for its change.
  Main, since commit `e039c02` (2026-10-21), answers `530 Login not possible: FTPD is not APF
  authorized...` at once and keeps the session usable (`USER`, `SYST`, `NOOP`, `QUIT`).
  The mechanism of the silent `PASS` (a second S047 inside the command recovery) is ECO-0015.
  `[source: src/ftpd#aut.c at d9c88fa]` `[tested]` for the release's hang; the main answer is source only (not run).
- **`SITE JESINTERFACELEVEL` is not accepted:** FTPD answers it as an unrecognized parameter, as z/OS does
  for a client that tries to change a server setting. What the level governs on z/OS (who may see and fetch
  another user's spool) is not implemented. `[source: src/ftpd#sit.c at d9c88fa]`
- **Reading the output of a started task works for non-operators.** The first read of the FTPD STC log
  failed once (`550 Spool data set for STC... no longer available.`); later reads worked. `[tested]` (the
  first failure was not explained).

## The evidence

TK5 container: a job of one user purged by another user through FTPD `DELE` (`250 Cancel successful`);
the FTPD STC refused with `550 Access denied - cannot cancel STC00043`. MVS/CE container: the FTPD
STC refused as `550 Access denied - cannot cancel STC00033`; a spool document of a foreign job fetched with
`RETR` by a normal user. Container-local numbers.

## Limits

- Container results, not a stand. The MVS/CE image has the products copied in; TK5 has them SMP-installed
  (ECO-0007).
- Waiting jobs were modelled with TYPRUN=HOLD; no truly running batch job was used.
- Only TSO's OPER/NOOPER flip was measured (MVS-SEC-0001); other operator notions (RACF OPERATIONS,
  console authority) were not measured against FTPD.
- The same spool gap on the REST side: ECO-0022.
