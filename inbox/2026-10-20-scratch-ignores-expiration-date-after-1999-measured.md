# SCRATCH (SVC 29) on MVS 3.8j deletes unexpired data sets: two-digit DSCB year vs. CVTDATE year since 1900

Source: libc370 session, 2026-10-19. Found while building `__scratch()` /
`__renamev()` for mvslovers/libc370#143, PR mvslovers/libc370#681 (merged;
"Not asserted on MVS" paragraph of the PR body). Platform: MVS 3.8j, MVS/CE
in an own throwaway container (`mvsce-target`). KB check before writing: no
document covers DS1EXPDT, the SCRATCH purge-date test or CVTDATE.

## Finding

SCRATCH without the purge-date override (CAMLST `OVRD`) deletes a data set
whose expiration date has not been reached. Every expiration date looks
past whenever the system date is in 2000 or later.

## Mechanism (source)

IBM DADSM module `IGG0290A` (mvs38-ibmsrc `ibm/IGG/IGG0290A.asm`, lines
459-502, sequence numbers 03140000-03420000): unless `2(PL),X'10'` (override) is set, it converts
CVTDATE (packed `0cyyddd`) to a binary year byte and day, then

```
         CLC   DS1EXPDT(3),FIELD1+5     COMPARE PURGE DATE AND DATE
         BH    NOPURGE
...
NOPURGE  EQU   *                        PURGE DATE ERROR         Y02078
         LA    R3,PURGERR               SET PURGE DATE ERROR     Y02078
```

The code comments the halfword as `0YYZ`, i.e. it assumes the century
digit is 0. From 2000 on CVTDATE carries c=1, the halfword is `1YYZ`, and
the year byte becomes 100+yy: 126 (X'7E') in 2026. The format-1 DSCB keeps the year without the century: 26
(X'1A'). X'1A....' is never higher than X'7E....', so NOPURGE (volume
status 3) is never taken.

## Measurement

- Probe MEAS2 (an OBTAIN of the format-1 DSCB plus CVTDATE, written ad hoc
  for this; `IBMUSER.TSTVOLAD.EXP`, uncataloged on WORK01, created with
  `LABEL=RETPD=30` on 2026-10-19), JOB00026 (container-local):

  ```
  MEAS2 rc=0 credt=1A0124 expdt=1A0142 cvtdate=0126292F
  ```
  credt = year X'1A' (26), day X'0124' (292); expdt = day X'0142' (322),
  30 days later; CVTDATE = 0126292F (c=1, yy=26, ddd=292).
- Probe `test/mvs/tstvolad.c` (libc370), JCL `jcl/setvolad.jcl` creates the
  data sets, `jcl/tstvolad.jcl` runs it. JOB00023 (container-local):
  ```
  +TSTVOLAD   __scratch(EXP, WORK01, 0) = 0 errno 0
  +TSTVOLAD   __scratch(EXP, WORK01, OVRD) = 8
  ```
  SCRATCH without override returned 0 and deleted the 30-day-retention
  data set; the following OVRD call found nothing left (8). The final
  version of the probe repeats it on `IBMUSER.TSTVOLAD.EXP2` and records
  the result (0) instead of asserting it.

Not measured: a system date before 2000, where the two years would agree;
the 2-digit claim for DSCB years is from the measured X'1A', not from
another release.

## What it means for callers

- On MVS 3.8j with a current date, expiration dates / retention periods do
  not protect a DASD data set from SCRATCH; `OVRD` makes no difference.
  Utilities that scratch through the same DADSM module (IEHPROGM, IDCAMS
  DELETE of a non-VSAM data set) are presumably affected too `[inferred,
  not tested]`.
- libc370 `__scratch()` maps volume status 3 to `EPERM`, but on 3.8j that
  code cannot occur for SCRATCH today; the Library Reference says so.
- Do not rely on `RETPD`/`EXPDT` as a safety net for DASD data sets on
  this platform.
