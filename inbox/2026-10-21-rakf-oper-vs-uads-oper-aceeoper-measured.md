# Two operator flags on MVS 3.8j: UADS OPER (TSO commands) and RAKF column 28 (ACEEOPER, data sets) are independent

Source: QA session for Paperclip MVS-326 (parent MVS-240, ftpd#90), 2026-10-21.
Follow-up to the MVS-285 note `2026-10-21-jes-spool-authorization-tso-prefix-rule-oper-ftpd-mvsmf-none-measured.md`.
Platforms: MVS/CE (RAKF 2.0.0, SHADOW passwords) and TK5 (VER 3.8J REL P6.2007.JAN.01,
RAKF 1.2.x, clear passwords in USERS), each in an own throwaway container, one test user
per system. Container results, not stand results. Maintainer approved the inbox entries
for this series on MVS-285/MVS-326.
KB check before writing: only INDEX looked at; no document found on the two flags.

## Finding

- **There are two separate operator flags, maintained in two separate places.**
  - UADS attribute OPER: set with `ACCOUNT` / `CHANGE (user) OPER|NOOPER`, stored in
    `SYS1.UADS`, copied into the PSCB at TSO LOGON. TSO `CANCEL`, `OUTPUT`, `STATUS`
    use it.
  - RAKF `SYS1.SECURE.CNTL(USERS)`, column 28 (`Y`/`N`): loaded by `S RAKF`, put into
    `ACEEOPER` (bit `0x20` of `aceeflg1`) at RACINIT. `ACEEOPER` makes RAKF grant
    DATASET/DASDVOL access without a permit ("ACCESS ALLOWED VIA OPERATIONS").
  - Nothing synchronises them: changing one does not touch the other.
- **The shipped images keep them in agreement by hand.**
  - CE: IBMUSER, MVSCE01 are UADS OPER and RAKF Y; MVSCE02 is NOOPER and N.
  - TK5: HERC01, HERC02, IBMUSER are OPER and Y; HERC03, HERC04 are NOOPER and N.
  - RAKF has entries with no UADS entry (CE: MVP (oper Y), FTPD, HTTPD; TK5: FTPD,
    HTTPD). Their TSO attribute does not exist, their ACEEOPER is what RAKF says.
- **ACEEOPER follows column 28 exactly.** RACINIT without a password (as `racf_login`
  in libc370 and `ftpd#aut.c` do), `aceeflg1` = `0x61` for Y (OPER bit set) and `0x41`
  for N, on both images. `ACEESPEC` stays 0 for every user. UADS has no influence.
- **Cross cases, one user, identical on CE and TK5** (job `ZQFS<n>` owned by someone
  else; data set `ZQPRIV.DATA` under profile `DATASET ZQPRIV.* NONE`):

  | UADS | RAKF | ACEEOPER | TSO `CANCEL <foreign job> PURGE` | read `ZQPRIV.DATA` |
  |---|---|---|---|---|
  | NOOPER | N | 0 | rejected | S913 |
  | OPER | N | 0 | allowed, job purged, no message | S913 |
  | NOOPER | Y | 1 | rejected | RC 0000, data read |
  | OPER | Y | 1 | allowed | RC 0000 |

  Rejection text: `JOB ZQFS2 REJECTED - JOBNAME MUST BE YOUR USERID OR MUST START WITH YOUR USERID`.
  Denied read: `RAKF0005 INVALID ATTEMPT TO ACCESS RESOURCE`,
  `RAKF000A  MVSCE02 ,ZQREAD  ,DATASET ,ZQPRIV.DATA`,
  `IEC150I 913-38,IFG0194C,ZQREAD,G,SYSUT1,...,ZQPRIV.DATA`.
  So: UADS OPER governs the job-name rule of the TSO commands only; RAKF Y governs
  data set access only. Neither implies the other.
- **RAKF changes take effect only after `S RAKF`.** `S RAKF` (CE: messages
  `RAKFPROF7  RAKF PROFILES UPDATED`, `RAKFUIDS4  USER TABLE UPDATED`) reloads PROFILES
  and USERS. Editing the USERS member alone changes nothing: with `Y` in the member and
  no reload a new RACINIT still gave `flg1=41`; after `S RAKF` it gave `flg1=61`. Not
  measured: an ACEE that was built before the reload (a long-running FTP session).
- **UADS can be read by a program; the OPER bit is in the first record of the member.**
  - `SYS1.UADS` is a PDS (DSORG=PO, RECFM=FB, LRECL=80, BLKSIZE=800). A user's member
    is named **userid followed by `0`** (`IBMUSER0`, `MVSCE020`, `HERC030`; a 7-character
    userid gives 8 characters).
  - Record 1 of the member: bytes 0-3 `03 20 00 40`, bytes 4-11 the userid padded with
    blanks (EBCDIC), byte offset 16 (0-based) the attribute byte. Bits found by
    changing one attribute at a time and dumping the member with IEBPTPCH
    `PRINT TYPORG=PO,MAXNAME=1,TOTCONV=XE`: `0x80` OPER, `0x40` ACCT, `0x20` JCL,
    `0x10` MOUNT. Examples: MVSCE02 NOOPER/NOACCT/JCL = `20`; + OPER = `A0`;
    + ACCT = `60`; + MOUNT = `30`; IBMUSER (OPER ACCT JCL MOUNT) = `F0`. Identical on
    CE and TK5.
  - Authorization: with no profile for `SYS1.UADS`, the universal `DATASET *` READ
    applies. RACHECK for FTPD (RACINIT without password): READ rc=0, UPDATE rc=8
    (group USER on CE, group FTPD on TK5). An operator ACEE gets UPDATE too.
    Not tried: an actual OPEN of the PDS under the FTPD STC identity.
  - The UADS password field is not needed to read the OPER bit and was not examined.
- **Probe:** a small AC(1) program that calls `racf_login(user, NULL, NULL, &rc)`,
  prints `aceeflg1/2` and `racf_auth(a, "DATASET", dsn, READ|UPDATE)`. It must run
  from an APF library. `ACCOUNT CHANGE` in an IKJEFT01 step fails with
  `IKJ56576I ... USERID IN USE` while the user is logged on to TSO.

## Not measured

- `RAKF0007 ACCESS ALLOWED VIA OPERATIONS` was not seen, neither in the job log nor in
  the CE Hercules log (the TK5 log was not readable).
- A real FTP login (password check) was not part of the run; ACEE was built by the
  probe through the same libc370 call.
- Stands were not touched.
