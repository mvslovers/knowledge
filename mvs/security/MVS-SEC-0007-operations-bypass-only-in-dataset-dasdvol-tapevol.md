---
id: MVS-SEC-0007
title: RAKF OPERATIONS (ACEEOPER) bypasses nothing outside DATASET, DASDVOL and TAPEVOL
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers (RAKF built into the images), 2026-10-21: probe users with oper flag Y (aceeflg1 0x61), the images' IBMUSER (MVS/CE) and HERC01 (TK5); control on DATASET ZQPRIV.* NONE"
  - "MVS/CE container with RAKF 2.0.0 (release deck), 2026-10-21 (oper user, class JESSPOOL) and 2026-10-22 (oper user in group USER, MVS-SEC-0008 fixtures)"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/ICHSFR00.hlasm label ENTYOPER (comment: users with OPERATIONS may use all resources in the DATASET, DASDVOL and TAPEVOL class)"
  - "Rob Prins (RAKF maintainer), 2026-10-22: OPERATIONS gives access only in DATASET, TAPEVOL and DASDVOL, as in IBM's RACF (his statement)"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf]
tags: [rakf, operations, aceeoper, jesspool, facility, dataset, security]
related: [MVS-SEC-0001, MVS-SEC-0004, MVS-SEC-0008]
---

## The claims

- Users with `ACEEOPER` set (`aceeflg1` = `0x61`) get **RC 8 for READ, UPDATE and ALTER in JESSPOOL**
  under `*` NONE and under a specific NONE profile. The control with the same users on DATASET
  `ZQPRIV.*` NONE returns 0/0/0. `[tested]` (image RAKF and RAKF 2.0.0, MVS/CE; the images' own
  IBMUSER (MVS/CE) and HERC01 (TK5) behave like the probe user.)
- The source agrees: the operator test (ENTYOPER) is reached only from the UACC check (UACC
  insufficient), and it compares the class with `DATASET`, `DASDVOL` and `TAPEVOL`; every other
  class goes to ENTYFAIL. `[source: RAKF v2.0.0 ICHSFR00 ENTYOPER/ENTYOPR2]`
- **A matched but insufficient user or group entry never reaches the operator test, in any class**:
  ENTYEXCP and the group loop (`WORKOPRB`) go straight to ENTYFAIL. `[source]` (Only the source says so; not
  measured for DATASET.)
- An operator user is therefore denied in FACILITY and JESSPOOL like anyone else; access must come
  from a permit or the UACC. A group with a permit grants (the `ADMIN` group of the shipped
  profiles), an operator flag in USERS does not. `[tested]`
- On a RAKF 2.0.0 container, a user in group USER with OPERATIONS `Y` got 8/8/8 on all six test
  entities of MVS-SEC-0008, while members of ADMIN without OPERATIONS got 0/0/8. `[tested]`
- Maintainer statement (not measured by us): OPERATIONS gives access only in DATASET, TAPEVOL and
  DASDVOL, as in IBM's RACF. TAPEVOL is in the source list; no TAPEVOL check was run here.
  `[attributed]`

## Where the flag does work

DATASET access without a permit: ENTYOPR2 tests `TM ACEEFLG1,ACEEOPER`; the message
`RAKF0007 ACCESS ALLOWED VIA OPERATIONS` is written only for the userid `PROD` (MVS-SEC-0001).
How the two operator flags relate: MVS-SEC-0001.
