# 2026-10-21 — SMP4: RESTORE and REJECT of a FUNCTION fail after ACCEPT; UCLIN is the way out

Source: QA acceptance run of UFSD 1.5.0 (FMID TUFS150, deletes TUFS140), installed
through SMP from the release artifacts following the installation guide.
Measured in a fresh, throwaway TK5 container (TK5 Update 5, SMP4, UFSD 1.4.0 / TUFS140
SMP-installed in the image). Container result, not a stand result. The container is gone.

Platform: mvs38j (TK5).

## Finding

Once the install job has run ACCEPT for a FUNCTION SYSMOD, both documented ways back are
closed. The inventory (CDS and ACDS) can only be edited with UCLIN.

State before the test: TUFS150 freshly installed (RECEIVE, APPLY, ACCEPT; all steps RC 00),
`UFSD000I` / `UFSD001I READY` after start. The libraries, CDS and ACDS all held TUFS150.

### RESTORE and REJECT

Job (JOB00059), two SMP steps, the second with `COND=EVEN`:

```
//UFSDRR   JOB (SYS),'UFSD RR',CLASS=A,MSGCLASS=H
//RES     EXEC SMPAPP
//SMPCNTL  DD *
 RESTORE S(TUFS150) .
/*
//REJ     EXEC SMPAPP,COND=EVEN
//SMPCNTL  DD *
 REJECT S(TUFS150) .
/*
```

Result: both steps RC 12, job CC 0012.

```
HMA2452 ** SYSMOD TUFS150 SELECTED FOR RESTORE HAS BEEN ACCEPTED
HMA3703 ** RESTORE PROCESSING TERMINATED BECAUSE FUNCTION SYSMOD TUFS150 FAILED
HMA2050 RESTORE PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12
HMA2462 ** SYSMOD TUFS150 NOT FOUND ON SMPPTS LIBRARY
HMA2260 REJECT PROCESSING TERMINATED FOR SYSMOD TUFS150
HMA2050 REJECT PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12
```

Note the wording of HMA2462: REJECT says "NOT FOUND ON SMPPTS", not "already accepted".
Reading: ACCEPT drops the SYSMOD's MCS from SMPPTS, and REJECT works from that member. `[inferred]`
(the SMPPTS member was not listed before and after ACCEPT).

### UCLIN, the only way out

Job UFSDUCL (JOB00053), three steps, run against the system that held TUFS150 and the
marks of the earlier releases: `UCLIN CDS` (step UCLCDS), `UCLIN ACDS` (UCLACDS), then
`RESETRC` plus ten `LIST` stanzas (LIST). Statements, per zone (the ACDS step has the same
list without the `LMOD` lines):

```
 UCLIN CDS .
  DEL SYSMOD(TUFS150) MOD(UFSD) .            (also UFSDSSIR, UFSDCLNP, UFSFMT)
  DEL MOD(UFSD) .                            (also UFSDSSIR, UFSDCLNP, UFSFMT)
  DEL LMOD(UFSD) .                           (also UFSDSSIR, UFSDCLNP, UFSFMT)
  DEL SYSMOD(TUFS150) .
  DEL SYSMOD(TUFS140) .
  DEL SYSMOD(TUFS130) .
  DEL SYSMOD(TUFS120) .
  DEL SYSMOD(TUFS110) .
 ENDUCL .
```

Result: UCLCDS RC 08, UCLACDS RC 08, LIST RC 04, job CC 0008. All five ids are named
because every upgrade leaves the id of its predecessor behind as a `DELBY` mark; an id that
was never on the system is reported and raises the step to RC 08, with the following
statements still processed:

```
HMA2532 ** SYSMOD ENTRY TUFS120 TO BE DELETED DOES NOT EXIST     (2x, one per zone)
HMA2532 ** SYSMOD ENTRY TUFS110 TO BE DELETED DOES NOT EXIST     (2x)
HMA2550    UPDATE COMPLETE FOR TUFS150 (10x), TUFS140 (2x), TUFS130 (2x),
           and for each of UFSD, UFSDSSIR, UFSDCLNP, UFSFMT (3x)
HMA2050    UCLIN PROCESSING COMPLETED - HIGHEST RETURN CODE IS 08   (2x)
HMA2050    LIST PROCESSING COMPLETED - HIGHEST RETURN CODE IS 04    (LIST step)
```

All ten `LIST` stanzas (five ids x CDS and ACDS) answer "NOT FOUND OR WERE NOT ELIGIBLE":
the FMID is gone from the inventory and can be received again. UCLIN touches no library;
the data sets were deleted by hand (IDCAMS) afterwards, then `alloc` and `inst` ran again
with all steps RC 00 (`HMA2380` 4x per zone, `TUFS140 DELETED` as for any install).

The job text is chapter 7 of the UFSD User's Guide (ML05-0001), step 2; it was submitted
as printed in the book.

## What RESTORE is still for

Not measured in this run `[assumed]`. RESTORE takes applied SYSMODs out of the target zone
by copying the distribution-library copies back. That works for service (PTFs) that is
APPLYed but not yet ACCEPTed, and brings a target library back to the accepted FUNCTION
level. This is why the mbt install job accepts the FMID itself: the accepted FUNCTION is the
baseline that later PTFs can be restored to. It does not work for the FUNCTION that was
accepted.

## Consequence for texts and templates

- Any text that says "if you must start over, reject the SYSMOD first" or "the way back is
  an SMP RESTORE" is wrong for a FUNCTION that the same job accepted (HMA2462 / HMA3703,
  RC 12). It was found in a job-template header and in an install guide; both are being
  corrected.
- The way back is UCLIN on CDS and ACDS (inventory), then delete the libraries by hand.
  There is no SMP way back to the previous release; an upgrade deletes its predecessor.

## Notes for the ingest

- Overlap: ECO-0007 (the same two messages for TFTP100) and MVS-SMP-0005 (HMA2462 for
  ZMG0002). New here: the second FMID/product, the exact UCLIN set with its expected
  HMA2532/RC 08 behaviour, and the reading of HMA2462. Decide whether it extends those or
  stands as its own document.
- Status: the messages and return codes are `tested` (TK5 Update 5, SMP4, one container,
  one run). The SMPPTS explanation is `inferred`; the RESTORE-for-PTFs paragraph is
  `assumed`.
