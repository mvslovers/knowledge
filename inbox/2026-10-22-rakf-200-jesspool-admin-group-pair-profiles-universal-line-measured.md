# RAKF 2.0.0: group-based access to JESSPOOL profiles, pair profiles, mandatory universal line (measured)

Measured 2026-10-22 on one throwaway MVS/CE container (not a stand), built from the `mvsce:dev` image that ships
RAKF 2.0.0 (TK5 Update 6, TRKF200) after mvs-docker#27. Paperclip issue MVS-360 (follows MVS-326, MVS-332, MVS-343).
Probe JSPROBE: AC(1) (copied to SYS2.LINKLIB), libc370 2.25.1, `racf_login(user, NULL, group, &rc)` without
password, then `racf_auth(acee, "JESSPOOL", entity, READ|UPDATE|ALTER)`. RC 0 = allowed, 8 = denied, 4 = no profile.
Image check by content, not by banner: an undefined class (`NOSUCHCL`) gives RC 8 + `RAKF0012 UNDEFINED CLASS`
(the older RAKF in the base image gives RC 4). Entity cap 8 characters (CDT length byte), see the MVS-332 notes.

## Users table as shipped, and the group semantics

`SYS1.SECURE.CNTL(USERS)` of the image: `IBMUSER` and `MVSCE01` each have two lines, `ADMIN` and `RAKFADM`, **both**
with `*` in column 18 (the default-group flag, `DFLTGRPF` in CJYRUIDS). Both are in ADMIN. ACEE after RACINIT:
`defgrp=RAKFADM`, connected groups `ADMIN RAKFADM` (the loader takes the last flagged line in sorted order as the
default group). So on the shipped image ADMIN is a **connected** group of the two admins, not their default group.

Source (ICHSFR00, `ENTYULOP`/`ENTYCONN`): the check goes through the **user** entries of the profile first (a match
decides alone), then through **every connected group** (`ACEECGRP`), which holds one entry per USERS line, the default
group included. ACEEGRP (the default group name) is not consulted. Measured consequences:

| Case (USERS) | ACEE | ADMIN row of `JESSPOOL*` effective? |
|---|---|---|
| ADMIN connected only (IBMUSER, MVSCE01 as shipped: default RAKFADM) | defgrp=RAKFADM conn=ADMIN RAKFADM | yes, 0/0/8 |
| ADMIN as the only group (MIKE3, MVSCE01 reduced to one `ADMIN *` line) | defgrp=ADMIN conn=ADMIN | yes, 0/0/8 |
| ADMIN connected, default USER (MIKE5: `ADMIN` and `USER *`) | defgrp=USER conn=ADMIN USER | yes, 0/0/8 |
| ADMIN without OPERATIONS (MIKE3, MIKE5: oper N) | oper=0 | yes: the group grants, ACEEOPER is not needed |
| USER group with OPERATIONS Y (MIKE4) | oper=1 | no, 8/8/8: ACEEOPER is no bypass in JESSPOOL |
| not in ADMIN, `racf_login(.., group="ADMIN")` (MIKE1) | defgrp=USER (request ignored), conn=USER | no, 8/8/8 |

A group that is requested but not connected gives nothing. The requested group was not even taken over into the
ACEE by this libc370/RAKF combination.

## Fixture 1 (`JESSPOOL*` NONE; `JESSPOOL*` ADMIN UPDATE)

READ/UPDATE/ALTER, entities `MIKE1.JOBA.JOB00012`, `MIKE2.JOBB.JOB00013`, `IBMUSER.JOBC.JOB00014`,
`SYSTEM.JES2.JOB00001`, `.JOBD.JOB00015` (no owner), `MIKE10.JOBE.JOB00016`: users in ADMIN (any way) **0/0/8** on all six,
users not in ADMIN (also with OPERATIONS) **8/8/8** on all six. Without any JESSPOOL profile: 4/4/4 for everybody.

## Fixture 2 (pair MIKE1/MIKE2, correct)

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

Notes: the owner's own job is **not** covered by the profile (the owner has no row in his own block), so "own job" has
to be decided by the caller before `racf_auth`, or by an own row. `MIKE10.…` is not caught by `MIKE1.*` (the
profile prefix is `MIKE1.`). The profile `MIKE1.*` and the cut entity `MIKE1.JO` match as before.

## Fixture 2 without the ADMIN rows in the two owner blocks

The last matching profile wins and a profile that matches the entity but has no row for the caller's group falls to
its own UACC (NONE): ADMIN members get **8/8/8** on jobs of MIKE1 and MIKE2, still 0/0/8 on IBMUSER, SYSTEM, ownerless and
MIKE10 jobs (they fall to `JESSPOOL*`). MIKE1/MIKE2 unchanged.

## Fixture 3 (no universal rows in the blocks, no ADMIN in the blocks) and a variant

`S RAKFPROF` with
```
JESSPOOL* NONE / JESSPOOL* ADMIN UPDATE / JESSPOOLMIKE1.* MIKE2 UPDATE / JESSPOOLMIKE2.* MIKE1 UPDATE
```
console: `RAKFPROF8 JESSPOOLMIKE1.*   MIKE2   UPDATE` (the offending record),
`RAKFPROF4  PERMIT RECORD WITHOUT UNIVERSAL ACCESS RECORD`, `RAKFPROF4  **  PROGRAM TERMINATED  **`,
`IEF450I RAKFPROF RAKFPROF - ABEND S000 U0400`. **The old chain stays active** (probe afterwards identical to the
previous load: ADMIN 8 on the blocks of MIKE1 and MIKE2 because the previous load was the no-ADMIN variant).
Variant with only `JESSPOOL*` missing its universal row (all blocks complete): the same message for
`JESSPOOL*  ADMIN  UPDATE`, U0400. Recovery without IPL: write the correct file, `S RAKFPROF` -> `RAKFPROF7  RAKF PROFILES UPDATED`,
probe shows the new chain. The broken file must not be left in `SYS1.SECURE.CNTL(PROFILES)`: with RAKF 2.0.0 an IPL
with an invalid table does not start JES2 (see the MVS-332 note); not re-measured here.

## Limits

Container result, not a stand result. One image, RAKF 2.0.0 only. Entities are strings given to `racf_auth`; no
real job of these owners existed. IPL with the broken file was not repeated. In the measured USERS the MVP line
`*ADMIN` (group field starting with `*`) was dropped while rewriting the table (does not matter for the probes).
Raw outputs: Paperclip scratch directory of MVS-360 (not kept).
