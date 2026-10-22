# RAKF 2.0.0 (TK5 Update 6): racf_auth on JESSPOOL measured, side by side with the older MVS/CE RAKF

Measured 2026-10-21 on a throwaway MVS/CE container (not a stand), Paperclip issue MVS-332, follow-up
to the MVS-326 part 5 note (`2026-10-21-rakf-jesspool-class-return-codes-and-jes2-node-measured.md`).
Probe: JSPROBE (AC(1), libc370 `<mvs/racf.h>`: racf_login without password, then
`racf_auth(acee,"JESSPOOL",entity,attr)` for READ/UPDATE/ALTER), 150 checks per profile phase,
four phases (A: no JESSPOOL profiles, B: only `*` UACC NONE, C: 64 test profiles, D: C + `*` UACC NONE).
Each check is the RC triple (READ, UPDATE, ALTER). 600 checks run on the old RAKF, the same 600 on 2.0.0.

## How RAKF 2.0.0 was obtained

SMP4 RECEIVE/APPLY/ACCEPT of FUNCTION TRKF200 (release install deck) in the container, after removing the
old TRKF200 inventory (CDS/ACDS UCLIN delete; `RESETRC.` is required after an RC 8 UCLIN, otherwise the next
UCLIN is silently ignored). RAKF 2.0.0 needs an IPL with CLPA (new ICHSFR00 in LPALIB); `CLPA,` was put in
IEASYS00 and the container was re-IPLed in place (Hercules `sysclear` + `ipl 150`; never `quit`, the DASD
lives in the container). Verified by content, not by RC: the installed ICHSFR00 contains the text
`UNDEFINED CLASS` / `RAKF0012`; the installed ICHSEC00 (CJYRCVT) carries the CDT entry `X'08' JESSPOOL`
(length byte 8; FACILITY X'27', DATASET X'2C', APPL X'08'). IPL banner: `RAKF V2R0M0 ... RCVT WAS PROCESSED
SUCCESSFULLY`.

## Result: identical except for one row

Of 600 checks, 4 differ (one check, four phases): the **undefined class**.

| Check | old RAKF | RAKF 2.0.0 |
|---|---|---|
| `racf_auth` class not in the CDT (`NOSUCHCL`) | RC 4 (R/U/A) | **RC 8** (R/U/A), console `RAKF0012 UNDEFINED CLASS NOSUCHCL` once per call (three per READ/UPDATE/ALTER probe) |
| JESSPOOL without matching profile (phase A, C) | RC 4 | RC 4 |
| `*` UACC NONE (phase B, D) | RC 8 | RC 8 |
| levels NONE/READ/UPDATE/ALTER via user, group, UACC; multi-group users | as MVS-326 | identical |
| entity cap 8 characters, both on the profile and on the checked entity | yes | yes (CDT length byte is 8) |
| ordering: last matching profile in EBCDIC sort order wins (`OWN*` after `OWN.*` after ... `OWN1.*`) | yes | yes |
| ACEEOPER (oper user JSUO, class JESSPOOL) | no bypass | no bypass |
| console message on a racf_auth denial (JESSPOOL, FACILITY, DATASET) | none | none (RAKF0005/000A did appear in the same log, but only for other callers: the STC SVC244 check and a batch DATASET check) |
| profile change after `S RAKFPROF` in a running AC(1) process | effective at the next racf_auth, no new RACINIT | same: R=8 before, R=0 after the reload, same ACEE |

Entity length consequence (unchanged): `LOCAL.IBMUSER`, `LOCAL.IBMUSER.JOBA.JOB00012` and `LOCAL.IBMUSERX...`
all collapse to `LOCAL.IB` (all three are decided by the same profile); `ABC.*` matches `ABC.JOBA.JOB00012`
but not `ABCD.JOBA.JOB00012`; 7-char owner `ABCDEFG.*` matches `ABCDEFG.J.JOB00001` (`ABCDEFG.`), while
`ABCDEFGH.*` matches every entity that starts with the same 8 characters (`ABCDEFGH`). Owner, jobname and job id
cannot be told apart in a JESSPOOL entity. The cap is a constant of the class table (`CJYRCVT.hlasm`,
`DC AL1(8),CL8'JESSPOOL'`), not of the profile text.

## Side finding: RAKF 2.0.0 takes the STC group from USERS

After the 2.0.0 IPL the started tasks HTTPD and FTPD, listed in USERS as `HTTPD   *USER` / `FTPD    *USER`,
were denied `FACILITY SVC244` (`RAKF0005`, `RAKF000A HTTPD ,HTTPD ,FACILITY,SVC244`): HTTPD ended with
`HTTPD012E ... UNABLE TO DYNAMICALLY OBTAIN APF AUTHORIZATION`, FTPD kept running without APF
(`APF SETUP FAILED RC=4`, `RACINIT FAILED: CANNOT ENTER SUPERVISOR STATE`). With the old RAKF the same USERS
file worked. The profile grants SVC244 READ to ADMIN and STCGROUP only. Changing the two USERS lines to group
`STCGROUP` (`HTTPD    STCGROUP*`), `S RAKFUSER` and restarting HTTPD/FTPD fixed it; reverting FTPD to `*USER`
reproduced the denial. Conclusion (measured): under 2.0.0 the USERS entry of an STC user decides its group; the
release `users.txt` puts them in group `STARTED`, and the release profiles grant `STARTED` access to
`FACILITY SVC244`. An upgrade of a stand whose USERS lists STC users with another group needs that change
before the IPL. The text `STC IDENTITY SET TO HTTPD/USER` printed by HTTPD/FTPD did not change after the fix
(it is not a measure of the effective group).

## Source of the numbers

Job outputs and result files of the run are in the Paperclip scratch directory of MVS-332 (not kept). Container
result on MVS/CE with RAKF taken from the TRKF200 SMP package; it is not a stand result.
