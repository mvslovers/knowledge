---
id: MVS-LNK-0001
title: Two link-list changes that fail with IEA703I 106-F until the next IPL — a new extent, and a compress that moves resident-BLDL modules
status: tested
platform: [mvs38j]
sources:
  - "MVSCE-LAB 2026-09-25: SYS2.LINKLIB grew from 1 to 3 extents on an IEBCOPY update (JOB01199); modules in the new extents failed 106-F until the IPL"
  - "MVSCE-LAB 2026-09-26: SMP APPLY of usermod ZMG0002 gave SYS1.CMDLIB a second extent (JOB01330); every EXEC failed 106-F (JOB01332) until the IPL"
  - "MVSCE-LAB 2026-09-27: IEBCOPY compress in place of SYS1.CMDLIB (JOB01355, RC 0, extents unchanged, VTOC listing JOB01357); console afterwards: IEA703I 106-F for ALLOC, LOGON, LOGOFF; cured by an IPL"
  - "SYS1.PARMLIB(IEABLD00) on MVSCE-LAB: ALLOC, ALLOCATE, E, EDIT, HEWL, IEWL..., LINK, LINKEDIT, LOADER, LOGOFF, LOGON, SUBMIT, TEST"
verified_on: 2026-09-27
verified_platforms: ["MVS/CE 3.0.0 (mvsdev)"]
applies_to: [rexx370, brexx370, ufsd, ftpd, httpd, mvsmf]
tags: [linklist, lnklst, ieabld, resident-bldl, iea703i, abend106, program-fetch, compress, iebcopy, extent, ipl, cmdlib]
related: [MVS-SMP-0004, MVS-BLDL-0001]
---

## The claims

1. **A new extent in a link-list library is invisible until the next IPL.**
   Every module in it fails with `IEA703I 106-F`. The link list takes the
   library's extents at IPL. `[tested]`
2. **A compress in place keeps the extents and still breaks modules.** It moves
   members, and the modules named in the resident BLDL list
   (`SYS1.PARMLIB(IEABLDxx)`) are then fetched from their old place: `106-F`
   until the next IPL. `[tested]`
   Mechanism: MVS keeps those directory entries in storage from IPL on, so it
   never sees the new TTR. `[inferred]` It fits every observation: only the
   modules in `IEABLD00` failed, and EXEC, which is in the same library but not
   in the list, kept working.

## What claim 2 looked like

The compress (IEBCOPY `COPY INDD=LIB,OUTDD=LIB`, `DISP=SHR`) ended RC 0. It
copied all 291 members, 115 of them already in place. Extents 2 → 2. Batch tests
that use EXEC from the same library stayed green (JOB01365).

In the foreground, the console showed:

```
IEA703I 106- F IBMUSER  IKJACCNT MODULE ACCESSED ALLOC
IEC130I SYSEXEC  DD STATEMENT MISSING
IEA703I 106- F IBMUSER  IKJACCNT MODULE ACCESSED LOGON
IEA703I 106- F IBMUSER  IKJACCNT MODULE ACCESSED LOGOFF
```

- The logon CLIST's ALLOC failed, so SYSEXEC was never allocated. REXX execs were
  then silently not found: no message, only `READY`.
- `LOGON` and `LOGOFF` ended `DUE TO ERROR`, and `?` gave `SYSTEM ABEND CODE 106
  REASON CODE 00F`.
- A session that could not LOGOFF stayed `IN USE`, and `C U=` did not free it.

An IPL without CLPA cured all of it.

On MVSCE-LAB the resident list names SYS1.LINKLIB, but the TSO commands in it
(ALLOC, LOGON, LOGOFF, TEST, ...) live in SYS1.CMDLIB, and those are the ones that
broke.

## Consequences

- **Before writing into a link-list library** (SMP APPLY, IEBCOPY, `make deploy`
  of a load module there), check that it fits in the current extents: tracks
  free versus the size of the new member in tracks.
- **A compress of a link-list library needs an IPL right after it.** This holds
  even when nothing in the VTOC changes. Plan both together, and say so before
  starting.
- **`106-F` is not "module missing".** It means the module is fetched from a place
  the link list does not know. Read the `IEA703I` line: it names the module.
- **A back-up that reads every member** (IEBCOPY unload to a sequential data set)
  is also the cheap check that a library is intact after an aborted compress.
- **mvsMF reports the size of a data set in tracks** while labelling it
  `CYLINDERS`. SYS1.CMDLIB showed "120 CYLINDERS"; the VTOC has 4 cylinders =
  120 tracks. Use IEHLIST `LISTVTOC FORMAT` for the real figures.
