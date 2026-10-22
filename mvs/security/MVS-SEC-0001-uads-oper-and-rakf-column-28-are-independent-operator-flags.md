---
id: MVS-SEC-0001
title: UADS OPER and RAKF column 28 are two independent operator flags
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01) throwaway containers, 2026-10-21, one test user per system; probe = AC(1) program calling libc370 racf_login(user, NULL, NULL, &rc) and racf_auth(); job numbers are container-local and not kept"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/ICHSFR00.hlasm labels RACIACEE, ENTYOPER; SRCLIB/CJYRUIDS.hlasm (flag columns)"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, httpd, mvsmf]
tags: [rakf, uads, oper, operations, aceeoper, aceeflg1, tso, account, security]
related: [MVS-SEC-0002, MVS-SEC-0003, MVS-SEC-0007, ECO-0008, ECO-0020]
---

## The claims

- **There are two operator flags, kept in two places, and nothing synchronises them.**
  - UADS attribute `OPER`: set with `ACCOUNT` / `CHANGE (user) OPER|NOOPER`, stored in
    `SYS1.UADS`, copied into the PSCB at TSO LOGON. TSO `CANCEL`, `OUTPUT` and `STATUS`
    use it (see MVS-SEC-0003). `[tested]`
  - RAKF `SYS1.SECURE.CNTL(USERS)` column 28 (`Y`/`N`): loaded by `S RAKF` (or `S RAKFUSER`),
    put into `ACEEOPER` (bit `X'20'` of `ACEEFLG1`) at RACINIT. `[tested]`
    `[source: RAKF v2.0.0 ICHSFR00 RACIACEE: CBLKFLG1='Y' -> OI ACEEFLG1,ACEEOPER]`
- **ACEEOPER follows column 28 exactly; UADS has no influence on it.** RACINIT without a password
  (what `racf_login` in libc370 and `ftpd#aut.c` do) gives `aceeflg1` = `0x61` for `Y` and `0x41`
  for `N`, on both images. `ACEESPEC` stays 0 for every user. `[tested]`
  `[source: ICHSFR00 RACIACEE builds ACEEFLG1 = ACEERACF+ACEECNTL (0x41) and adds ACEEOPER (0x20)]`
- **ACEEOPER makes RAKF grant access without a permit only in the classes DATASET, DASDVOL and
  TAPEVOL** (details: MVS-SEC-0007). UADS OPER governs only the job-name rule of the TSO commands.
  Neither implies the other. `[tested]`
- **The shipped images keep the two in agreement by hand.** `[tested]`
  - MVS/CE image: IBMUSER, MVSCE01 are UADS OPER and RAKF `Y`; MVSCE02 is NOOPER and `N`.
  - TK5 image: HERC01, HERC02, IBMUSER are OPER and `Y`; HERC03, HERC04 are NOOPER and `N`.
  - RAKF has users with no UADS entry (MVS/CE: MVP with oper `Y`, FTPD, HTTPD; TK5: FTPD, HTTPD).
    They have no TSO attribute; their ACEEOPER is what RAKF says.
- **A change in `SYS1.SECURE.CNTL(USERS)` takes effect only after the reload.** Editing the member
  alone changed nothing: with `Y` in the member and no reload a new RACINIT still gave `flg1=41`;
  after `S RAKF` it gave `flg1=61`. `S RAKF` printed `RAKFPROF7  RAKF PROFILES UPDATED` and
  `RAKFUIDS4  USER TABLE UPDATED`. `[tested]`
- **Not measured:** an ACEE built before the reload (a long-running FTP session); `RAKF0007
  ACCESS ALLOWED VIA OPERATIONS` was never seen in the job log or the MVS/CE Hercules log. `[source]`
  The reason is in the source: RAKF 2.0.0 issues RAKF0007 only when the userid is `PROD`
  (`CLC =C'PROD',ACEEUSRI` / `BNE AUTHGOOD` at ENTYOPR2); for every other user the bypass is silent.

## The evidence

Cross cases, one user, identical on MVS/CE and TK5 (job `ZQFS<n>` owned by someone else; data set
`ZQPRIV.DATA` under the profile `DATASET ZQPRIV.* NONE`):

| UADS | RAKF | ACEEOPER | TSO `CANCEL <foreign job> PURGE` | read `ZQPRIV.DATA` |
|---|---|---|---|---|
| NOOPER | N | 0 | rejected | S913 |
| OPER | N | 0 | allowed, job purged, no message | S913 |
| NOOPER | Y | 1 | rejected | RC 0000, data read |
| OPER | Y | 1 | allowed | RC 0000 |

Rejection text: `JOB ZQFS2 REJECTED - JOBNAME MUST BE YOUR USERID OR MUST START WITH YOUR USERID`.
Denied read (the same job log in each case):

```
RAKF0005 INVALID ATTEMPT TO ACCESS RESOURCE
RAKF000A  MVSCE02 ,ZQREAD  ,DATASET ,ZQPRIV.DATA
IEC150I 913-38,IFG0194C,ZQREAD,G,SYSUT1,...,ZQPRIV.DATA
```

Probe note: the program must run from an APF library (`racf_login` abends S047 otherwise, see
ECO-0020). `ACCOUNT CHANGE` in an IKJEFT01 step fails with `IKJ56576I ... USERID IN USE` while the
user is logged on to TSO.

## Builds

The reload messages and the `0x61`/`0x41` values were measured on the RAKF built into the MVS/CE
image and on the TK5 image (RAKF 1.2.x, clear passwords in USERS); the source reading is RAKF v2.0.0.
The inbox note labelled the MVS/CE image "RAKF 2.0.0"; the image carries an older build under the
same banner (MVS-SEC-0010), so the measurement is for that build. The v2.0.0 source builds the flags
the same way.
