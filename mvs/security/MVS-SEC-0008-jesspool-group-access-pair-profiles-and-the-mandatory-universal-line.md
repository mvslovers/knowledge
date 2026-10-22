---
id: MVS-SEC-0008
title: RAKF 2.0.0 JESSPOOL: access through connected groups, owner-pair profiles and the mandatory universal line
status: tested
platform: [mvs38j]
sources:
  - "One throwaway MVS/CE container built from an image that ships RAKF 2.0.0 (mvslovers/mvs-docker#27), 2026-10-22; probe: AC(1) program from SYS2.LINKLIB, libc370 2.25.1, racf_login(user, NULL, group, &rc) without password, then racf_auth(acee, \"JESSPOOL\", entity, READ|UPDATE|ALTER); raw outputs not kept"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/ICHSFR00.hlasm ENTYULOP/ENTYCONN, SRCLIB/CJYRUIDS.hlasm DFLTGRPF, SRCLIB/CJYRPROF.hlasm NOUAR/PERMINVL"
verified_on: 2026-10-22
applies_to: [ftpd, mvsmf, libc370]
tags: [rakf, rakf-2.0.0, jesspool, group, acee, connected-groups, pair-profile, universal-access, u0400, security]
related: [MVS-SEC-0004, MVS-SEC-0005, MVS-SEC-0006, MVS-SEC-0007, MVS-SEC-0009, MVS-SEC-0010, MVS-JES2-0002]
---

## The claims

- **The check goes through the user entries of the profile first, then through every connected
  group (`ACEECGRP`), then the UACC.** `ACEEGRP` (the default group name) is not consulted. The
  connected groups hold one entry per USERS line of the user, the default group included.
  `[source: ICHSFR00 ENTYULOP / ENTYCONN]` `[tested]`
- **The default group of a user is the last USERS line flagged `*` in column 18, in sorted order.**
  The image's own `USERS` has two lines for IBMUSER and MVSCE01 (`ADMIN` and `RAKFADM`) with `*` on both;
  after RACINIT the ACEE has `defgrp=RAKFADM`, connected groups `ADMIN RAKFADM`. ADMIN is a connected
  group there, not the default group. `[tested]` `[source: CJYRUIDS DFLTGRPF]`
- **A group that is requested but not connected grants nothing**, and the request is not taken over
  into the ACEE: `racf_login(.., group="ADMIN")` for a user not in ADMIN gave `defgrp=USER`,
  `conn=USER`, and 8/8/8. `[tested]`
- A group permit grants, the operator flag does not (MVS-SEC-0007). `[tested]`
- **A permit record without a universal-access record aborts the load with `U0400`**, and the
  previous table stays active. `[tested]` `[source: CJYRPROF NOUAR]`

## The evidence

Does the ADMIN row of `JESSPOOL*` take effect? (result triple READ/UPDATE/ALTER)

| Case (USERS) | ACEE | ADMIN row of `JESSPOOL*` effective? |
|---|---|---|
| ADMIN connected only (IBMUSER, MVSCE01 as shipped: default RAKFADM) | defgrp=RAKFADM conn=ADMIN RAKFADM | yes, 0/0/8 |
| ADMIN as the only group (`ADMIN *` line only) | defgrp=ADMIN conn=ADMIN | yes, 0/0/8 |
| ADMIN connected, default USER (`ADMIN` and `USER *`) | defgrp=USER conn=ADMIN USER | yes, 0/0/8 |
| ADMIN without OPERATIONS (oper N) | oper=0 | yes: the group grants, ACEEOPER is not needed |
| group USER with OPERATIONS Y | oper=1 | no, 8/8/8 |
| not in ADMIN, `racf_login(.., group="ADMIN")` | defgrp=USER (request ignored), conn=USER | no, 8/8/8 |

