# FTPD (main 5f5734b, 1.3.0-DEV) without APF and without SVC 244: PASS is swallowed, not hung

Source: Paperclip MVS-345 (follow-up to MVS-343), MVS/CE throwaway container on mvsdev, RAKF 2.0.0.
Container result, not a stand result. Date 2026-10-21.

## Setup
- FTPD built from origin/main (5f5734b), deployed to a non-APF library (FTPD.DEV.LINKLIB) as the only STEPLIB.
- `FACILITY SVC244` READ for STCGROUP removed from SYS1.SECURE.CNTL(PROFILES), `S RAKF`.
  (The container's RAKF 2.0.0 does not map the STC name FTPD to *USER at start: RAKF0010I "DEFAULT STC ACCOUNT",
  FTPD004I "STC RUNS AS STC/STCGROUP". So the identity is STC/STCGROUP, with SVC244 denied.)
- Startup: `RAKF0005`/`RAKF000A STC,FTPD,FACILITY,SVC244`, `FTPD003W APF SETUP FAILED RC=4`, then FTPD001I READY.

## Measured
- 220 and 331 come at once. PASS gets no reply at all: not within 240 s, not ever. The next command on the same
  connection is answered immediately (NOOP 200, PWD 530 Not logged in). So the session thread is NOT hung; the
  PASS command just ends without a reply. PASS repeated: each one silent, the attempt counter never advances.
- Only the idle timeout ends it: `421 Idle timeout, closing connection` after 303 s (IDLETIMEOUT 300).
- Three PASS in a row (no other command in between): `FTPD071E SESSION SOCKET=n CLOSED AFTER 3 CONSECUTIVE ABENDS`
  on the console, socket closed with no reply. A NOOP in between resets the counter, so a client that
  alternates never gets closed.
- STDOUT of the STC has no "RAKF login failed" line and the console has no FTPD070E at all: racf_login never
  returned, and the recovery handler never reached its WTO / reply.
- Other sessions are served normally up to PASS (greeting, USER). The listener and the worker pool are fine.
- Control: SVC244 READ for STCGROUP restored, `S RAKF`, restart of the same load module from the same
  non-APF library: `FTPD008I AUTHORIZED BY SVC (MODULE KEY 8)`, PASS 230 in 0.09 s.

## Why (source read, libc370 src/mvs/racf, ftpd#ses.c)
- `racf_login()` (raclogin.c) does `MODESET KEY=ZERO,MODE=SUP` unless TESTAUTH says supervisor state: an
  unauthorized caller gets S047, not an error code (MVS-343: INTC 006B).
- The command runs under `try(ftpd_run_command ...)` (ftpd#ses.c:667). The abend is caught and
  `try(ftpd_session_recover ...)` (ftpd#ses.c:675) runs. Its step 1 is `racf_set_acee(stc_acee)` (ftpd#ses.c:429),
  and `racf_set_acee()` (racsacee.c) also does `MODESET KEY=ZERO,MODE=SUP` -> S047 again, inside the recovery.
  The outer `try()` swallows it ("Contain a re-ABEND during recovery itself"), so FTPD070E (step 3) and the
  client reply (step 4) are never reached. The loop then `continue`s.
- Consequence: the docs say "the commands that need authorization fail one by one and say so"
  (docs/installation.md, ug-install.typ, ref-stc.typ); for the login that is not true.

Clean exits that exist in principle: refuse to start (or do not answer READY) when apf_rc != 0; or answer
`421`/`530` in ftpd_auth_pass before racf_login when the task is not authorized; or reorder recover so the reply
precedes racf_set_acee (and make racf_set_acee conditional on authorization).

## Addendum 2026-10-22: fixed in FTPD, the libc370 finding stays

FTPD fixed the swallowed PASS with mvslovers/ftpd#258 (PR #259, merged to main): without APF, `ftpd_auth_pass` now answers `530` before calling `racf_login`. This was read in the code, not re-measured on MVS.

The general finding still holds for every program: libc370 `racf_login()` and `racf_set_acee()` issue `MODESET KEY=ZERO,MODE=SUP` and end with S047 in an unauthorized caller instead of returning an error code, and a second abend inside a `try()` recovery path is swallowed without a trace. Check authorization before calling them, and never call them from a recovery routine of a program that may run unauthorized.
