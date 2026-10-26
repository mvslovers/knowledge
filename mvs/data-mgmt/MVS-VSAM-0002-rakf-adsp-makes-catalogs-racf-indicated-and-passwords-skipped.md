---
id: MVS-VSAM-0002
title: Under RAKF a normal job's DEFINE makes catalogs and entries RACF-indicated, and VSAM then does not check cluster passwords in that catalog
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway containers (image ghcr.io/mvslovers/mvsce:latest as of 2026-10-20, job log '370/148 VS2 R03.8 MVSC'; image digest, Hercules version and RAKF version not recorded), 2026-10-20: container A job DEF623 (JOB00020) and JOB00022; container B JOB00019/00020/00022; container C JOB00019 (TSTVSPW) and JOB00020 (TSTVSPW2). Job numbers are container-local and restart in each container."
  - "libc370 PR #698 (merged 2026-10-20, released in 2.25.0, closes #623): body section 'What MVS 3.8j / MVS/CE did'; test/mvs/tstvsox.c and jcl/tstvsox.jcl at v2.25.0"
  - "libc370 Library Reference, VSAM chapter, __vsopenx notes 'Passwords' (docs/books/ref/mvs-vsam.typ, main) — states the same measurements, including the not-RACF-indicated catalog case"
  - "RAKF (MVS-SYSGEN/RAKF) SRCLIB/ICHSFR00.hlasm, RACINIT path: commit 534c817 (2022-09-02 import) line 470, tag v2.0.0 (commit 019acf4) line 623; JCLIN/TRKF200.jcl (SYSLIB = SYS1.MACLIB)"
  - "mvslovers/mvs38src, work/macros/mvsce-2.1.4-target/IHAACEE (ACEEFLG1, ACEEFLG2 bit definitions)"
verified_on: 2026-10-20
verified_platforms: ["MVS/CE"]
applies_to: [libc370]
tags: [vsam, rakf, racf, adsp, jscbadsp, aceeadsp, catalog, password, iec161i, acberflg, define, listcat, idcams]
related: [ECO-0008, MVS-VSAM-0003, MVS-SEC-0010]
---

## The claim

On a system with RAKF (MVS/CE, TK5):

1. A user catalog and every entry that a normal job DEFINEs into it are
   **RACF-indicated** (`RACF (YES)` in LISTCAT). `[tested]`
2. In a RACF-indicated catalog VSAM **does not check the passwords** of the
   clusters in it, whatever the cluster's own indication. A cluster defined
   with READPW/UPDATEPW/MASTERPW opens with the right password, a wrong one
   and none. `[tested]` That access control is then RAKF's is the
   expectation for a RACF-indicated catalog, not traced. `[inferred]`
3. In a catalog that is **not** RACF-indicated, VSAM checks the cluster
   password at OPEN, also for a cluster that is RACF-indicated itself.
   `[tested]`

So the deciding fact is the catalog's RACF indication, not the cluster's.

For how RAKF matches profiles and what it grants, see the RAKF documents of
this KB.

## 1. DEFINE under a normal job gives RACF (YES) everywhere

- Container A, job DEF623 (JOB00020): a new user catalog `LIBC623.UCAT` with
  `MASTERPW(CATPW)`. LISTCAT ALL shows RACF (YES) on every cluster, on the AIX
  and path entries, and on the UCAT's cluster entry itself. Only the UCAT's own
  data and index components show RACF (NO).
- Container B: the LISTCAT in the LOAD step of `jcl/tstvsox.jcl`
  (JOB00019/00020/00022) shows the same for the `VSOX623.*` entries (recorded
  less closely than in A).

## 2. In that catalog, passwords were not checked

A KSDS in `LIBC623.UCAT`, defined with `READPW(RDPW) UPDATEPW(UPPW)
MASTERPW(MSPW) ATTEMPTS(0)`, opened with rc 0 in every case:

- `vsopen()` of libc370 2.24.1, no password: container A JOB00022 and
  container B JOB00022, step RED.
- `__vsopenx()` (libc370 2.25.0) with no password, with "XXXX" and with
  "RDPW": container A JOB00022 step GREEN (no IEC161I, no WTOR); container B
  JOB00022 step GREEN, case (d) of `tstvsox.c`.

## 3. In a catalog that is not RACF-indicated, passwords are checked

Container C (own, same image). A helper, NOADSP (AC=1, scratch, not in any
repo), clears `JSCBADSP` (JSCB+X'10E', bit X'40') and LINKs IDCAMS. Catalog
`VSPW623.UCAT` on WORK00 with `MASTERPW(CATPW)`; all clusters
`KEYS(8 0) READPW(RDPW) UPDATEPW(UPPW) MASTERPW(MSPW) ATTEMPTS(0)`. Probe:
scratch `tstvspw.c` against libc370 2.25.0; it calls `__vsopenx()` and, for the
diagnosis only, repeats the open through the library's internal open to read
ACBERFLG.

