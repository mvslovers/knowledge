# RAKF 2.0.0 vs older MVS/CE RAKF: edge cases of racf_auth/JESSPOOL, table errors, cold start (measured)

Measured 2026-10-21 on two throwaway MVS/CE containers (not a stand), Paperclip issue MVS-332 (second measuring
order, follows `2026-10-21-rakf-200-jesspool-racf-auth-measured-vs-old-rakf.md`). Same probe JSPROBE (AC(1),
libc370 2.25.1 `<mvs/racf.h>`, racf_login without password, racf_auth READ/UPDATE/ALTER). "Container RAKF" = the
RAKF built into the MVS/CE image (banner V2R0M0, but an older build than the release); "2.0.0" = RAKF TRKF200
installed from the release deck with CLPA IPL. Label: **gemessen** = result of a job on the container,
**nur Quelltext** = read from source, not measured.

## Results (container RAKF | RAKF 2.0.0)

| Point | Container RAKF | RAKF 2.0.0 |
|---|---|---|
| A1 empty class, READ/UPDATE/ALTER | RC 4/4/4 (gemessen) | RC 4/4/4 (gemessen); libc370 2.25.1 on both. LOG=NONE / flag byte 0x10 (libc370 #63: before the fix RC 4 was reported as 0) is nur Quelltext, no older libc370 measured |
| A6 ACEEOPER user under `*` NONE | RC 8 (gemessen) | RC 8 (gemessen) |
| A3 comparison width W | 8 (gemessen) | 8 (gemessen); `ABC.PROD*` UPDATE: RC 0 for `ABC.PRODX.JOB00001`, RC 8 for `ABC.TESTX.JOB00002` and `ABC.PRO` |
| A15 profile without star | **discrete** (gemessen) | **prefix** (gemessen) — deviates. `ABC` UPDATE / `ABCD` READ: `ABC.JOBA.JOB00012` RC 8 on the container RAKF, R0/U0/A8 on 2.0.0. Source says prefix up to the first blank/star (nur Quelltext), so the container RAKF is the outlier |
| A7 class not in CDT | RC 4, no message (gemessen, with `NOSUCHCL`) | RC 8 + `RAKF0012 UNDEFINED CLASS NOSUCHCL`, three messages per READ/UPDATE/ALTER probe, not suppressed by racf_auth (gemessen). JESSPOOL itself was not removed from the CDT; for JESSPOOL absent from the CDT RC 8 + RAKF0012 is nur Quelltext. Empty class on 2.0.0 = RC 4 (gemessen) |
| A13 profile with group line but no universal line | U0400 at load, old chain stays (gemessen) | same |
| A12 8-character userid | `ABCDEFGH.*` and `ABCDEFGH` decide alike (gemessen) | identical |
| A10 entities `X..`, `..` | `X..`/`X.` match `X.*`, `..` only `*` (RC 8) (gemessen) | identical |
| Entity characters outside [A-Z0-9$#@] (blank, `X*…`, `*…`, lowercase, `-`, `*`, `.`, `A.B.C`) | all fall to `*` NONE, RC 8, no special RC (gemessen) | identical |
| A11 running AC(1) process and `S RAKFPROF` | effective at next racf_auth, no new RACINIT (gemessen) | identical |
| E6 user SYSTEM in USERS | no (acee NULL, rc 28) (gemessen) | no (gemessen); release users.txt has no SYSTEM (nur Quelltext) |
| A14 reload: duplicate/same key | U0300 `RAKFPROF3 I/P RECORDS OUT OF ORDER`, old chain stays (gemessen) | same |
| A14 reload: broken file | U0500 `RAKFPROF6 ENTITY RECORD WITH NO ACCESS AUTHORITY`, old chain stays (gemessen) | same |
| A14 cold start, user/profile table invalid | survives: `RAKF0003 RESOURCE TABLE INVALID/MISSING: ALLOWED:<user>` + `RAKF0009` per call, `RAKF0001` because the user table is not loaded either; racf_auth RC 0 everywhere (everything allowed) (gemessen; source agrees) | **JES2 does not start** (`IEF174I SYSTEM ERROR BEFORE JOB INITIATION`, `IEA911E` dump of ASID 2, `RAKF0001`, `RAKF0002 … USER: ~ ~`); `S RAKFUSER` (also `SUB=MSTR`) gets no response; no recovery from the console (gemessen, reproduced twice) |

## Side facts

- The loader CJYRPROF sorts its input itself; unsorted input is accepted. U0300 fires only for records with the
  same class/entity/id (duplicates). U0400 = permit record without universal record; U0500 = entity record
  without access authority. All three abort the load (ABEND 300/400/500) and leave the old chain in place on a
  reload (gemessen).
- At IPL ICHSEC00 loads RCVT, then CJYRPROF (profiles), then CJYRUIDS (users). A profile abend aborts the user
  load too. The cold start failure was reproduced with garbage PROFILES (valid USERS) and with garbage USERS
  (valid profiles); the cause is the missing user table, so "profiles only missing" cannot be isolated.
- No recovery from the console was found on a bricked 2.0.0 system; the tables have to be valid before the IPL
  (nothing else was tried, the containers were discarded).
- Match rule unchanged: last matching profile in EBCDIC sort order wins; JESSPOOL entity cap 8 (CDT length
  byte 8). On the container RAKF an unlisted class behaves with cap 8 as well and issues no CDT message.

## What a permanent MVS/CE image with RAKF 2.0.0 needs (the switch itself is a board decision)

New ICHSFR00 in SYS1.LPALIB; new CJYRCVT/ICHSEC00 in LINKLIB with the CDT including `AL1(8) JESSPOOL`; IPL with
CLPA; RAKF tables USERS/PROFILES (valid, they are fatal at IPL on 2.0.0); STC users HTTPD/FTPD in USERS with
group STCGROUP or STARTED (plus the SVC244 profile), see the side finding of the first note; SMP inventory of
TRKF200 instead of the old entries.

## Source of the numbers

Job outputs and console logs are in the Paperclip scratch directory of MVS-332 (not kept). Container results
on MVS/CE; they are not stand results.

## Addendum 2026-10-22: what the RAKF maintainer says

Rob Prins (RAKF maintainer), 2026-10-22, in reply to these measurements (his statements, not measured by us):
- A prefix match (profile without a star) is meant **only for class DATASET**. The prefix behaviour of a star-less profile in JESSPOOL on 2.0.0 is therefore probably a RAKF defect, not intended behaviour. Write `OWNER.*` in other classes and do not rely on star-less profiles there.
- `MIKE1.*` is a valid generic profile in JESSPOOL; the JESSPOOL entity length is limited to 8 (IBM allows 246, too long for RAKF).
- OPERATIONS gives access only in DATASET, TAPEVOL and DASDVOL, as in IBM's RACF.
- Create profiles with the RAKF commands (`RDEFINE`/`RDEF`, `PERMIT`/`PE`, then `S RAKFPROF`) rather than editing PROFILES by hand. `PERMIT` refuses without a universal-access record (HELP member PERMIT).
