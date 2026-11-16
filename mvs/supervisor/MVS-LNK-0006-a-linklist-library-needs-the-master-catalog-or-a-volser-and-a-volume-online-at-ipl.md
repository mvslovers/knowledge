---
id: MVS-LNK-0006
title: A LNKLST00 library is found through the master catalog or a volser in the entry — and its volume must be online at IPL (IEA327I, IEA317A)
status: tested
platform: [mvs38j]
sources:
  - "Own throwaway containers, 2026-10-31, one IPL per case, one run each (as reported in the inbox note; maintainer approved the inbox entry 2026-11-01): TK5 ghcr.io/mvslovers/tk5@sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf593d5258dd612325c29c14c6 (built 2026-10-18, image label Update 5; UFSD, HTTPD, mvsMF and FTPD SMP-installed) and MVS/CE 3.0.0 ghcr.io/mvslovers/mvsce@sha256:7ce810ce0fba609af00c14293d0532348a0bca3945d1a5b24adbdab2da7779e8 (created 2026-10-22); job numbers in the table belong to those containers"
verified_on: 2026-10-31
verified_platforms: ["TK5 (image of 2026-10-18)", "MVS/CE 3.0.0"]
applies_to: [brexx370, mbt, ufsd, ftpd, httpd, mvsmf]
tags: [lnklst, lnklst00, linklist, master-catalog, user-catalog, volser, iea327i, iea317a, nip, ipl, sysres, s806, hao]
related: [MVS-LNK-0001, MVS-DASD-0004]
---

## The claims

- **The system finds a LNKLST library through the master catalog.** A library reachable only through an alias
  in a user catalog is not loaded: `IEA327I LINK LIBRARY DATA SETS NOT FOUND`, and later S806-4. `[tested]`
  The remedy is a volser in the `LNKLST00` entry; then the catalog is not consulted for the data set.
  `[tested]` (TK5 only)
- **SYSRES is not required.** Any volume works if it is online at IPL. `[tested]`
- **A volume that is not online at IPL stops NIP at `IEA317A` on the TK5 image.** The MVS/CE image goes on
  only because its Hercules `hao` rule answers every console prompt with a blank line; without such a rule
  it would wait as well. That is a property of the image, not of MVS. `[tested]` for the behaviour of the two
  images; the reading of the `hao` rule as the reason is `[inferred]`.
- **Changing `LNKLST00` needs an IPL** (`MVS-LNK-0001`).

## The cases

A test library was put into `LNKLST00` and the system IPLed once per case.

| Case | TK5 | MVS/CE |
|---|---|---|
| A: cataloged in the master catalog, on the SYSRES volume | loaded, no message (JOB00061) | loaded, no message (JOB00052) |
| B: reachable only through an alias in a user catalog, entry without volser | `IEA327I LINK LIBRARY DATA SETS NOT FOUND`, not loaded, later S806-4 (JOB00062) | same message, S806-4 (JOB00054) |
| B2: user catalog, entry with volser, e.g. `BREXX.LINKLIB(TK5RES)` | loaded (JOB00063) | not measured |
| C: master catalog, a volume other than SYSRES that is online at IPL | loaded, with and without volser (JOB00064, JOB00065) | loaded (JOB00056, JOB00058) |
| D: the volume is not online at IPL | `IEA317A SPECIFY UNIT ... OR CANCEL`, NIP stops; no way forward found (CANCEL in seven spellings; unit replies gave `IEA310A`/`IEA318I`) | `IEA317A`, then `IEA327I`, library missing, IPL goes on (JOB00059) |

## Not established

- How to continue after `IEA317A` on the TK5 image.
- Repeats of the cases: one run each. Two TK5 containers crashed (exit 134) in case D, probably through an endless `hao` loop in the image
  script; not proven.
- MVS/CE for case B2; a real SMP install of BREXX/370.

Container results, not stand results.
