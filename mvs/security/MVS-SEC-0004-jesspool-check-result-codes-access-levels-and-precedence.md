---
id: MVS-SEC-0004
title: JESSPOOL checks through racf_auth: return codes, access levels and user/group/UACC precedence
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers (RAKF built into the images), 2026-10-21; probe = AC(1) program: racf_login(user, NULL, NULL, &rc), then racf_auth(acee, \"JESSPOOL\", entity, READ|UPDATE|ALTER), one call per attribute, profiles in SYS1.SECURE.CNTL(PROFILES) loaded with S RAKFPROF; libc370 2.25.1"
  - "MVS/CE container with RAKF 2.0.0 installed from the release deck, 2026-10-21: the same 600 checks (4 profile phases x 150 checks) against the image RAKF and against 2.0.0"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/ICHSFR00.hlasm labels ENTYCHCK, ENTYULOP, ENTYCONN/ENTYCON2, ENTYUACC, ENTYEXCP, ENTYFAIL, ENTYWARN"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf, httpd]
tags: [rakf, racf, jesspool, racf_auth, racheck, return-code, access-level, uacc, permit, security]
related: [MVS-SEC-0005, MVS-SEC-0006, MVS-SEC-0007, MVS-SEC-0008, ECO-0020, MVS-SEC-0010]
---

## The claims

- `racf_auth(acee, "JESSPOOL", entity, attr)` returns **0 allowed, 4 no matching profile, 8
  denied**. `[tested]` Where the answers come from in the source: ENTYWARN sets RC 4, ENTYFAIL RC 8,
  AUTHGOOD RC 0. `[source: RAKF v2.0.0 ICHSFR00]`
- The attribute test is "level at or below the profile's level passes": `[tested]`

  | Effective access N | READ | UPDATE | ALTER |
  |---|---|---|---|
  | no JESSPOOL profile in the class, or none matching | 4 | 4 | 4 |
  | `*` UACC NONE, user without permit | 8 | 8 | 8 |
  | N = NONE (via user permit, group permit or UACC) | 8 | 8 | 8 |
  | N = READ | 0 | 8 | 8 |
  | N = UPDATE | 0 | 0 | 8 |
  | N = ALTER | 0 | 0 | 0 |

  CONTROL was not measured.
- **Precedence inside one matched profile** `[tested]` `[source: ICHSFR00 ENTYULOP -> ENTYCONN -> ENTYUACC]`:
  1. An exact **user permit decides alone**. User READ with group ALTER gives READ only; user NONE
     with group ALTER gives 8; user NONE with UACC ALTER gives 8.
  2. Otherwise the **connected groups**: one sufficient group is enough (group NONE plus another
     group UPDATE allows UPDATE). A matched but insufficient group **blocks the UACC**: group NONE
     with UACC ALTER gives 8; group READ with UACC ALTER gives READ only. A user outside the group
     falls to the UACC.
  3. Otherwise the **UACC**.
- A profile line with a blank id is the profile's UACC. `[tested]`
- A change of the profile table after `S RAKFPROF` is effective at the next `racf_auth` call of a
  running process, without a new RACINIT: `R=8` before, `R=0` after the reload, same ACEE. `[tested]`
  Not measured: the cost of one check; an ACEE built before a reload in a long-running server.

## The evidence

Profile line format (measured against existing FACILITY lines; TK5 members carry sequence numbers
in 73-80): class columns 1-8, entity 9-52, user or group id 53-60, access 61-68
(`NONE`, `READ`, `UPDATE`, `ALTER`). `JESSPOOL` fills the class field, so the entity starts directly
in column 9:

```
JESSPOOL*                                                   NONE
JESSPOOL*                                           ADMIN   UPDATE
```

Phase check on the 600-check comparison (phase A no JESSPOOL profiles, B only `*` UACC NONE, C 64
test profiles, D C plus `*` NONE): the result triples were identical on the image RAKF and on
RAKF 2.0.0 for every row of the table above, for user, group and UACC levels and for multi-group
users. The single difference is the undefined class (MVS-SEC-0010). `[tested]`

Messages: a `racf_auth` denial or RC 4 produced no RAKF0005/RAKF000A/RAKF000B in the job log or the
Hercules log; that is a property of the call, see ECO-0020.

Group semantics in detail (default group versus connected groups, the shipped ADMIN pair): MVS-SEC-0008.
