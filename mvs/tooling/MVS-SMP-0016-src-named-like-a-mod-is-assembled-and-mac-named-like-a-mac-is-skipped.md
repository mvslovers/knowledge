---
id: MVS-SMP-0016
title: SMP4 assembles a ++SRC named like a MOD in the CDS (and link-edits it if the text assembles) and silently skips a ++MAC named like an existing MAC
status: tested
platform: [mvs38j]
sources:
  - "Reproduction of a collision found while testing an SMP package with ++MAC/++SRC library elements (mvslovers/mbt#310, PR #311), 2026-10-31, on two fresh throwaway containers for citable job numbers: MVS/CE 3.0.0 (ghcr.io/mvslovers/mvsce@sha256:7ce810ce0fba609af00c14293d0532348a0bca3945d1a5b24adbdab2da7779e8) and TK5 Update 5 (ghcr.io/mvslovers/tk5@sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf593d5258dd612325c29c14c6); SMP4 HMASMP LVL 04.48 on both"
  - "First occurrence, the real package of mbt#310 (114 ++MAC and 121 ++SRC members): MVS/CE job ELT31INS JOB00054 ended RC 12 with HMA2402 ** ASSEMBLY FAILED - MOD=LISTALC - LIBRARY=SAMPLES - SYSMOD=TELT100; the container was torn down, the reproduction below is the citable one"
verified_on: 2026-10-31
verified_platforms: ["MVS/CE (3.0.0)", "TK5 Update 5 (image with UFSD, HTTPD, mvsMF, FTPD SMP-installed)"]
applies_to: [mbt, brexx370]
tags: [smp, smp4, src, mac, mod, collision, assembly, hma2402, hma2400, hma4441, hma4090, not-sel, cds, packaging, listalc]
related: [ECO-0007, MVS-SMP-0006, MVS-SMP-0007, MVS-SMP-0011]
---

## The claims

1. **A `++SRC` is not just a file copy.** If its name equals a `MOD` in the target CDS, SMP takes it for that
   module's source and assembles it. `[tested]`
   - With text that is not assembler (REXX, C, data) the assembly fails: APPLY RC 12, the SYSMOD in ERROR, and
     an `SRC` entry is left behind in the CDS although the SYSMOD failed. The `MOD` stays as it was
     (`LASTUPD = JCLIN`); nothing is link-edited. Measured on MVS/CE and TK5.
   - With valid assembler text the assembly succeeds and SMP reports a link-edit into the library of the
     matching `LMOD` and sets the module's `FMID` and `RMID` to the package's SYSMOD. Measured on MVS/CE only.
     The member in `SYS1.CMDLIB` itself was not listed before and after, so the replacement of the load
     module is what SMP reports, not something the member list confirmed.
2. **A `++MAC` whose name equals an existing `MAC` is skipped.** Status `NOT SEL`, APPLY RC 0, nothing copied
   (the target library has 0 members, the DLIB too; checked on TK5 only, through the mvsMF member list).
   Nothing in the return code shows it; only the element status in the output does. This is the ownership
   wall of `MVS-SMP-0006` for macros. `[tested]`
3. **A `++SRC` whose name is not a `MOD` is only copied.** `HMA4441 ASSEMBLY ... WILL NOT BE DONE - DISTLIB NOT
   DETERMINED` is a warning at APPLY RC 4, not an error. `[tested]`

## Pre-state, identical on both systems

`LIST CDS` before the test, one statement per element type:

- `LISTALC` is a `MOD` (JCLIN, DISTLIB ACMDLIB, LMOD LISTALC, library `SYS1.CMDLIB`) and a `MAC` (in `AHELP`).
- `BUILD` is a `MAC` in `AMACLIB` (FMID EDM1102); `LISTCAT` and `PRINT` are `MAC` entries in `AHELP`.
- There is no `SRC` and no `MOD` named `BUILD`, `LISTCAT` or `PRINT`.

