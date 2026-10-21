# JES spool access on MVS 3.8j: TSO checks the job-name prefix and UADS OPER; FTPD 1.3.0 and mvsMF 1.3.0 check nothing

Source: QA session for Paperclip MVS-285 (parent MVS-240, ftpd#90), 2026-10-21.
Platforms: MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01), each in an own throwaway
container on mvsdev (`mvsce-target`), two users per system. Container results, not
stand results. Maintainer approved this inbox entry on MVS-285 (2026-10-21).
KB check before writing: not looked up in the KB beyond the INDEX; no document found
that names the REJECTED message.

## Finding

- **TSO `STATUS`, `OUTPUT`, `CANCEL`, `CANCEL ... PURGE`** reject a non-operator with
  `JOB <name> REJECTED - JOBNAME MUST BE YOUR USERID OR MUST START WITH YOUR USERID`.
  The test is on the **job name** (equal to the userid or starting with it), not on the
  job owner. A job `MVSCE02X` submitted by IBMUSER is treated as MVSCE02's; a job
  `ZNRFIN` submitted by MVSCE02 is rejected for MVSCE02. Same on CE and TK5.
- **The operator is recognised by the UADS attribute OPER** (`SYS1.UADS`, shown by
  `LIST (*)` in an IKJEFT01 batch step), not by the RAKF group. CE: IBMUSER is in RAKF
  group ADMIN, MVSCE02 in USER; `CHANGE (MVSCE02) OPER` made MVSCE02 pass
  OUTPUT/CANCEL/PURGE on foreign jobs, `NOOPER` restored the rejection. TK5: HERC01,
  HERC02, IBMUSER have OPER; HERC03, HERC04 do not.
- **Reading is not restricted:** `STATUS <jobname>` shows any job; the RFE OUTLIST
  browse (`S`) opens any spool entry including the FTPD STC; the TK5 `QUEUE` command
  lists every job for every user. `STATUS` without arguments lists only jobs with the
  user's name prefix, also for the operator.
- **Which tool produces the message:** the TSO `CANCEL` command. RFE OUTLIST selection
  codes `C` and `P` call it. TK5 `QUEUE` (DA, DT, DS, DC, STATUS LEVEL, DQ, DI, AI, HI,
  DF, DO, AO, HO, END) is display-only and has no cancel or purge.
- **Not an authorization question:** cancelling an active STC fails even for the
  operator: `INVALID CANCEL REQUEST - FTPD(STC00033) IS AN ACTIVE TSO USER OR STARTED
  TASK+`. `CANCEL` of a finished job: `NOT CANCELLED BECAUSE ON OUTPUT QUEUE+`; of a
  held job: silent, the job moves to the output queue. `OUTPUT` sees only held output
  classes (CE `Y`, TK5 `H`); a second call gives `NO HELD OUTPUT FOR JOB ...`.
- **FTPD 1.3.0-dev (main), JES mode:** the owner is only a display filter
  (`jes_owner`; default the login userid, `SITE JESOWNER=*` lists everything). `RETR`
  of any spool document and `DELE` (jescanj purge, `250 Cancel successful`) work on any
  job for any logged-in user, operator or not. Active STC: `550 Access denied - cannot
  cancel STC00033`. Login itself is gated by the RAKF FACILITY class FTPAUTH (CE and
  TK5 default: ADMIN READ only; a normal user gets `530 Not authorized for FTP
  access.`).
- **mvsMF 1.3.0:** Basic Auth only. `GET /zosmf/restjobs/jobs?owner=*`, `files`,
  `records` and `DELETE` (purge) work for any user on any job (200). The default list is
  owner-filtered. `PUT {"request":"cancel"}` answers 404
  `{"rc":4,"category":6,"reason":7,"message":"Not Found"}`; hold, cancel and
  release are not implemented. `DELETE` of an active STC: 400 `Cannot purge a started
  task`.

## Measurement

CE container (mvsMF port 33975 at the time), TK5 container (33969). Per user and system
twelve jobs (IEBGENER, TYPRUN=HOLD for the waiting ones; names with and without the
userid prefix; owner and name prefix crossed). Examples: CE `ZOPFIN` JOB00020 (operator,
read by MVSCE02 via STATUS: `ON OUTPUT QUEUE`), `ZNRFIN` JOB00159 (`NOT CANCELLED
BECAUSE ON OUTPUT QUEUE+`), FTPD STC00033; TK5 FTPD STC00043, `ZOPFIN` JOB00141 purged
by HERC03 through mvsMF (200), JOB00165 purged by HERC03 through FTPD DELE (250).
Results in the Paperclip comment on MVS-285 (tables per access, user and job).

## Limits

- Container, not stand; CE has the products copied in, TK5 has them SMP-installed.
- FTPAUTH for group USER added in the container's `SYS1.SECURE.CNTL(PROFILES)` to let
  the normal user log in to FTPD.
- No truly running batch job; waiting was modelled with TYPRUN=HOLD.
- OPER/NOOPER flip measured on CE for TSO only. Other operator notions (RACF
  OPERATIONS, console authority) were not measured. mvsMF hold/release not tested.
- First read of the FTPD STC log failed once (`550 Spool data set for STC... no longer
  available.`), later reads worked, also for non-operators.
