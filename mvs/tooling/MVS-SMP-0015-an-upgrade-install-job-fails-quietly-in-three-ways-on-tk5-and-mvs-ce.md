---
id: MVS-SMP-0015
title: The install job of an upgrade (FTPD 1.2.0 to 1.3.0) on TK5 and MVS/CE — three traps where the return codes mislead
status: tested
platform: [mvs38j]
sources:
  - "QA acceptance run of FTPD 1.3.0 (FMID TFTP130, deletes TFTP120), release candidate 6b6367d (rc2 and rc3 builds of the same commit), installed through SMP from the candidate's artefacts following ftpd docs/installation.md (Paperclip MVS-20, ftpd#283 to #287); fresh throwaway containers 2026-10-22 on TK5 (image with FTPD 1.2.0 / TFTP120 SMP-installed) and MVS/CE (image with an FTPD 1.2.0 that SMP never saw); job numbers restart in every container and belong to their run only"
  - "ftpd docs/installation.md at origin/main 5afc39a: the MVS/CE passage on the member FTPD in SYS2.PROCLIB (STEPLIB MVSLOVER.FTPD.LOADLIB of the image's 1.2.0)"
verified_on: 2026-10-22
verified_platforms: ["TK5 (image with SMP-installed FTPD 1.2.0)", "MVS/CE 3.0.0 (image FTPD 1.2.0 outside SMP)"]
applies_to: [ftpd, ufsd, httpd, mvsmf, mbt]
tags: [smp, smp4, upgrade, apply, hma2461, hma3862, hma2380, allocation, xmit, stale, tk5, mvs-ce, ftpd, return-code]
related: [ECO-0007, MVS-SMP-0002, MVS-SMP-0008, MVS-SMP-0014, MVS-DASD-0003]
---

## The claims

1. **The APPLY return code of an upgrade depends on what SMP has seen, not on whether the install worked.**
   `[tested]`
   - TK5, where SMP installed 1.2.0 (TFTP120): APPLYCHK 0000, **APPLY 0004**, ACCEPT 0000, job CC 0004, with
     `HMA2461 SYSMOD TFTP120 NOT FOUND ON SMPSCDS LIBRARY` after `HMA2270`. The install is complete;
     `LIST CDS/ACDS` shows FMID = RMID = `TFTP130` for MOD and LMOD `FTPD`.
   - MVS/CE, where the image's FTPD 1.2.0 runs from `MVSLOVER.FTPD.LOADLIB` and SMP never saw it: every step
     0000, no `HMA2461`. There is nothing named TFTP120 to delete or to miss.
   Both are right. This is `MVS-SMP-0008` point 4 and 5 seen on two distributions with the same product. Read
   the install, not the code: `HMA2380 COPY SUCCESSFUL - MOD=FTPD - LMOD=FTPD - LIBRARY=LINKLIB -
   SYSMOD=TFTP130`, the `LIST` stanza, and the banner of the started task (`F FTPD,VERSION` printed
   `FTPD016I FTPD 1.3.0 (6B6367D)`).
2. **The libraries must exist before the install job runs, and the allocation job comes first.** `[tested]`
   - MVS/CE without the allocation job: `JCL ERROR`, `IEF212I FTPDINS HMASMP APPLYCHK LINKLIB - DATA SET NOT
     FOUND`.
   - The allocation job run after the install has already received the SYSMOD: the install job ends CC 0008
     with `HMA3862 ** SYSMOD TFTP130 ALREADY RECEIVED` and APPLYCHK does not run; APPLY and ACCEPT still end
     0000 (`MVS-SMP-0002`).
3. **A stale XMIT data set gives a clean install of the old module.** On TK5 the image carries
   `HERC01.FTPD.LOAD.XMIT` and `HERC01.FTPD.SAMP.XMIT` of FTPD 1.2.0. If the upload of the new XMIT files
   fails, or goes to other data set names, and the install job still points at those names, RECEIVE succeeds
   and SMP reports TFTP130, but the installed module is the old one: the SMP output showed `Receiving
   'FTPD.V1R2M0.LINKLIB'` and the started task printed `FTPD 1.2.0`. All return codes were clean. Delete the
   old data sets before the upload and read the banner afterwards. `[tested]`

## The evidence

TK5, job `FTPDINS` (TFTP120 in the SMP inventory), run of 2026-10-22:

```
FTPDINS    APPLYCHK  HMASMP    HMASMP    RC= 0000
FTPDINS    APPLY     HMASMP    HMASMP    RC= 0004
FTPDINS    ACCEPT    HMASMP    HMASMP    RC= 0000
HMA2380    COPY SUCCESSFUL - MOD=FTPD - LMOD=FTPD - LIBRARY=LINKLIB - SYSMOD=TFTP130 - RETURN CODE=00
HMA2270    APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTP130
HMA2461    SYSMOD TFTP120 NOT FOUND ON SMPSCDS LIBRARY
HMA2270    ACCEPT PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTP130
```

`HMA2461` comes after `HMA2270`: SMP reports that the deleted level has no backup entry in SMPSCDS to keep.

## MVS/CE specifics seen in the same run

- The shipped procedure has to replace the image's member `FTPD` in `SYS2.PROCLIB`; otherwise the started
  task keeps running `MVSLOVER.FTPD.LOADLIB` (1.2.0). `[tested]` `[source: ftpd docs/installation.md]`
- `SYS2.PARMLIB` has room, so the default `D='SYS2.PARMLIB'` of the shipped procedure works there without a
  change. On TK5 `SYS1.PARMLIB` is full (`MVS-DASD-0003`).

## Limits

- The upgrade return codes were seen on both the rc2 and the rc3 build of the same commit; the rc3 files are
  identical in content to rc2.
- Not measured: the same sequence on a real stand with years of SMP history (old FMIDs, tombstones).

Container results, not stand results.
