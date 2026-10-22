---
id: MVS-SMP-0013
title: After ACCEPT of a FUNCTION both RESTORE and REJECT fail (HMA2452, HMA2462) — PURGE=YES in the SMPPTS SYSTEM entry is the probable cause, and UCLIN is the only route measured
status: tested
platform: [mvs38j]
sources:
  - "TK5 Update 5 throwaway container, SMP 4 HMASMP LVL 04.48, 2026-10-21 (as reported in the inbox note; job numbers container-local) — UFSD 1.5.0 (TUFS150, deletes TUFS140) installed through SMP, then RESTORE and REJECT in one job JOB00059 (both steps RC 12)"
  - "MVS/CE and TK5 throwaway containers, 2026-10-21 — LIST PTS . showing the SYSTEM entry with PURGE=YES; RESTORE and REJECT after ACCEPT of TUFS150 on both; seven failed UCLIN PTS REP variants (HMA2032)"
  - "MVS/CE system, 2026-08-14 — TFTP100 removal, the earlier measurement of the same two messages; see ECO-0007"
  - "ufsd docs/uninstall.md at commit 6804ee7"
verified_on: 2026-10-21
verified_platforms: ["MVS/CE (3.0.0)", "TK5 Update 5"]
applies_to: [ufsd, ftpd, httpd, mbt]
tags: [smp, smp4, restore, reject, accept, purge, smppts, hma2452, hma2462, hma3703, hma2032, hma2033, uclin, function]
related: [ECO-0007, MVS-SMP-0002, MVS-SMP-0005, MVS-SMP-0009, MVS-SMP-0014]
---

## The claims

1. **Once ACCEPT has run for a FUNCTION SYSMOD, `RESTORE` and `REJECT` both end
   RC 12 and neither undoes anything.** Measured on a second product (UFSD) on
   both distributions, after TFTP100 in `ECO-0007`. `[tested]`
2. **The `SMPPTS` SYSTEM entry carries `PURGE=YES`.** Shown on both
   distributions. `[tested]`
3. **`PURGE=YES` is why `REJECT` cannot find the accepted SYSMOD.** `[inferred]`
   The link between the option and `HMA2462` is the documented meaning of the
   option plus the output below. It was **not** shown that `PURGE=NO` lets a
   `REJECT` succeed after an ACCEPT.
4. **The inventory edit that works is `UCLIN` on both zones**, but no other
   route was tried successfully either, so "only way" is a statement about what
   was demonstrated. `[tested]`

## The output

Both steps in one job (TK5 container, JOB00059; the second step `COND=EVEN`):

```
RESTORE S(TUFS150) .
HMA2452 ** SYSMOD TUFS150 SELECTED FOR RESTORE HAS BEEN ACCEPTED
HMA3703 ** RESTORE PROCESSING TERMINATED BECAUSE FUNCTION SYSMOD TUFS150 FAILED
HMA2050 RESTORE PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12

REJECT S(TUFS150) .
HMA2462 ** SYSMOD TUFS150 NOT FOUND ON SMPPTS LIBRARY
HMA2260 REJECT PROCESSING TERMINATED FOR SYSMOD TUFS150
HMA2050 REJECT PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12
```

Identical on an MVS/CE container. The wording of `HMA2462` is "not found on
SMPPTS", not "already accepted": RESTORE refuses because the SYSMOD is accepted,
REJECT because it cannot find an MCS.

## The setting

`LIST PTS .` shows the SYSTEM entry of the PTS (`LIST SYSTEM .` and `LIST PTS
SYSTEM .` are rejected with `HMA2033`). On both distributions:

```
SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=YES
```

Reading `[inferred]`: `PURGE=YES` makes ACCEPT remove the accepted SYSMOD from
the PTS, so `REJECT` has nothing to work from. This refines the earlier reading
in `ECO-0007` ("the ACCEPT removes the MCS from `SYS1.SMPPTS`"): that part was
verified there directly (the PTS held 3091 members and the TFTP100 MCS was not
one of them); the setting behind it is new.

Not established: how to change the option. `UCLIN PTS .` followed by `REP
SYSTEM`, `REP SYS` or `REP OPTIONS`, with `OPTIONS(PURGE=NO)` or `PURGE(NO)`,
ended `HMA2032 ** SYNTAX ERROR IN UCL STATEMENT` (RC 08) on the REP statement in
seven variants. The right syntax is unknown, so the `PURGE=NO` case is
unmeasured.

## What this does to the guidance

- **"Reject the SYSMOD first" and "the way back is an SMP RESTORE" are wrong for
  a FUNCTION the same job accepted.** The mbt install job accepts the FMID
  itself, so this applies to every shipped package that uses it. ufsd's guide
  records that the removal text of its 1.2.0 archive (`RESTORE`, then `REJECT`)
  was wrong for that reason. `[source: ufsd docs/uninstall.md, 6804ee7]`
- **The way back is `UCLIN` on CDS and ACDS** (inventory) and then deleting the
  libraries by hand; the sequence and its error behaviour are in `MVS-SMP-0009`.
  There is no SMP way back to the previous release: an upgrade deletes its
  predecessor (`MVS-SMP-0008`).
- **A usermod that was only applied behaves differently**: `RESTORE` clears the
  inventory (`MVS-SMP-0005`), and the later `REJECT` fails with the same
  `HMA2462` because RESTORE took the MCS away. That is consistent with the reading
  above that `HMA2462` means "no MCS", whatever removed it.
- **A removal that goes through a dummy function** instead of UCLIN works for the
  libraries and the MOD/LMOD entries, but still needs UCLIN to free the ids
  (`MVS-SMP-0014`).

## What RESTORE is still for `[assumed]`

Not measured here. `RESTORE` takes applied SYSMODs out of the target zone by
copying the distribution-library copies back. That should work for service (PTFs)
that is applied but not yet accepted, and bring a target library back to the
accepted FUNCTION level. It is the reason the install job accepts the FMID:
the accepted FUNCTION is the baseline later PTFs can be restored to. It does not
work for the FUNCTION that was accepted.

## Limits

- Throwaway containers, one product, one run per distribution.
- `PURGE=NO` was never set; `REJECT` after ACCEPT under that setting is unmeasured.
- The SMPPTS member list was not taken before and after the ACCEPT in this run.
