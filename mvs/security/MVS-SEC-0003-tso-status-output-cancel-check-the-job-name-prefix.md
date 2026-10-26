---
id: MVS-SEC-0003
title: TSO STATUS, OUTPUT and CANCEL check the job-name prefix and UADS OPER, not the job owner
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01) throwaway containers, 2026-10-21, two users per system, twelve jobs per user (IEBGENER; TYPRUN=HOLD for the waiting ones); job numbers are container-local and not kept"
  - "IBM TSO command processors were not reachable at ingest; the rule below is the observed behaviour"
verified_on: 2026-10-21
applies_to: [ftpd, mvsmf]
tags: [tso, status, output, cancel, purge, oper, uads, spool, jes2, security]
related: [MVS-SEC-0001, MVS-SEC-0002, ECO-0021, ECO-0022]
---

## The claims

- **TSO `STATUS`, `OUTPUT`, `CANCEL` and `CANCEL ... PURGE` reject a non-operator** with
  `JOB <name> REJECTED - JOBNAME MUST BE YOUR USERID OR MUST START WITH YOUR USERID`. `[tested]`
- **The test is on the job name** (equal to the userid or starting with it), **not on the job
  owner.** A job `MVSCE02X` submitted by IBMUSER counts as MVSCE02's; a job `ZNRFIN` submitted by
  MVSCE02 is rejected for MVSCE02. Same on MVS/CE and TK5. `[tested]`
- **The operator is recognised by the UADS attribute OPER**, not by the RAKF group. MVS/CE:
  IBMUSER is in RAKF group ADMIN and MVSCE02 in USER; `CHANGE (MVSCE02) OPER` let MVSCE02 pass
  OUTPUT/CANCEL/PURGE on foreign jobs, `NOOPER` restored the rejection. TK5: HERC01, HERC02,
  IBMUSER have OPER; HERC03, HERC04 do not. `[tested]` The OPER/NOOPER flip was measured on
  MVS/CE for TSO only. Other operator notions (RACF OPERATIONS, console authority) were not
  measured for these commands.
- **Reading is not restricted.** `STATUS <jobname>` shows any job; the RFE OUTLIST browse (`S`)
  opens any spool entry including the FTPD started task; the TK5 `QUEUE` command lists every job for
  every user. `STATUS` without an operand lists only jobs with the user's name prefix, also for the
  operator. `[tested]`
- **Which tool produces the message:** the TSO `CANCEL` command. RFE OUTLIST selection codes `C`
  and `P` call it. TK5 `QUEUE` (DA, DT, DS, DC, STATUS LEVEL, DQ, DI, AI, HI, DF, DO, AO, HO, END) is
  display-only and has no cancel or purge. `[tested]`
- **Refusals that are not authorization:** `[tested]`
  - Cancelling an active started task fails even for the operator:
    `INVALID CANCEL REQUEST - FTPD(STC00033) IS AN ACTIVE TSO USER OR STARTED TASK+`.
  - `CANCEL` of a finished job: `NOT CANCELLED BECAUSE ON OUTPUT QUEUE+`; of a held job: silent,
    the job moves to the output queue.
  - `OUTPUT` sees only held output classes (MVS/CE `Y`, TK5 `H`); a second call gives
    `NO HELD OUTPUT FOR JOB ...`.
- `STATUS` without an operand abends S0C1 in batch TSO on both systems. `[tested]`

## The evidence

Per user and system twelve jobs, names with and without the userid prefix, owner and name prefix
crossed. Examples (job numbers container-local): MVS/CE `ZOPFIN` JOB00020 (operator's job, read by
MVSCE02 via `STATUS`: `ON OUTPUT QUEUE`), `ZNRFIN` JOB00159 (`NOT CANCELLED BECAUSE ON OUTPUT
QUEUE+`), FTPD STC00033; TK5 FTPD STC00043.

## Limits

Container, not a stand. No truly running batch job existed; waiting was modelled with TYPRUN=HOLD.
The first read of the FTPD started-task log failed once (`550 Spool data set for STC... no longer
available.`), later reads worked, also for non-operators.

What FTPD and mvsMF do with the same spool: ECO-0021, ECO-0022.
