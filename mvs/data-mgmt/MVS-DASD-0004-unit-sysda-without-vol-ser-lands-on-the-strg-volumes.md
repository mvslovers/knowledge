---
id: MVS-DASD-0004
title: UNIT=SYSDA without VOL=SER puts a new data set on the STRG volumes, never on SYSRES — and SMP4 has no DDDEFs, so the calling JCL decides where a product's libraries go
status: tested
platform: [mvs38j]
sources:
  - "Own throwaway containers, 2026-10-31, one IPL or job per case (as reported in the inbox note): TK5 ghcr.io/mvslovers/tk5@sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf593d5258dd612325c29c14c6 (built 2026-10-18; UFSD, HTTPD, mvsMF and FTPD SMP-installed, so not a plain TK5) and MVS/CE 3.0.0 ghcr.io/mvslovers/mvsce@sha256:7ce810ce0fba609af00c14293d0532348a0bca3945d1a5b24adbdab2da7779e8; jobs TK5 JOB00052 (SYSDA), JOB00057 (VOL=SER=SYSRES), MVS/CE JOB00044, JOB00045, JOB00047"
  - "SMP4 HMASMP LVL 04.48, message HMA2033 (no DDDEFs); the proc SMPAPP of both images (as reported; the proc text was not re-read at ingest)"
verified_on: 2026-10-31
verified_platforms: ["TK5 (image of 2026-10-18)", "MVS/CE 3.0.0"]
applies_to: [brexx370, mbt, ufsd, ftpd, httpd, mvsmf]
tags: [sysda, unit, volser, strg, sysres, smp4, dddef, hma2033, smpapp, volumes, tk5, mvs-ce, ief210i, rakf]
related: [MVS-DASD-0001, MVS-LNK-0006, ECO-0007]
---

## The claims

- **A new data set with `UNIT=SYSDA` and no `VOL=SER` lands on the STRG volumes, never on SYSRES or on the
  volume of the IBM distribution libraries.** `[tested]`

  | | TK5 | MVS/CE |
  |---|---|---|
  | `UNIT=SYSDA`, no `VOL=SER` | **TSO001-003** (JOB00052) | **WORK00/WORK01** (JOB00044, JOB00045, JOB00047) |
  | same with `VOL=SER=<SYSRES>` | works (JOB00057) | works (JOB00047) |

- **A DD for a new data set without `UNIT` is a JCL error** (`IEF210I`). `[tested]`
- **SMP4 (HMASMP LVL 04.48) has no DDDEFs** (`HMA2033`). The volume of a product's target and distribution
  libraries comes from the JCL of the calling job alone: `SMPAPP` names `SYS1.xxx` with `DISP=SHR` and no
  volume, and only `SMPTLIB` carries `VOL=SER=&TVOL`. Same on both systems. `[tested]` (as reported)

## Volumes

| | TK5 | MVS/CE |
|---|---|---|
| SYSRES / IPL volume | TK5RES (3390) | MVSRES (3350) |
| volume of the IBM distribution libraries (`SYS1.A*`) | TK5DLB (3390) | SMP000 (3350) |
| STRG volumes (what `SYSDA` picks) | TSO001-003 | WORK00, WORK01 |
| free space | TK5RES 567 cyl + 48 trk, TK5DLB 614 cyl + 150 trk | MVSRES 276 cyl, SMP000 158 cyl + 26 trk |

The figures are those of the images named in the sources, measured once.

## What existing products do

Not a convention, and different per system. `[tested]`

- TK5, RAKF (not IBM): target libraries on TK5RES, distribution libraries (`RAKF.A*`) on TK5DLB.
- TK5, UFSD / HTTPD / mvsMF / FTPD: target and distribution libraries both on TSO001. That comes from the
  image build, which replaces `UNIT=SYSDA` by `UNIT=3390,VOL=SER=TSO001` in the install jobs; it is not a
  product convention.
- MVS/CE, RAKF: load modules in `SYS1.LINKLIB` / `SYS1.CMDLIB` (MVSRES), distribution libraries
  `SYSGEN.RAKF.V2R0M0.*` on PUB001, not on SMP000.

## Consequences

- A target library of a product that goes into the link list must be placed deliberately: `SYSDA` alone puts it
  on a STRG volume, which has to be online at IPL (`MVS-LNK-0006`).
- A package that wants its libraries on a specific volume has to say so in the JCL it generates; SMP does not
  know where they go.

## Not measured

A real SMP install of BREXX/370; 3330 geometry; the peak space of an install (RECEIVE libraries). The space
need of BREXX/370 3.0.0 (7-8 cylinders per side on a 3350, 5-6 on a 3390) was calculated from the generated
package without a real SMP run; it is not recorded here as a measurement.

Container results, not stand results.
