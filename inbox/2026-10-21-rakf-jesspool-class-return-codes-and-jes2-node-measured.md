# RAKF class JESSPOOL on MVS 3.8j: return codes, 8-character entity cap, profile order, no OPER bypass; no JES2 node name

Source: QA session for Paperclip MVS-326 (parent MVS-240, ftpd#90), 2026-10-21.
Follow-up to `2026-10-21-rakf-oper-vs-uads-oper-aceeoper-measured.md` and to the MVS-285 note
`2026-10-21-jes-spool-authorization-tso-prefix-rule-oper-ftpd-mvsmf-none-measured.md`.
Platforms: MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01), each in an own throwaway container.
Container results, not stand results. Maintainer approved the inbox entries for this series.
KB check before writing: only INDEX looked at.

Method: a small AC(1) probe (APF library inside the container) logs a user in with
`racf_login(user, NULL, NULL, &rc)` (RACINIT without password) and calls
`racf_auth(acee, "JESSPOOL", entity, RACF_ATTR_READ | UPDATE | ALTER)`, one call per attribute.
Profiles are lines in `SYS1.SECURE.CNTL(PROFILES)`, loaded with `S RAKFPROF`.
Everything in "Measured" was identical on CE and TK5 unless stated.

## Which RAKF the containers have (measured) vs RAKF 2.0.0 (source only)

- **Measured:** the RAKF in both containers is an older level than the public 2.0.0 source.
  `ICHSFR00` from `SYS1.LPALIB` (fetched in binary) contains RAKF0005/0007/0008/000B but not
  "UNDEFINED CLASS" or RAKF0012. The loader has fixed per-class entity lengths: FACILITY 39,
  DATASET 44, DASDVOL 6, every other class name, including JESSPOOL and an invented
  `ZQUNKWN`, 8. A class name nobody defined is not an error: **profile lines with that class
  are all it takes to "create" the class.** Without any JESSPOOL line the check returns 4;
  no "Undefined class" message and no RC 8 appeared.
- **Source only (RAKF 2.0.0):** the class descriptor table (CJYRCVT) lists JESSPOOL with max
  entity length 8, the same value the old loader falls back to. An unknown class gives RC 8
  and RAKF0012 `UNDEFINED CLASS` (RACSTAT check in ICHSFR00). The operator bypass (ENTYOPER)
  applies to DATASET, DASDVOL, TAPEVOL only. Not measured with 2.0.0.

## Profile line format (measured against existing FACILITY lines)

Class in columns 1-8 (entity starts directly in column 9), entity 9-52, user or group id
53-60, access 61-68 (`NONE`, `READ`, `UPDATE`, `ALTER`). TK5 members carry sequence numbers in
73-80. A line with a blank id is the profile's UACC. `S RAKFPROF` reloads the profiles,
`S RAKFUSER` the users.

## Return codes of racf_auth (measured)

| Situation | READ | UPDATE | ALTER |
|---|---|---|---|
| no JESSPOOL profile in the class, or none matching | 4 | 4 | 4 |
| `*` UACC NONE, user without permit | 8 | 8 | 8 |
| access level N (user permit, group permit or UACC), N = NONE | 8 | 8 | 8 |
| N = READ | 0 | 8 | 8 |
| N = UPDATE | 0 | 0 | 8 |
| N = ALTER | 0 | 0 | 0 |

RC 0 allowed, 4 no matching profile (RAKF000B, which libc370 suppresses; `ftpd#aut.h` treats
4 as "not protected"), 8 denied. Attributes at or below the level pass, higher ones fail.

Precedence inside one matched profile:

- An exact user permit decides alone: user READ with group ALTER gives READ only; user NONE
  with group ALTER gives 8; user NONE with UACC ALTER gives 8.
- Otherwise the connected groups: one sufficient group is enough (ZQGRP2 NONE + ZQGRP3 UPDATE
  allows UPDATE). A matched but insufficient group blocks UACC: group NONE with UACC ALTER
  gives 8; group READ with UACC ALTER gives READ only. A user outside the group falls to UACC.
- Otherwise UACC.

## Entity matching (measured)

- **A JESSPOOL profile entity is capped at 8 characters** (longer text is truncated at load).
  The check entity is compared on its first 8 characters.
- No star: a **discrete** match of the first 8 characters, blank padded. `SHORT` does not
  match `SHORT.A`; `ZQUSR123` matches `ZQUSR123.A` but not `ZQUSR124`.