Only `LISTALC` was used in the collision cases; a collision with `BUILD`, `LISTCAT` or `PRINT` was not tried.

## The test

A one-element function SYSMOD per case, received and applied with the `SMPAPP` proc, `DISTLIB(DLIB)
SYSLIB(TLIB)` pointing at new empty PDS libraries; then `LIST CDS` for the SYSMOD, `MOD(LISTALC)`, `SRC(...)`.

| Case | Element | Text of the element |
|---|---|---|
| A | `++SRC(LISTALC)` | REXX text (not assembler) |
| B | `++SRC(LISTALC)` | `LISTALC CSECT` / `BR 14` / `END LISTALC` |
| C (control) | `++SRC(KBNOCOLL)` | any (name not in the CDS) |
| D | `++MAC(LISTALC)` | MACRO text |

| Case | Platform | Job | APPLY RC | What SMP did |
|---|---|---|---|---|
| A | MVS/CE | KBA JOB00037 | 12 | `HMA4090 COPY SUCCESSFUL - SRC=LISTALC`, then `HMA2402 ** ASSEMBLY FAILED - MOD=LISTALC - LIBRARY=TLIB - SYSMOD=TKB0A01 - RETURN CODE=08`, `HMA3020 ... REASON = SYSTEM UTILITY FAILURE`, `HMA3703`. SYSMOD in ERROR. |
| A | TK5 | KBA JOB00045 | 12 | same messages |
| B | MVS/CE | KBB JOB00035 (second container) | 0 | `HMA2400 ASSEMBLY SUCCESSFUL - MOD=LISTALC`, `HMA2390 LINK SUCCESSFUL - MOD=LISTALC - LMOD=LISTALC - LIBRARY=CMDLIB - SYSMOD=TKB0B01 - RETURN CODE=00`, `HMA2270`. |
| C | MVS/CE | KBC JOB00039 | 4 | `HMA4441 ASSEMBLY KBNOCOLL FOR SRC KBNOCOLL ... WILL NOT BE DONE - DISTLIB NOT DETERMINED`, `HMA4090 COPY SUCCESSFUL`. SYSMOD applied. |
| C | TK5 | KBC JOB00046 | 4 | same |
| D | MVS/CE | KBD JOB00038 | 0 | `MAC LISTALC NOT SEL ... TKB0D01 APPLIED`, `HMA2270`. |
| D | TK5 | KBD JOB00047 | 0 | same |

The job return code of KBB and KBD on MVS/CE is 4 because of the later `LIST` steps, not because of APPLY.
The job numbers belong to the containers named above.

Case A in detail:

- The SYSMOD entry shows `ASSEM = LISTALC`.
- `LIST CDS SRC(LISTALC)` shows `SRC LISTALC NOGO`, `ASSEM NAMES LISTALC`, `LOAD MOD LISTALC`, `LMOD SYSLIB
  CMDLIB`, `TKB0A01 ERROR`; the `SRC` entry is in the CDS (`LASTUPD = TKB0A01`) although the SYSMOD is in ERROR.

Case B in detail: after APPLY, `LIST CDS MOD(LISTALC)` shows FMID and RMID = `TKB0B01` (`RMIDASM`).

The first occurrence: one member of the mbt#310 package had the name of the TSO command `LISTALC`. After it was
renamed, the error did not recur.

## What follows for packagers

- Before the first install of a package with library elements, check every member name against the target CDS,
  one element type per statement, and rename every hit in the package before it is built:

  ```
  LIST CDS MOD(name1,name2,...) .
  LIST CDS SRC(name1,name2,...) .
  LIST CDS MAC(name1,name2,...) .
  ```

- Compare the name list of the package with the CDS as part of the install check, not only the member list of
  the library. (The check is the packager's remedy; it was not itself run against a collision-free package.)
- Read the element status of a `++MAC` in the output; RC 0 does not show a skipped macro (`MVS-SMP-0007`).

Container results, not stand results.