**Fixture 1** (`JESSPOOL*` NONE; `JESSPOOL*` ADMIN UPDATE), entities `MIKE1.JOBA.JOB00012`,
`MIKE2.JOBB.JOB00013`, `IBMUSER.JOBC.JOB00014`, `SYSTEM.JES2.JOB00001`, `.JOBD.JOB00015` (no owner),
`MIKE10.JOBE.JOB00016`: users in ADMIN (any way) 0/0/8 on all six; users not in ADMIN (also with
OPERATIONS) 8/8/8 on all six. Without any JESSPOOL profile: 4/4/4 for everybody.

**Fixture 2** (correct pair profiles for MIKE1/MIKE2):

```
JESSPOOL*  NONE            JESSPOOL*  ADMIN UPDATE
JESSPOOLMIKE1.*  NONE      JESSPOOLMIKE1.*  ADMIN UPDATE   JESSPOOLMIKE1.*  MIKE2 UPDATE
JESSPOOLMIKE2.*  NONE      JESSPOOLMIKE2.*  ADMIN UPDATE   JESSPOOLMIKE2.*  MIKE1 UPDATE
```

| User \ job of | MIKE1 | MIKE2 | IBMUSER | SYSTEM | no owner | MIKE10 |
|---|---|---|---|---|---|---|
| ADMIN members | 0/0/8 | 0/0/8 | 0/0/8 | 0/0/8 | 0/0/8 | 0/0/8 |
| MIKE1 | **8/8/8** (own job) | 0/0/8 | 8/8/8 | 8/8/8 | 8/8/8 | 8/8/8 |
| MIKE2 | 0/0/8 | **8/8/8** (own job) | 8/8/8 | 8/8/8 | 8/8/8 | 8/8/8 |
| MIKE4 (oper Y, USER) | 8 | 8 | 8 | 8 | 8 | 8 |

- The owner's own job is **not** covered by the profile (the owner has no row in his own block):
  "own job" must be decided by the caller before `racf_auth`, or by an own row.
- `MIKE10.…` is not caught by `MIKE1.*` (the profile prefix is `MIKE1.`); the cut entity `MIKE1.JO`
  still matches as in MVS-SEC-0005.

**Fixture 2 without the ADMIN rows in the two owner blocks:** the last matching profile wins and a
profile that matches the entity but has no row for the caller's group falls to its own UACC (NONE).
ADMIN members get 8/8/8 on the jobs of MIKE1 and MIKE2, still 0/0/8 on IBMUSER, SYSTEM, ownerless
and MIKE10 jobs (they fall to `JESSPOOL*`). MIKE1 and MIKE2 unchanged.

**Fixture 3** (no universal rows in the blocks, no ADMIN in the blocks): `S RAKFPROF` with

```
JESSPOOL* NONE / JESSPOOL* ADMIN UPDATE / JESSPOOLMIKE1.* MIKE2 UPDATE / JESSPOOLMIKE2.* MIKE1 UPDATE
```

console:

```
RAKFPROF8 JESSPOOLMIKE1.*   MIKE2   UPDATE
RAKFPROF4  PERMIT RECORD WITHOUT UNIVERSAL ACCESS RECORD
RAKFPROF4  **  PROGRAM TERMINATED  **
IEF450I RAKFPROF RAKFPROF - ABEND S000 U0400
```

The old chain stays active (the probe afterwards was identical to the previous load). A variant with only
`JESSPOOL*` missing its universal row gave the same message for `JESSPOOL*  ADMIN  UPDATE`, U0400.
Recovery without IPL: write the correct file, `S RAKFPROF` -> `RAKFPROF7  RAKF PROFILES UPDATED`,
the probe shows the new chain. Do not leave a broken file in `SYS1.SECURE.CNTL(PROFILES)`: an IPL with an
invalid table does not start JES2 on RAKF 2.0.0 (MVS-SEC-0011; not re-measured here).

## Limits

Container, one image, RAKF 2.0.0 only; entities are strings given to `racf_auth`, no real job of
these owners existed. In the measured USERS the line `MVP *ADMIN` (group field starting with `*`) was dropped
while rewriting the table, which does not matter for the probes.
