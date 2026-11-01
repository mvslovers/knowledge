# LNKLST libraries: master catalog or volser, volume online at IPL (IEA327I, IEA317A), and where `UNIT=SYSDA` lands

Source: measurement of where SMP target and distribution libraries go and what LNKLST needs, 2026-10-31.
Platform: own throwaway containers, one IPL per case. Container results, not stand results.
Maintainer approved this inbox entry (2026-11-01).

Images:

- TK5: `ghcr.io/mvslovers/tk5:latest`, digest `sha256:2e4210c4c2d2…14c6`, built 2026-10-18. The image label says Update 5; the running MVS does not show it. UFSD, HTTPD, mvsMF and FTPD are SMP-installed in it, so it is not a plain TK5.
- MVS/CE: `ghcr.io/mvslovers/mvsce:latest`, digest `sha256:7ce810ce…79e8`, created 2026-10-22, MVS/CE 3.0.0.

## LNKLST at IPL

A test library was put into `LNKLST00` and the system IPLed once per case.

| Case | TK5 | MVS/CE |
|---|---|---|
| A: cataloged in the master catalog, on the SYSRES volume | loaded, no message (JOB00061) | loaded, no message (JOB00052) |
| B: reachable only through an alias in a user catalog, entry without volser | `IEA327I LINK LIBRARY DATA SETS NOT FOUND`, not loaded, later S806-4 (JOB00062) | same message, S806-4 (JOB00054) |
| B2: user catalog, entry with volser, e.g. `BREXX.LINKLIB(TK5RES)` | loaded (JOB00063) | not measured |
| C: master catalog, a volume other than SYSRES that is online at IPL | loaded, with and without volser (JOB00064, JOB00065) | loaded (JOB00056, JOB00058) |
| D: the volume is not online at IPL | `IEA317A SPECIFY UNIT … OR CANCEL`, NIP stops; no way forward found (CANCEL in seven spellings, unit replies gave `IEA310A`/`IEA318I`) | `IEA317A`, then `IEA327I`, library missing, IPL goes on (JOB00059) |

What follows, each from one run:

- The system finds a LNKLST library **through the master catalog**. An alias in a user catalog is not enough (case B). The remedy is a volser in the `LNKLST00` entry (case B2); then the catalog is not consulted for the data set.
- **SYSRES is not required.** Any volume works if it is online at IPL (case C).
- A volume that is not online at IPL stops NIP at `IEA317A` on the TK5 image. The MVS/CE image goes on only because its Hercules `hao` rule answers every console prompt with a blank line; without such a rule it would wait as well. This is a property of the image, not of MVS.
- Two TK5 containers crashed (exit 134) in case D, probably through an endless `hao` loop in the image script. Not proven.
- Changing `LNKLST00` needs an IPL (see `MVS-LNK-0001`).

## Where `UNIT=SYSDA` without `VOL=SER` lands

| | TK5 | MVS/CE |
|---|---|---|
| New data set, `UNIT=SYSDA`, no `VOL=SER` | **TSO001-003** (STRG volumes), never SYSRES or the DLIB volume (JOB00052) | **WORK00/WORK01** (STRG volumes), never SYSRES or the DLIB volume (JOB00044, JOB00045, JOB00047) |
| Same with `VOL=SER=<SYSRES>` | works (JOB00057) | works (JOB00047) |

A DD for a new data set without `UNIT` is a JCL error (`IEF210I`).

SMP4 (HMASMP LVL 04.48) has no DDDEFs (HMA2033). The volume placement of the libraries comes from the JCL of the calling job alone: SMPAPP names `SYS1.xxx` with `DISP=SHR` and no volume; only `SMPTLIB` carries `VOL=SER=&TVOL`. Same on both systems.

## Volumes

| | TK5 | MVS/CE |
|---|---|---|
| SYSRES / IPL volume | TK5RES (3390) | MVSRES (3350) |
| volume of the IBM distribution libraries (`SYS1.A*`) | TK5DLB (3390) | SMP000 (3350) |
| STRG volumes (what `SYSDA` picks) | TSO001-003 | WORK00, WORK01 |
| free space | TK5RES 567 cyl + 48 trk, TK5DLB 614 cyl + 150 trk | MVSRES 276 cyl, SMP000 158 cyl + 26 trk |

Space need of a product of the size of BREXX/370 3.0.0 (target libraries and distribution libraries, calculated from the generated package, no real SMP run): 7-8 cylinders per side on a 3350, 5-6 on a 3390.

## Convention of existing products

- TK5, RAKF (not IBM): target libraries on TK5RES, distribution libraries (`RAKF.A*`) on TK5DLB.
- TK5, UFSD/HTTPD/mvsMF/FTPD: target and distribution libraries both on TSO001. That comes from the image build, which replaces `UNIT=SYSDA` by `UNIT=3390,VOL=SER=TSO001` in the install jobs; it is not a product convention.
- MVS/CE, RAKF: load modules in `SYS1.LINKLIB`/`SYS1.CMDLIB` (MVSRES), distribution libraries `SYSGEN.RAKF.V2R0M0.*` on PUB001, not on SMP000. No uniform convention.

## Not measured

A real SMP install of BREXX; 3330 geometry; peak space of an install (RECEIVE libraries); how to continue after `IEA317A` on the TK5 image; repeats of the LNKLST cases (one run each).
