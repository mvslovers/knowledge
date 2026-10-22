---
id: MVS-SEC-0011
title: RAKF 2.0.0 install needs a CLPA IPL, and invalid USERS/PROFILES at that IPL stop JES2
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway containers, 2026-10-21: SMP4 RECEIVE/APPLY/ACCEPT of FUNCTION TRKF200 (release install deck) after removing the old TRKF200 inventory; IPL with CLPA; cold-start runs with garbage PROFILES (valid USERS) and with garbage USERS (valid PROFILES), the 2.0.0 failure reproduced twice; console logs container-local and not kept"
  - "RAKF v2.0.0 (commit 019acf4): SRCLIB/ICHSEC00.hlasm (INIT: LOAD ICHSFR00, call CJYRCVT, then CJYRPROF, then CJYRUIDS), SRCLIB/ICHSFR00.hlasm ENTYERR1 / WTOMSG1-3, PROCLIB/RAKF.jcl, PARMLIB/RAKFINIT"
  - "mvslovers/mvs-docker#27 (PR text): build with two Hercules sessions, CLPA set in IEASYS00 and reverted afterwards"
verified_on: 2026-10-21
applies_to: [mvs-docker, libc370, ftpd, httpd, mvsmf]
tags: [rakf, rakf-2.0.0, trkf200, smp4, clpa, ipl, lpalib, cold-start, jes2, users, profiles, security]
related: [MVS-SEC-0009, MVS-SEC-0010, MVS-SEC-0012, ECO-0007]
---

## The claims

- **RAKF 2.0.0 puts a new `ICHSFR00` into `SYS1.LPALIB`; it takes effect only after an IPL with CLPA.**
  `[tested]` The container was re-IPLed in place with `CLPA,` added to `IEASYS00`. Per mvs-docker#27, the PLPA built
  by the CLPA IPL persists on the page data set, so later IPLs without CLPA still run the new `ICHSFR00`; the PR
  reverts CLPA after the install. `[attributed to the PR text; not re-measured]`
- **Files that change** `[tested]` `[source]`:
  - `ICHSFR00` in `SYS1.LPALIB` (the SAF router);
  - `CJYRCVT` / `ICHSEC00` in the link list, with the class descriptor table including `JESSPOOL`
    (MVS-SEC-0010);
  - the RAKF tables `SYS1.SECURE.CNTL(USERS)` and `(PROFILES)`, which must be valid before the IPL (below);
  - STC users such as HTTPD and FTPD in USERS need a group that has `FACILITY SVC244` (MVS-SEC-0012);
  - the SMP inventory entry for TRKF200 (the image's old TRKF200 entry must be removed first).
- **Removing the old inventory:** delete the old TRKF200 from CDS and ACDS with `UCLIN DEL SYSMOD`. After an RC 8
  UCLIN, `RESETRC.` is required, otherwise the next UCLIN is silently ignored. `[tested]` APPLY ends RC 04
  (mvs-docker#27, as for TK5).
- **Initialisation order at IPL:** ICHSEC00 loads the RCVT, then CJYRPROF (profiles), then CJYRUIDS (users).
  `[source: ICHSEC00 INIT]` A profile abend ends the step (`ABEND ...,STEP`), so the user load is not reached.
  `[inferred from the source; not isolated by a test]`
- **Cold start with an invalid user/profile table:**
  - **Image RAKF: the system starts and allows everything.** `RAKF0003 RESOURCE TABLE INVALID/MISSING: ALLOWED:<user>`
    and `RAKF0009` per call, `RAKF0001` because the user table is not loaded either; `racf_auth` returns RC 0
    everywhere. `[tested]` `[source: ICHSFR00 ENTYERR1 -> AUTHGOOD]`
  - **RAKF 2.0.0: JES2 does not start.** `IEF174I SYSTEM ERROR BEFORE JOB INITIATION`, an `IEA911E` dump of
    ASID 2, `RAKF0001`, `RAKF0002 ... USER: ~ ~`. `S RAKFUSER` (also with `SUB=MSTR`) gets no response; no recovery
    from the console was found. Reproduced twice, with garbage PROFILES (valid USERS) and with garbage USERS
    (valid PROFILES). `[tested]` The mechanism was not read in the source; the "missing user table" as the cause
    is `[inferred]` (the two cases cannot isolate "profiles only missing").
  - **The tables have to be valid before the IPL.** Nothing else was tried; the containers were discarded.
    `[tested]`
- An invalid file at a *reload* is harmless in comparison: the old chain stays (MVS-SEC-0009).

## The evidence

IPL banner after the CLPA IPL with the release deck: `RAKF V2R0M0 ... RCVT WAS PROCESSED SUCCESSFULLY`; the
installed `ICHSFR00` contains `UNDEFINED CLASS` and `RAKF0012`, `ICHSEC00` carries the CDT entry `X'08'
JESSPOOL` (MVS-SEC-0010).

The failed 2.0.0 cold start:

```
IEF174I SYSTEM ERROR BEFORE JOB INITIATION
IEA911E  ... (a dump of ASID 2)
RAKF0001 USERID TABLE INVALID OR MISSING
RAKF0002 STC ACCESS ALLOWED: USER: ~ ~
```

(The two RAKF lines are quoted from the message texts in `ICHSFR00`, WTOMSG1/WTOMSG2; the inbox note
gave the abbreviated forms.)

Container results, not stand results. MVS/CE only; TK5 was not used for the 2.0.0 install.
