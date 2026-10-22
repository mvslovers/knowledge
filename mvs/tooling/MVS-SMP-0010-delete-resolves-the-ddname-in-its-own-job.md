---
id: MVS-SMP-0010
title: SMP records ddnames, not data sets — a deleting APPLY resolves the old element's ddname in its own job, so a rename leaves the old library populated and a missing DD fails silently
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE system, SMP 4 HMASMP LVL 04.48, 2026-09-14 — throwaway ids TTMP113 / TTMP114 and a throwaway module in libraries that belong to no product: renamed last qualifier TTMPBINS JOB00317 (HMA2832, APPLY CHECK RC 12), the same with the predecessor DDs added TTMPCINS JOB00319 (works), unchanged last qualifier TTMPEINS JOB00325 (installs, old data set left populated); output quoted in mvslovers/mbt#100"
  - "mvslovers/ftpd#145 (docs issue for the pre-DELETE upgrade text) and mvslovers/ftpd#146 (the documentation written from the measurement; arm D is TTMPEINS)"
  - "MVS/CE and TK5 throwaway containers, SMP 4 HMASMP LVL 04.48, 2026-10-21 — dummy function ++VER(Z038) DELETE(TUFS150) with and without the HMASMP.LINKLIB and HMASMP.AUFSDLOD DDs (as reported in the inbox note; job numbers not carried over)"
verified_on: 2026-10-21
verified_platforms: ["MVS/CE (3.0.0)", "TK5 Update 5"]
applies_to: [ufsd, ftpd, httpd, mbt]
tags: [smp, smp4, ddname, delete, rename, hma2832, hma2833, hma3020, hma3703, linklib, steplib, mbt]
related: [ECO-0007, MVS-SMP-0007, MVS-SMP-0008, MVS-SMP-0014]
---

## The claims

1. **SMP records the ddname an element was installed through, never the data set
   behind it.** `[tested]`
2. **A SYSMOD that deletes its predecessor resolves that ddname in its own job.**
   It deletes from whatever the job's DD of that name points at, and never touches
   the predecessor's data set by itself. `[tested]`
3. **A deleting APPLY whose job lacks the DD fails silently**; the matching
   ACCEPT fails loudly. `[tested]`

The CDS `LMOD` entry shows the ddname:

```
TTMPMOD   LASTUPD         = TTMP113  TYPE=ADD
          SYSTEM LIBRARY  = OLDLIB          <- a ddname
```

mbt derives the ddname from the last qualifier of `target` and `distlib`. This
is SMP's behaviour, not that of any one project; the three throwaway tests
below used a module name and libraries that belonged to no product.

## Case 1: the last qualifier is unchanged

`FTPD.V1R0M2.LINKLIB` to `FTPD.LINKLIB`: both end in `LINKLIB`. The install
succeeds, and SMP's delete lands on the **new** library through the shared
ddname. The old data set stays populated and nothing names it in the log
(TTMPEINS, JOB00325). Re-pointing `STEPLIB` (and the authorisation entry) and
scratching the old libraries are then the actual upgrade, not housekeeping: skip
them and the old server keeps running while every condition code says the
upgrade worked (`MVS-SMP-0007`).

## Case 2: the last qualifier changes

Predecessor in `OLDLIB`, successor into `NEWLIB` (TTMPBINS, JOB00317):

```
HMA2832 ** OLDLIB DDCARD MISSING FOR SYSMOD TTMP113
HMA2260    APPLY PROCESSING TERMINATED FOR SYSMOD TTMP113
HMA2832 ** OLDLIB DDCARD MISSING FOR LOAD MODULE TTMPMOD IN SYSMOD TTMP114
HMA2260    APPLY PROCESSING TERMINATED FOR SYSMOD TTMP114
HMA3702 ** APPLY PROCESSING TERMINATED BECAUSE FUNCTION SYSMOD TTMP114 FAILED
HMA2050    APPLY PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12
```

APPLY CHECK ends RC 12 and the APPLY never runs. It fails safely: the predecessor
stays `REC APP ACC` in its library, the successor is received but not applied,
the new libraries stay empty. The failure is loud while the cause is not:
`HMA2832` names a ddname and says nothing about a renamed data set.

Adding the predecessor's DDs to each SMP step makes it work (TTMPCINS, JOB00319):

```
//HMASMP.OLDLIB   DD  DISP=SHR,DSN=IBMUSER.TTMP.OLDLIB
//HMASMP.AOLDLOD  DD  DISP=SHR,DSN=IBMUSER.TTMP.AOLDLOD
```

```
HMA2240 SUCCESSFULLY DELETED LMOD TTMPMOD ON OLDLIB LIBRARY
HMA2380 COPY SUCCESSFUL - MOD=TTMPMOD - LMOD=TTMPMOD - LIBRARY=NEWLIB - ...
HMA2270 APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TTMP114
```

The old library was emptied and ownership transferred.

mbt cannot emit those DDs yet: `[distribution.smp] delete` is a list of ids and
carries no data set names, and when the qualifiers match the two DDs would
collide on one ddname. Open as mvslovers/mbt#100 (state at ingest). `[source:
mbt#100]` Neither ufsd nor ftpd is in this case; the first project that changes
a last qualifier will be.

## A deleting APPLY with no DD for the library

Measured 2026-10-21 on an MVS/CE and a TK5 container with the dummy function of
`MVS-SMP-0014`:

- **`APPLY` without a `HMASMP.LINKLIB` DD** ends RC 04 with the same four
  `HMA2240 SUCCESSFULLY DELETED LMOD … ON LINKLIB LIBRARY` lines as a run that
  worked. The SMPAPP procedure then points `LINKLIB` at `SYS1.LINKLIB`:
  `UFSD.LINKLIB` kept all four members. Return code and messages look the same.
- **`ACCEPT` without a `HMASMP.AUFSDLOD` DD** ends RC 12:

  ```
  HMA2833 ** AUFSDLOD DDCARD MISSING
  HMA3020 ... REASON = DELETE PROCESSING FAILURE
  HMA3703 ...
  ```

  and the members of `UFSD.AUFSDLOD` stay. This one is loud.

So the only proof of a deleting APPLY is the member list of the target library.

## Rules

- A project that drops the version qualifier from its data set names must check
  which of the two cases it is in before shipping.
- After any deleting APPLY, list the target library (`MVS-SMP-0008`).
