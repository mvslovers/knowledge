---
id: MVS-DASD-0002
title: SCRATCH (SVC 29) deletes unexpired data sets on MVS 3.8j once the system date is 2000 or later
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway container (image and Hercules version not recorded), 2026-10-19: probe MEAS2 (container-local JOB00026) and test/mvs/tstvolad.c (container-local JOB00023)"
  - "libc370 PR #681 (merged 2026-10-19, closes #143), body paragraph 'Not asserted on MVS' — same numbers: expdt=1A0142, CVTDATE 0126292F"
  - "libc370 v2.24.0 — test/mvs/tstvolad.c, jcl/setvolad.jcl (RETPD=30 data sets), src/mvs/dscb/@@dadsm.c (statuserr)"
  - "libc370 Library Reference, mvs-datasets chapter, notes of __scratch/__renamev (docs/books/ref/mvs-datasets.typ)"
  - "mvslovers/mvs38src, work/macros/mvsce-2.1.4-target: IECSDSL1 (DS1EXPDT XL3) and CVT (CVTDATE, packed decimal word)"
verified_on: 2026-10-19
verified_platforms: ["MVS/CE"]
applies_to: [libc370, mvsmf]
tags: [scratch, svc29, dadsm, expiration, retpd, ds1expdt, cvtdate, y2k, igg0290a, dscb, purge-date]
related: [MVS-DASD-0001]
---

## The claim

SCRATCH issued **without** the purge-date override (CAMLST `OVRD`) deletes a
data set whose expiration date has not been reached. On a system whose date
is in 2000 or later every expiration date looks past to SCRATCH.
`[tested]`

Consequence: on MVS 3.8j with a current date, `LABEL=RETPD=` / `EXPDT=` do not
protect a DASD data set from SCRATCH. Do not rely on them as a safety net.

## The measurement

Platform: MVS 3.8j (MVS/CE image, throwaway container), system date
2026-10-19 (CVTDATE day 292).

Probe MEAS2 (an OBTAIN of the format-1 DSCB plus CVTDATE, written ad hoc;
the data set `IBMUSER.TSTVOLAD.EXP` was uncataloged on volume WORK01 and
created with `LABEL=RETPD=30`), container-local JOB00026:

```
MEAS2 rc=0 credt=1A0124 expdt=1A0142 cvtdate=0126292F
```

- `credt` = year X'1A' (26), day X'0124' (292).
- `expdt` = year X'1A', day X'0142' (322): 30 days later.
- `cvtdate` = X'0126292F': century digit 1, year 26, day 292.

So the DSCB year is **two digits** (26), while CVTDATE carries the century
digit.

`test/mvs/tstvolad.c` (libc370), data sets created by `jcl/setvolad.jcl`,
run by `jcl/tstvolad.jcl`; container-local JOB00023 (an earlier version of the
probe that scratched without override first):

```
+TSTVOLAD   __scratch(EXP, WORK01, 0) = 0 errno 0
+TSTVOLAD   __scratch(EXP, WORK01, OVRD) = 8
```

SCRATCH without override returned 0 and deleted the 30-day-retention data
set; the following OVRD call found nothing left (8). The released probe
(libc370 2.24.0) repeats the no-override case on `IBMUSER.TSTVOLAD.EXP2`
and accepts either 0 or 8/`EPERM`; it records the result instead of
asserting it. The same numbers (`expdt=1A0142`, `0126292F` read as 126) are in
the body of libc370 PR #681.

Not measured: a system date before 2000, where the two years would agree.

## The mechanism `[inferred]`

From the inbox note; the listing was not re-read at ingest. The note says
that DADSM module `IGG0290A` (SCRATCH), unless the override bit is set,
converts CVTDATE to a binary year byte and a day, then compares with the
DSCB's expiration date:

```
         CLC   DS1EXPDT(3),FIELD1+5     COMPARE PURGE DATE AND DATE
         BH    NOPURGE
```

and that the code treats the date halfword as `0YYZ` (century digit 0). From
2000 on CVTDATE has century digit 1, the year byte becomes 100+yy (126 in
2026) and the DSCB year stays 26 (X'1A'); X'1A....' is never higher than
X'7E....', so the `NOPURGE` path (volume status 3, "purge date error") is never
taken.

What was read at ingest: the format-1 DSCB field is `DS1EXPDT DS XL3` (IECSDSL1)
and `CVTDATE` is a packed-decimal word (CVT macro), both in the MVS/CE 2.1.4
macro library copy in mvslovers/mvs38src `[source: IECSDSL1, CVT]`. The
measured values above fit the mechanism.

## What it means for callers

- libc370 `__scratch()` (first released in 2.24.0) maps volume status 3 to
  `EPERM` `[source: libc370 src/mvs/dscb/@@dadsm.c, function statuserr, v2.24.0]`.
  On 3.8j with a current date that code cannot occur for SCRATCH today; the
  Library Reference says so.
- Other utilities that scratch through the same DADSM module (IEHPROGM
  SCRATCH, IDCAMS DELETE of a non-VSAM data set) are presumably affected too
  `[inferred, not tested]`.
