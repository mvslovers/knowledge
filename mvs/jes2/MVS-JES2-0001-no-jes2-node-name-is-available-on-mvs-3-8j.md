---
id: MVS-JES2-0001
title: No JES2 node name is available on MVS 3.8j images, so a JESSPOOL resource cannot carry one
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01) throwaway containers, 2026-10-21: JES2 console commands, init decks (MVS/CE SYS1.PARMLIB(JES2PM00); TK5 SYS1.JES2PARM(JES2PARM) and STARTSTD), TSO STATUS, mvsMF job JSON; output container-local and not kept"
  - "mvslovers/mvsmf tag v1.3.0 (commit d454edf), src/jobsapi.c process_job: JSON fields subsystem, jobname, jobid, owner, type, class, url, files-url, status"
verified_on: 2026-10-21
applies_to: [ftpd, mvsmf, libc370]
tags: [jes2, node, ownnode, numnode, nje, jesspool, console, tso-status, jes-spool]
related: [MVS-SEC-0005, MVS-JES2-0002, ECO-0021, ECO-0022]
---

## The claims

- **No JES2 node name is available on either image.** `[tested]`
  - `$D NJEDEF`, `$D NODE(1)`, `$D N`, `$D N1` and `$D NODE` return a job display, because JES2 on 3.8j parses
    `$D` followed by such a token as a job display ("PRT LOCAL PUN LOCAL PRIO 1 ANY" for the oldest job).
  - `$D MASDEF`, `$D SID`, `$D SPOOL`: `INVALID OPERAND`; `$D CKPT`, `$D LINE(1)`: `INVALID COMMAND`;
    `$D JES2`: `JOB(S) NOT FOUND`.
- **The init decks contain no `OWNNODE`, `NUMNODE` or `NODE` statement** (MVS/CE `SYS1.PARMLIB(JES2PM00)`; TK5
  `SYS1.JES2PARM(JES2PARM)` and `STARTSTD`). TK5 has only a comment line `&NUMNODE &OWNNODE &TGSIZE`; changes
  there need a cold start. Neither image has NJE38 data sets. `[tested]`
- **What exists instead:** the route name `LOCAL` and the SMF system id in `$HASP373` (`SYS MVSC` on MVS/CE, `SYS TK5R`
  on TK5). TK5 also has DESTIDs RMT01 to RMT04. `[tested]`
- **No client surface shows a node.** TSO `STATUS <jobname>` prints only
  `IKJ56192I JOB <name>(JOB000nn) ON OUTPUT QUEUE`. The mvsMF job JSON has no node field. `[tested]`
  `[source: mvsMF v1.3.0 process_job lists only subsystem, jobname, jobid, owner, type, class, url, files-url, status]`
- **Consequence for JESSPOOL:** the z/OS resource name is `<nodeid>.<userid>.<jobname>.<jobid>.<dsid>`; a name
  for this platform has no node to put first, and with the 8-character entity cap (MVS-SEC-0005) every
  character spent on a constant prefix is taken from the owner. `[inferred]` from the facts here and in
  MVS-SEC-0005.

## Not measured

RFE could not be measured: it is full-screen (`REVIEW TERMINATED BECAUSE TERMINAL IS NOT A 3270 DISPLAY` in batch)
and no 3270 client was available. `STATUS` without an operand abends S0C1 in batch TSO on both images
(MVS-SEC-0003). Container results, not stand results.
