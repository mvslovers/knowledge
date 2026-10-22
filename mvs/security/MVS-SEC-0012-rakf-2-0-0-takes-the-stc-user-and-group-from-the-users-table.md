---
id: MVS-SEC-0012
title: RAKF 2.0.0 takes the user and group of a started task from the USERS table
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway container with RAKF 2.0.0 installed from the release deck, 2026-10-21: HTTPD and FTPD started tasks before and after changing their USERS lines; MVS/CE container, 2026-10-21, probe run as batch and as started task from a library that is not APF-authorized"
  - "RAKF v2.0.0 (commit 019acf4): SRCLIB/ICHSFR00.hlasm RACISSTC/RACIESTC/RACIACEE (lines 551-640); users.txt (FTPD and HTTPD in group STARTED), profiles.txt lines 46-49 (FACILITY SVC244 READ for ADMIN, STARTED, STCGROUP; commit 0233f83, 2026-10-18)"
  - "RAKF git history: SRCLIB/ICHSFR00.hlasm before 8904e07 (2026-02-27) and at 4093978 (2026-07-27): STC/STCGROUP hardcoded, ACEEGRP = CBLKGRP"
verified_on: 2026-10-21
applies_to: [ftpd, httpd, libc370]
tags: [rakf, rakf-2.0.0, stc, started-task, svc244, facility, users, group, upgrade, security]
related: [MVS-SEC-0010, MVS-SEC-0011, ECO-0001, ECO-0008, ECO-0020]
---

## The claims

- **On RAKF 2.0.0 the USERS entry of an STC user decides its user and group; only an STC that is not
  in USERS gets the hardcoded `STC` / `STCGROUP` pair.** `[source: RACISSTC looks up the START= procedure
  name in the USERS core table; RACIESTC is the default, with message RAKF0010I]` `[tested]` The older
  behaviour (always `STC`/`STCGROUP`, ECO-0008) is what the source before the 2.0 line shows
  (`RACISSTC: LA R4,STCUID-L'CBLKNEXT` straight to RACIACEE; no USERS lookup for the STC name;
  `[source: RAKF commit 4093978, SRCLIB/ICHSFR00.hlasm]`).
- **The ACEE default group is the group of the USERS entry, not the group requested by the RACINIT caller.**
  `[source: RACIACEE: MVC ACEEGRP,CBLKGRP]` `[tested]` (MVS-SEC-0008: a requested group that is not connected is
  ignored). The source reading of the pre-2.0 `ICHSFR00` is the same (`MVC ACEEGRP,CBLKGRP`, commits 8904e07^ and
  4093978), see the open point in ECO-0008.
- **An upgrade whose USERS lists STC users with another group breaks `FACILITY SVC244`.** After the 2.0.0 IPL the
  started tasks HTTPD and FTPD, listed as `HTTPD   *USER` and `FTPD    *USER`, were denied: `[tested]`
  - `RAKF0005`, `RAKF000A HTTPD ,HTTPD ,FACILITY,SVC244`;
  - HTTPD ended with `HTTPD012E ... UNABLE TO DYNAMICALLY OBTAIN APF AUTHORIZATION`;
  - FTPD kept running without APF (`APF SETUP FAILED RC=4`, `RACINIT FAILED: CANNOT ENTER SUPERVISOR STATE`).
  With the older RAKF the same USERS file worked (the STC got `STCGROUP`).
- **Fix measured:** change the two USERS lines to group `STCGROUP` (`HTTPD    STCGROUP*`), `S RAKFUSER`, restart
  HTTPD and FTPD. Reverting FTPD to `*USER` reproduced the denial. `FACILITY SVC244` for an STC user in
  `STCGROUP` = 0. `[tested]` The change has to be made before the IPL on a system that is upgraded (the
  tables must be valid then, MVS-SEC-0011).
- The profile grants `SVC244` READ to ADMIN and STCGROUP only on the old tables; the 2.0.0 release adds `STARTED`
  (`FACILITYSVC244 STARTED READ`), and the release `users.txt` puts FTPD and HTTPD in group `STARTED`. `[source]`
- **The text `STC IDENTITY SET TO HTTPD/USER` printed by HTTPD/FTPD did not change after the fix**; it is not a
  measure of the effective group. `[tested]`
- **The user `SYSTEM` is not an ordinary user.** `racf_login` for SYSTEM returns no ACEE (rc 28) on both builds;
  the release `users.txt` has no SYSTEM entry. `[tested]` `[source]` (JES2 labels every started task owner
  `SYSTEM`, MVS-JES2-0002.)

## The evidence

```
before (USERS)   HTTPD     *USER      -> RAKF0005 / RAKF000A HTTPD ,HTTPD ,FACILITY,SVC244
after  (USERS)   HTTPD     STCGROUP*  -> FACILITY SVC244 = 0, HTTPD gets APF
```

A started task whose RAKF user is in group `*USER` and which runs from a non-APF library still gets its own ACEE
from `racf_get_acee()`: user JSPROBS group USER, `FACILITY SVC244` = 8, JESSPOOL results as in MVS-SEC-0004
(ECO-0020).

Container result on MVS/CE with RAKF taken from the TRKF200 package; not a stand result.