JOB00019 (TSTVSPW): NOADSP wrote `JSCBFBYT X'40' AUTH 1`, `JSCBFBYT now X'00'`,
`LINK IDCAMS rc 0`. Step DEFN (through NOADSP) defined the UCAT and
`VSPW623.PWN`; step DEFR (plain IDCAMS, same job) defined `VSPW623.PWR`.
LISTCAT: UCAT, PWN and PWR all RACF (NO). So the cleared `JSCBADSP` held for
the later steps of the same job: per job, not per step (or at least not reset
at step start).

| case | result |
|---|---|
| PWN, no password | `__vsopenx()` rc 153 (EVSOPEN), ACBERFLG X'98', `IEC161I 040(056,006,IGG0CLBM)-002` |
| PWN, wrong password "XXXX" | rc 153, ACBERFLG X'98', `IEC161I 040(056,002,IGG0CLBM)-002` |
| PWN, right password "RDPW" | rc 0, ACBERFLG X'00', ACBOFLGS X'12', record read |

JOB00020 (TSTVSPW2), a new job without NOADSP: step DEFC (plain IDCAMS)
defined `VSPW623.PWC` into the same (RACF (NO)) catalog. LISTCAT: PWC RACF
(YES) on cluster, data and index, so `JSCBADSP` is on again in a new job. PWC,
no password: rc 153, ACBERFLG X'98', `IEC161I 040(056,006,IGG0CLBM)-002`:
refused. So a cluster that is RACF-indicated itself is still
password-checked when its catalog is not.

No WTOR and no IEC301A (the clusters have `ATTEMPTS(0)`). Probe 3/3, CC 0000.

## Why: ADSP `[source]` for RAKF's side, the rest `[inferred]`

RAKF's RACINIT builds the ACEE with

```
         OI    ACEEFLG1,ACEERACF+ACEECNTL
```

`[source: RAKF SRCLIB/ICHSFR00.hlasm, RACINIT path; line 470 in commit 534c817, line 623 at v2.0.0]`

In the system's `IHAACEE` macro (MVS/CE 2.1.4 copy in mvslovers/mvs38src),
`ACEERACF` is X'01' and `ACEEADSP` is X'40' ("AUTOMATIC DATA SECURITY
PROTECTION"), both bits of `ACEEFLG1`; `ACEECNTL` is X'40' as well, but a bit of
`ACEEFLG2` (CONTROL authority). `OI ACEEFLG1,ACEERACF+ACEECNTL` therefore sets
X'41' in `ACEEFLG1`: RACF-defined **and automatic data set protection** for
every user `[source: IHAACEE]`. The RAKF source has no comment on the line;
whether the ADSP effect is intended was not determined.

Open question at capture time was whether RAKF's own macro copy defines these
bits the same way. Answer: the RAKF repository contains no copy of
IHAACEE; `ICHSFR00` is assembled against `SYS1.MACLIB` (`JCLIN/TRKF200.jcl`,
`SYSLIB DD`) and uses the system macro. The RAKF release in the measured
containers was not recorded; the instruction was read in the 2022 source import
and in v2.0.0, not in the RAKF 1.2.6 deck that [ECO-0008] names as the deployed baseline.

The rest of the chain is from the inbox note; the listings were not re-read at
ingest `[inferred]`:

- IGG0CLAL (catalog DEFINE), lines 2566/2572 in the note: `IF JSCBADSP=ON |
  CTGFVRON=ON` (`TM JSCBADSP,X'40'`) leads to RACF definition of the new
  entry. Container C measures the same switch: clearing `JSCBADSP` gave RACF
  (NO) entries.
- IGG0CLB6 (IGGPCKCC, the security check, statements 0263-0292 and 869-957 in
  the note): VSAM first checks whether the catalog or entity is RACF-defined;
  for a RACF-defined catalog, RACF definition is implied for its entries;
  password information is extracted only "IF THE CATALOG IS NOT RAC-DEFINED".
  This fits sections 2 and 3.

Not found in any source: that the initiator sets `JSCBADSP` from `ACEEADSP`
`[inferred]`. Not traced: why RAKF's answer for the cluster lets every open
through (what RAKF's RACHECK returned) `[not examined]`.

## What it means

- On a system with RAKF, a user catalog that a normal job DEFINEs is
  RACF-indicated; VSAM passwords of the clusters in it are not checked
  (access control is expected to be RAKF's `[inferred]`).
- To get password checking, DEFINE the catalog in an address space where
  `JSCBADSP` is off (container C did it with an authorized helper); then a
  missing or wrong password fails OPEN with ACBERFLG X'98' and IEC161I 040.
  Define protected clusters with `ATTEMPTS(0)` so VSAM does not wait for an
  operator reply.
- libc370 2.25.0 `__vsopenx()` takes the password; its Library Reference
  documents the same behaviour.