- A star within the first 9 characters: generic prefix up to the star, star excluded.
  `ZQUSR1.*` matches `ZQUSR1.` and `ZQUSR1.…`, not `ZQUSR1` and not `ZQUSR1X`; `LOCAL.*`
  matches `LOCAL.…`, not `LOCAL` and not `LOCALX.A`; `ZQUSR2*` matches `ZQUSR2X…`.
  `ZQUSR123.*` is cut to `ZQUSR123`.
- **Prefix test from the board question:** profile `LOCAL.IBMUSER` (also written `.*` or `*`)
  becomes `LOCAL.IB` and matches **both** `LOCAL.IBMUSER.JOBA.JOB00012` and
  `LOCAL.IBMUSERX.JOBA.JOB00013`, also `LOCAL.IBMUSE`, `LOCAL.IB`, `LOCAL.IBM.X`; it does not
  match `LOCAL.I` or `LOCAL.ZZ`. Consequence for a resource name such as
  `<node>.<owner>.<jobname>.<jobid>`: only the first 8 characters can discriminate. Owner
  first with `OWNER.*` works for userids up to 7 characters; a node prefix of several
  characters eats the budget and cannot separate owners.

## Order when several profiles match (measured)

- A specific profile beats `*`.
- Among several, the one that sorts **last** in ascending EBCDIC order wins, not the longest
  and not file order (the loader sorts PROFILES by the 80-byte line and the last in sort order
  is checked first).
- Therefore: `OWN*` vs `OWN1.*` -> `OWN1.*` wins; `OWN*` vs `OWN-*` -> `OWN-*` wins;
  `OWN*` vs `OWN.*` -> **`OWN*` wins**, the less specific one, because `*` sorts above `.`
  in EBCDIC. A discrete 8-character profile beats `ZQ1.*`.

## RAKF operator users bypass nothing in JESSPOOL (measured)

Users with ACEEOPER set (`aceeflg1` = `0x61`: the test user with oper flag Y, and the image's
own IBMUSER on CE / HERC01 on TK5) get RC 8 for READ, UPDATE and ALTER in JESSPOOL under
`*` NONE and under a specific NONE profile. Control with the same users on DATASET
`ZQPRIV.*` NONE: 0/0/0. So the operator flag works for DATASET (source: also DASDVOL,
TAPEVOL) and not for JESSPOOL.

## Console messages (measured)

No RAKF0005, RAKF000A or RAKF000B for a `racf_auth` denial or for RC 4: not in the job log,
not in the CE Hercules log. The control with DATASET and RC 8 through `racf_auth` is also
silent, so this is a property of the call (libc370 runs it with logging suppressed), not of
the class. A real OPEN of a protected data set does log RAKF0005/RAKF000A (earlier note).
For JESSPOOL the messages on denial follow from the ICHSFR00 source only.

## JES2 node name (measured)

- No JES2 node name is available on either system. `$D NJEDEF`, `$D NODE(1)`, `$D N`, `$D N1`,
  `$D NODE` return a job display (JES2 3.8j parses `$D` as a job display, "PRT LOCAL PUN
  LOCAL PRIO 1 ANY" for the oldest job). `$D MASDEF`, `$D SID`, `$D SPOOL`: INVALID OPERAND;
  `$D CKPT`, `$D LINE(1)`: INVALID COMMAND; `$D JES2`: JOB(S) NOT FOUND.
- Init decks (CE `SYS1.PARMLIB(JES2PM00)`; TK5 `SYS1.JES2PARM(JES2PARM)` and `STARTSTD`)
  contain no OWNNODE, NUMNODE or NODE statement. TK5 has only a comment line `&NUMNODE
  &OWNNODE &TGSIZE` (changes there need a cold start). No NJE38 data sets in either image.
- What exists instead: the route name `LOCAL` and the SMF system id in `$HASP373`
  (`SYS MVSC` on CE, `SYS TK5R` on TK5). TK5 also has DESTIDs RMT01..04.
- TSO `STATUS <jobname>` prints only `IKJ56192I JOB <name>(JOB000nn) ON OUTPUT QUEUE`, no node.
  mvsMF job JSON has no node field. `STATUS` without operand abends S0C1 in batch TSO on both.
- RFE could not be measured: it is full-screen ("REVIEW TERMINATED BECAUSE TERMINAL IS NOT A
  3270 DISPLAY" in batch) and no 3270 client was available.

## Not measured

- RAKF 2.0.0 itself (no container has it); everything for it is from the source.
- Cost of one check; an ACEE built before a profile reload; attribute CONTROL; a real FTP
  login; RFE.
- Stands were not touched.
