# SMP4: a ++SRC named like a MOD in the CDS is assembled (and, if the text is valid assembler, link-edited into the system library, MVS/CE); a ++MAC named like an existing MAC is silently skipped

Source: reproduction of a collision found while testing an SMP package with `++MAC`/`++SRC` library elements (mbt#310, mbt PR #311), 2026-10-31. Re-measured on fresh containers for citable job numbers.
Platform: SMP4 `HMASMP LVL 04.48` on MVS 3.8j, two own throwaway containers. Container results, not stand results.

- MVS/CE 3.0.0, image `ghcr.io/mvslovers/mvsce@sha256:7ce810ce0fba609af00c14293d0532348a0bca3945d1a5b24adbdab2da7779e8`
- TK5 Update 5, image `ghcr.io/mvslovers/tk5@sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf593d5258dd612325c29c14c6`

## Pre-state (identical on both)

`LIST CDS` before the test (this note uses one `LIST CDS` statement per element type):

- `LISTALC` is a `MOD` (JCLIN, DISTLIB ACMDLIB, LMOD LISTALC, library `SYS1.CMDLIB`) and a `MAC` (in `AHELP`).
- `BUILD` is a `MAC` in `AMACLIB` (FMID EDM1102).
- `LISTCAT` and `PRINT` are `MAC` entries in `AHELP`.
- There is no `SRC` and no `MOD` named `BUILD`, `LISTCAT` or `PRINT`.

Only `LISTALC` was used in the collision cases below.

## Test

A one-element function SYSMOD per case, received and applied with the `SMPAPP` proc, with `DISTLIB(DLIB) SYSLIB(TLIB)` pointing at new empty PDS libraries. Then `LIST CDS` for the SYSMOD, `MOD(LISTALC)`, `SRC(...)`.

| Case | Element | Text of the element |
|---|---|---|
| A | `++SRC(LISTALC)` | REXX text (not assembler) |
| B | `++SRC(LISTALC)` | `LISTALC CSECT` / `BR 14` / `END LISTALC` |
| C (control) | `++SRC(KBNOCOLL)` | any (name not in the CDS) |
| D | `++MAC(LISTALC)` | MACRO text |

## Result

| Case | Platform | Job | APPLY RC | What SMP did |
|---|---|---|---|---|
| A | MVS/CE | KBA JOB00037 | 12 | `HMA4090 COPY SUCCESSFUL - SRC=LISTALC`, then `HMA2402 ** ASSEMBLY FAILED - MOD=LISTALC - LIBRARY=TLIB - SYSMOD=TKB0A01 - RETURN CODE=08`, `HMA3020 ... REASON = SYSTEM UTILITY FAILURE`, `HMA3703`. SYSMOD in ERROR. |
| A | TK5 Update 5 | KBA JOB00045 | 12 | same messages |
| B | MVS/CE | KBB JOB00035 (second container) | 0 | `HMA2400 ASSEMBLY SUCCESSFUL - MOD=LISTALC`, `HMA2390 LINK SUCCESSFUL - MOD=LISTALC - LMOD=LISTALC - LIBRARY=CMDLIB - SYSMOD=TKB0B01 - RETURN CODE=00`, `HMA2270`. |
| C | MVS/CE | KBC JOB00039 | 4 | `HMA4441 ASSEMBLY KBNOCOLL FOR SRC KBNOCOLL ... WILL NOT BE DONE - DISTLIB NOT DETERMINED`, `HMA4090 COPY SUCCESSFUL`. SYSMOD applied. |
| C | TK5 Update 5 | KBC JOB00046 | 4 | same |
| D | MVS/CE | KBD JOB00038 | 0 | `MAC LISTALC NOT SEL ... TKB0D01 APPLIED`, `HMA2270`. |
| D | TK5 Update 5 | KBD JOB00047 | 0 | same |

(The job return code of KBB and KBD on MVS/CE is 4 because of the later `LIST` steps, not because of APPLY.)

Case B was measured on MVS/CE only. The job numbers belong to the containers named above.

### Case A in detail

- The SYSMOD entry shows `ASSEM = LISTALC`: SMP takes a `++SRC` whose name equals a `MOD` for that module's source.
- `LIST CDS SRC(LISTALC)` shows `SRC LISTALC NOGO`, `ASSEM NAMES LISTALC`, `LOAD MOD LISTALC`, `LMOD SYSLIB CMDLIB`, `TKB0A01 ERROR`.
- The `SRC` entry is in the CDS (`LASTUPD = TKB0A01`) although the SYSMOD is in ERROR.
- `MOD LISTALC` stays at `LASTUPD = JCLIN`; nothing was link-edited.

### Case B in detail

- After APPLY, `LIST CDS MOD(LISTALC)` shows FMID and RMID = `TKB0B01` (`RMIDASM`). SMP reports a successful link-edit into `CMDLIB` (`HMA2390`) and sets the RMID of the module to the package's SYSMOD. The member in `SYS1.CMDLIB` itself was not listed before and after.

### Case C (control)

- A `++SRC` whose name is not a `MOD` is only copied: `HMA4441 ... WILL NOT BE DONE - DISTLIB NOT DETERMINED` is a warning at RC 4, not an error.

### Case D in detail

- `++MAC(LISTALC)`: SMP finds an existing `MAC` of that name and does not select the element. The status is `NOT SEL`, APPLY RC 0.
- Nothing is copied: the target library has 0 members, also the DLIB (checked on TK5 only, via the mvsMF member list).

### Original occurrence

First found with the real package of mbt#310 (114 `++MAC` and 121 `++SRC` members): MVS/CE job ELT31INS JOB00054 ended RC 12 with `HMA2402 ** ASSEMBLY FAILED - MOD=LISTALC - LIBRARY=SAMPLES - SYSMOD=TELT100`. One member of the package had the name of the TSO command `LISTALC`. After renaming it, that error did not recur. JOB00054 comes from a container that was torn down afterwards; the reproduction above is the citable one.

## What follows for packagers

- A `++SRC` is not just a file copy. If its name equals a `MOD` in the target CDS, SMP assembles it and, if the assembly succeeds (measured on MVS/CE with valid assembler text), reports a link-edit into the library of the matching `LMOD` and sets the module's RMID to the package's SYSMOD. With non-assembler text (REXX, C, data) the assembly fails: APPLY RC 12, SYSMOD in ERROR, and an `SRC` entry is left behind in the CDS.
- A `++MAC` whose name equals an existing `MAC` is skipped with status `NOT SEL` and APPLY RC 0. Nothing in the return code shows it; only the element status in the output (and the empty target library) does.
- Collision measured: `LISTALC`, which is a `MOD` and a `MAC` at once (cases A, B, D). `BUILD`, `LISTCAT` and `PRINT` are present as `MAC` in the CDS (pre-state); a collision with them was not tried.
- Before the first install of a package with library elements, check every member name against the target CDS, one element type per statement (as done in this note):

  ```
  LIST CDS MOD(name1,name2,...) .
  LIST CDS SRC(name1,name2,...) .
  LIST CDS MAC(name1,name2,...) .
  ```

  Rename every hit in the package before it is built.
- Keep a name list of the members of the package and compare it with the CDS as part of the install check, not only the library member list.
