---
id: MVS-SMP-0015
title: An upgrade through SMP ends APPLY RC 04 where SMP installed the deleted level and RC 00 where it did not — the return code is a property of the image, not of the upgrade
status: tested
platform: [mvs38j]
sources:
  - "TK5 and MVS/CE throwaway containers, 2026-10-22, SMP 4 — FTPD 1.3.0 (FMID TFTP130, deletes TFTP120), release candidate 6b6367d, installed from the candidate's artefacts following docs/installation.md; TK5 image with FTPD 1.2.0 installed through SMP (TFTP120 in the inventory): job FTPDINS, JOB00043; MVS/CE image with an FTPD 1.2.0 that SMP never saw: JOB00035; MVS/CE without the allocation job: JOB00034 (JCL ERROR); allocation job after the install had received the SYSMOD: JOB00036. Job numbers are container-local, the containers are gone"
  - "mvslovers/ftpd tag v1.3.0 (contains 6b6367d), docs/installation.md — the upgrade steps, 'One return code that looks wrong and is not', the MVS/CE note on MVSLOVER.FTPD.LOADLIB, the troubleshooting table"
  - "mvslovers/ftpd#285 and #287 (installation guide: upgrade steps on MVS/CE end in a JCL error; install job header says 'run the allocation job once')"
verified_on: 2026-10-22
verified_platforms: ["MVS/CE", "TK5"]
applies_to: [ftpd, ufsd, httpd, mbt]
tags: [smp, smp4, upgrade, apply, return-code, hma2461, hma3862, hma2380, jcl-error, allocation, tk5, mvsce, delete, ver]
related: [ECO-0007, MVS-SMP-0007, MVS-SMP-0008, MVS-SMP-0014]
---

## The claim

**The return code of an upgrade install job is not a pass/fail signal, and it is not the
same on two images for the same SYSMOD.** `[tested]` The same FTPD 1.3.0 install job
(RECEIVE, APPLYCHK, APPLY, ACCEPT) ended differently depending on whether SMP's inventory
knew the level that TFTP130 deletes:

| image | state before | APPLYCHK | APPLY | ACCEPT | `HMA2461` |
|---|---|---|---|---|---|
| TK5 | FTPD 1.2.0 installed through SMP (`TFTP120` in the inventory) | 0000 | **0004** | 0000 | yes |
| MVS/CE | FTPD 1.2.0 in the image, never seen by SMP | 0000 | **0000** | 0000 | no |

## TK5: the deleted level is in the inventory

```
FTPDINS    APPLYCHK  HMASMP    HMASMP    RC= 0000
FTPDINS    APPLY     HMASMP    HMASMP    RC= 0004
FTPDINS    ACCEPT    HMASMP    HMASMP    RC= 0000
HMA2380    COPY SUCCESSFUL - MOD=FTPD - LMOD=FTPD - LIBRARY=LINKLIB - SYSMOD=TFTP130 - RETURN CODE=00
HMA2270    APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTP130
HMA2461    SYSMOD TFTP120 NOT FOUND ON SMPSCDS LIBRARY
HMA2270    ACCEPT PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTP130
```

Job CC 0004. `HMA2461` is SMP saying that the deleted level has no backup entry in SMPSCDS to
keep; the install is complete. `LIST CDS/ACDS` shows FMID = RMID = `TFTP130` for MOD and LMOD
`FTPD`. `[tested]` This is the same message and the same RC 04 as in `MVS-SMP-0008`. The guide
of the product explains it the same way. `[source: ftpd docs/installation.md at v1.3.0]`

## MVS/CE: nothing named TFTP120 to delete

First install on MVS/CE (allocation job, then the same install job, JOB00035): every step
`CC 0000`, no `HMA2461`, `HMA2270` for APPLY and ACCEPT. `[tested]`

The reason given is that SMP never saw the image's FTPD 1.2.0. It runs from
`MVSLOVER.FTPD.LOADLIB`, not from an SMP install, so there is no `TFTP120` entry to remove or
to report as missing. `[source: ftpd docs/installation.md at v1.3.0, the MVS/CE note]` The
inventory of the measured MVS/CE container was not listed before the install, so the absence of
`TFTP120` there is the documented property of the image, not something this run read.

Consequence: on MVS/CE the started task keeps running the old module until the procedure is
replaced. The shipped procedure has to replace the image's member `FTPD` in `SYS2.PROCLIB`,
otherwise the task starts `MVSLOVER.FTPD.LOADLIB` (1.2.0). `[source: ftpd docs/installation.md
at v1.3.0, the MVS/CE note on SYS2.PROCLIB]` The inbox note states it as measured; the banner
check afterwards is what catches it.

## Allocation and ordering traps (MVS/CE)

- **No allocation job:** the install job ends `JCL ERROR`,
  `IEF212I FTPDINS HMASMP APPLYCHK LINKLIB - DATA SET NOT FOUND` (JOB00034). `[tested]` The
  libraries `FTPD.LINKLIB` and `FTPD.AFTPDLOD` do not exist on an MVS/CE image, because its FTPD
  was never installed through SMP. The `RECEIVE` steps have already run by the time the JCL
  error is raised (ftpd#285). `[source]`
- **Allocation job after that:** the next install job ends CC 0008 with
  `HMA3862 ** SYSMOD TFTP130 ALREADY RECEIVED`, and APPLYCHK does not run (JOB00036); APPLY and
  ACCEPT end 0000. `[tested]` So the order on MVS/CE is allocation job first, install job
  second.
- **On TK5 with an SMP-installed 1.2.0 the allocation job is skipped,** because it allocates the
  libraries `NEW` and they exist. The two images need opposite instructions; the header of the
  shipped install job said "run the allocation job once" for both (ftpd#287). `[source]`

## What to read instead of the return code

After an upgrade read three things, in this order (`MVS-SMP-0007`):

1. `HMA2380 COPY SUCCESSFUL` for `MOD=FTPD` in the APPLY output.
2. The `LIST` stanza for the MOD and LMOD (FMID and RMID name the new level).
3. The banner of the started task (`F FTPD,VERSION`: `FTPD016I FTPD 1.3.0 (6B6367D)`).

The first two say what SMP did. Only the banner says what is running; a stale input (the fourth
case in `MVS-SMP-0007`) passes the first two.

## What was not established

- The same sequence on a real system with years of SMP history (old FMIDs, tombstones).
- Whether MVS/CE images other than the one used carry an SMP-known FTPD.
- The RC 04 / RC 00 split was measured on the release candidate (builds rc2 and rc3 of
  `6b6367d`, identical in content), not on the tagged release artefacts.
