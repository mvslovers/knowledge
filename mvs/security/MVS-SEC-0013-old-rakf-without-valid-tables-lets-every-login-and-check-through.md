---
id: MVS-SEC-0013
title: Old RAKF without valid tables lets every racf_login and racf_auth through as STC/STCGROUP — RAKF 2.0.0 does not start at all
status: tested
platform: [mvs38j]
sources:
  - "Throwaway containers, 2026-10-30 (container-local, not kept): old RAKF 1.2.x as shipped in the TK5 image, and RAKF 2.0.0 as shipped in the MVS/CE image; a small libc370 probe program calling racf_login(), racf_auth() and racf_get_acee(), run against intact tables, a missing member, and an invalid member (as reported in the inbox note; job numbers not carried over)"
  - "RAKF commit 4093978 (V1R2M6 + 20 commits), SRCLIB/ICHSFR00.hlasm, labels RACIERR1 (RAKF0001, RAKF0002, then B RACISSTC) and WTOMSG1/WTOMSG2; SRCLIB/ICHSEC00.hlasm, WTO 'RAKF005I RAKF is already active'"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/ICHSFR00.hlasm, labels RACIERR1, ENTYERR1 (WTOMSG3 = RAKF0003, then AUTHGOOD), WTOMSG1 to WTOMSG3"
verified_on: 2026-10-30
verified_platforms: ["TK5 image RAKF 1.2.x", "MVS/CE image RAKF 2.0.0"]
applies_to: [libc370, ftpd, httpd, mvsmf]
tags: [rakf, racf_login, racf_auth, racf_get_acee, tables, users, profiles, stc, rakf0001, rakf0002, rakf0003, rakf005i, fail-open, security]
related: [MVS-SEC-0009, MVS-SEC-0010, MVS-SEC-0011, ECO-0020]
---

## The claims

- **An old RAKF (1.2.x) that comes up without valid tables answers "allowed" to everything.** `racf_login()`
  returns RC 0 for any userid and any password, and the ACEE it returns belongs to `STC` / `STCGROUP`, not to
  the user asked for. `racf_auth()` returns RC 0 for every class and entity, including a class nobody
  defined. `[tested]`
  `[source: RACIERR1 writes RAKF0001 and RAKF0002, then branches to RACISSTC, the started-task account; the
  same path stands in commit 4093978 and in 2.0.0]` The "tables" are the two members `PROFILES` and `USERS`
  of `SYS1.SECURE.CNTL`.
- **A check of the `racf_auth()` return codes alone cannot detect this state.** The login already succeeds
  for the wrong user. The signs are on the login side: a wrong password or an unknown user that returns RC 0,
  and an ACEE whose user is `STC`. `[tested]`
- **RAKF 2.0.0 does not come up without its tables.** With either table, or both, missing or invalid, JES2
  does not start, so no server task that depends on it starts. There is nothing to query. `[tested]`
  This extends MVS-SEC-0011, which measured invalid tables (garbage content): missing members give the same
  failure on 2.0.0.
- **The open state is made by an IPL or a RAKF restart that loads the tables, not by `S RAKF` on a running
  system.** With a table member missing, `S RAKF` answers `RAKF005I RAKF is already active`, reports
  `IEC141I ... RAKFPROF` (member not found), and the tables in storage stay: wrong password still RC 8,
  checks as before. `[tested]` `[source: ICHSEC00 tests for an existing SAFV and writes RAKF005I]`
  Restoring the member and reloading returns to normal; a long-running server that caches the session
  identity (for example HTTPD) needs a restart afterwards. `[tested]`
- **The healthy return code for an unknown class differs by RAKF version**: 4 on the old RAKF, 8 plus console
  message `RAKF0012 UNDEFINED CLASS <name>` on 2.0.0 (MVS-SEC-0010, ECO-0020). It is at most a supplementary
  signal, not a version-independent test. `[tested]`

## Old RAKF, tables missing or invalid: the evidence

Console messages at startup and during use; the texts are those of `ICHSFR00` (WTOMSG1 to WTOMSG3):

```
RAKF0001 USERID TABLE INVALID OR MISSING
RAKF0002 STC ACCESS ALLOWED: USER: <name>
RAKF0003 RESOURCE TABLE INVALID/MISSING: ALLOWED:STC
RAKF0009 STC ,<job> ,<class>,<entity>        (once per authorisation check)
```

`RAKF0001` is reported for the user table even if only the resource table is invalid. `[tested]`

Probe results in this state (`racf_rc` is the return code of `racf_login`; the three codes of a check are for
READ / UPDATE / ALTER):

```
STC ACEE (racf_get_acee): user=STC group=STCGROUP
LOGIN <valid user>, no password        -> racf_rc=0   ACEE user=STC group=STCGROUP
LOGIN <unknown user>, any password     -> racf_rc=0   ACEE user=STC
LOGIN <valid user>, wrong password     -> racf_rc=0   ACEE user=STC
CHECK FACILITY  <entity>               -> 0 / 0 / 0
CHECK DATASET   <dsn>                  -> 0 / 0 / 0
CHECK JESSPOOL  <entity>               -> 0 / 0 / 0
CHECK <undefined class> <entity>       -> 0 / 0 / 0
```

Healthy comparison, tables in place, same probe:

```
LOGIN <valid user>, no password        -> racf_rc=0   ACEE user = requested user, own group
LOGIN <unknown user>                   -> racf_rc=28  ACEE NULL
LOGIN <valid user>, wrong password     -> racf_rc=8   ACEE NULL
```

Healthy `racf_auth()` on the old RAKF for a class that is defined nowhere: 4 / 4 / 4. A class with no
matching profile (here JESSPOOL) also returns 4 / 4 / 4.

RAKF 2.0.0 with a member missing, console:

```
IEC141I 013-18 ... RAKFPROF / RAKFUSER      (member not found)
RAKF0001 USERID TABLE INVALID OR MISSING
RAKF0002 STC ACCESS ALLOWED: USER: ~ ~
IEA911E COMPLETE DUMP ON SYS1.DUMP00 FOR ASID(0002)
IEF174I SYSTEM ERROR BEFORE JOB INITIATION
```

Healthy 2.0.0: unknown class 8 / 8 / 8 plus `RAKF0012`; defined class without a matching profile 4;
login as in the healthy comparison above (unknown user 28, wrong password 8).

| Situation | `racf_login` | `racf_auth` |
|---|---|---|
| Old RAKF, tables ok, unknown user / wrong password | 28 / 8, ACEE NULL | n/a |
| Old RAKF, tables ok, unknown class | n/a | 4 |
| RAKF 2.0.0, tables ok, unknown class | n/a | 8 (+ `RAKF0012`) |
| Old RAKF, tables missing or invalid | 0 for everything, ACEE `STC`/`STCGROUP` | 0 for everything |
| RAKF 2.0.0, tables missing or invalid | system does not start | system does not start |

## Not established

- The abend code of the JES2 failure on 2.0.0 without tables was not analysed. The link to the missing tables
  rests on the variants in which only one table was affected and on the control run with intact tables; the
  mechanism was not read in the source.
- RAKF not active at all (no RCVT connection), and RACF instead of RAKF.

Container results with a probe program, not a stand result.
