---
id: MVS-JES2-0002
title: JESJOB.owner from jesjob(): empty for a reader job without USER, SYSTEM for every started task
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway container, 2026-10-21: AC(1) probe from SYS2.LINKLIB calling jesjob() (libc370 <mvs/jes2.h>), batch jobs with and without USER on the job card, started tasks HTTPD, FTPD, UFSD, NET, INIT, TSO, RAKFPROF; 77 queue entries listed; output container-local and not kept"
  - "libc370 tag v2.25.1 (commit 82016ba), include/mvs/jes2.h struct jesjob (unsigned char owner[9], offset 1A), src/mvs/jes2/jesjob.c lines 168-183 (TSO job: owner = job name; STC: 'SYSTEM'; batch: JCTUSEID, empty if not above blank)"
  - "mvslovers/mvsmf tag v1.3.0 (commit d454edf), src/jobsapi.c lines ~1813-1865 (owner completed from the submitter when the job comes back without one)"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf]
tags: [jes2, jesjob, owner, jctuseid, started-task, reader, jesspool, jes-spool]
related: [MVS-SEC-0006, MVS-SEC-0008, MVS-JES2-0001, ECO-0021, ECO-0022]
---

## The claims

- `JESJOB.owner` is `unsigned char[9]`, **NUL-terminated and not blank-padded**; the bytes after the name are
  `X'00'`. `[tested]` `[source: jes2.h offset 1A; jesjob.c cutblank(owner)]`
- A batch job with `USER` on the job card: owner = that user (for example `IBMUSER`, strlen 7). `[tested]`
- **A batch job submitted through the reader without USER/PASSWORD has an empty owner** (strlen 0, all nine bytes
  `X'00'`). Reproducible. `[tested]` `[source: jesjob.c copies JCTUSEID and sets owner[0]=0 when it is not above a
  blank; the code comment says the USERID= of the job card is only seen later, in the internal text]`
- **Every started task has the owner `SYSTEM`** (strlen 6): HTTPD, FTPD, UFSD, NET, INIT, TSO, RAKFPROF and others,
  also those started under their own RAKF user. `[tested]` `[source: jesjob.c: JCTSTCJB -> strcpy(owner, "SYSTEM")]`
  A TSO user's own job gets its job name as owner (`JCTTSUJB`). `[source]`
- JES2 and MSTR themselves are not in the queue: 77 entries listed, none of them JES2 or MSTR. `[tested]`
- Consequences for a JESSPOOL entity built as `<owner>.<jobname>.<jobid>`: `[inferred]`
  - an empty owner gives an entity that starts with `.` and is caught only by a `*` or `.*` profile (MVS-SEC-0006);
  - the owner `SYSTEM` is a literal, not a RAKF user: `SYSTEM` is not in the shipped USERS and `racf_login` for it returns no ACEE (MVS-SEC-0012).
- mvsMF v1.3.0 completes an empty owner from the authenticated submitter on its submit response; it reports the
  caller as owner only for the job it just submitted. `[source: jobsapi.c]`

## The evidence

JESSPOOL checks of an empty-owner entity are in MVS-SEC-0006 (`.JOBA.JOB00001` against `.*` and `*` profiles) and
MVS-SEC-0008 (`.JOBD.JOB00015`, no owner, 0/0/8 for ADMIN under fixture 1 and 8/8/8 for a user without a row).
Container result, not a stand result.
