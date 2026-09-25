---
id: MVS-SMP-0005
title: RESTORE of an applied usermod clears the inventory, but CSECTs it added stay in the load module
status: tested
platform: [mvs38j]
sources:
  - "MVSCE-LAB (MVS/CE 3.0.0 under Hercules), SMP 4 level 04.48, 2026-09-25 — USERMOD ZMG0002 (++JCLIN adding IKJEFTRX to LMOD IKJEFT01 and IKJCT437 to LMOD EXEC, ++MOD for IKJEFT01 and IKJCT430), applied, not accepted"
  - "RESTORE CHECK JOB01301, RESTORE JOB01302, LMOD comparison after the RESTORE JOB01303/JOB01304"
  - "REJECT CHECK JOB01305 (HMA2033), REJECT JOB01306 (HMA2462), LIST CDS JOB01307"
  - "RECEIVE of the rebuilt SYSMOD under the same id JOB01310, APPLY JOB01312, byte comparison JOB01313"
verified_on: 2026-09-25
verified_platforms: ["MVS/CE 3.0.0 (mvsdev)"]
applies_to: [rexx370]
tags: [smp, smp4, restore, reject, usermod, jclin, lmod, csect, inventory, hma2462, hma2033]
related: [ECO-0007, MVS-SMP-0004]
---

## The claims

1. **RESTORE removes the SYSMOD from the inventory completely.** Its CDS entry,
   its MCS in `SMPPTS`, and the MOD entries of modules it *added* through
   `++JCLIN` are all gone. `[tested]`
2. **The CSECTs of those added modules stay in the load modules.** The RESTORE
   reports them `DELETED`, but that is an inventory statement only. `[tested]`
3. **REJECT is not needed after such a RESTORE, and SMP 4's REJECT has no
   CHECK.** `[tested]`

## The evidence

`ZMG0002` replaced `MOD(IKJEFT01)` and `MOD(IKJCT430)` and added `IKJEFTRX` and
`IKJCT437` to the existing LMODs `IKJEFT01` and `EXEC` by `++JCLIN`. The
RESTORE CHECK element summary (JOB01301):

```
MOD    IKJCT430  RESTORED  EBB1102  UY16532        EXEC      CMDLIB   ZMG0002  RESTORED
MOD    IKJCT437  DELETED                           EXEC      CMDLIB   ZMG0002  RESTORED
MOD    IKJEFTRX  DELETED                           IKJEFT01  LPALIB   ZMG0002  RESTORED
MOD    IKJEFT01  RESTORED  EBB1102  UY13431        IKJEFT01  LPALIB   ZMG0002  RESTORED
```

After the real RESTORE (JOB01302), AMBLIST of the load modules (JOB01303,
JOB01304):

```
EXEC      IKJCT430 1128  PARS AE  IKJCT431 1F90  IKJCT432 21B5  IKJCT435 CE3  IKJCT437 2A4
IKJEFT01  IKJEFT01 1BB8  IKJEFT06 6A0  IKJEFTRX 1D0  IKJEFTSC ED0
```

- `IKJCT430` and `IKJEFT01` are back at the DLIB level. IKJEFT01 is
  byte-identical to the IBM source (UY13431).
- `IKJCT437` and `IKJEFTRX` are **still there**, the old versions.
- The link-edit went against the target load module, as every APPLY does
  (`MVS-SMP-0004`), so it carried the added CSECTs along.
- The ORDER that the usermod's JCLIN had put into the LKED CONTROL is gone:
  `IKJCT430` now leads EXEC again.

A `LIST CDS` afterwards (JOB01307):

```
SYSMOD      ZMG0002       NOT FOUND
MODULE      IKJCT437      NOT FOUND
MODULE      IKJEFTRX      NOT FOUND
IKJCT430    RMID = UY16532
IKJEFT01    RMID = UY13431
```

and `SYS1.SMPPTS` holds no `ZMG0002` member.

REJECT after that (JOB01306):

```
HMA2462 ** SYSMOD ZMG0002 NOT FOUND ON SMPPTS LIBRARY
HMA2483 ** THE REJECT FUNCTION WAS REQUESTED - NO SYSMODS MEET SPECIFICATIONS   RC 12
```

`REJECT SELECT(ZMG0002) CHECK .` gets `HMA2033 ** SYNTAX ERROR IN CONTROL
STATEMENT AT COL 25`, which is the `CHECK` (JOB01305).

## Consequences

- **The inventory says "gone", the disk says "still there".** The leftovers are
  harmless while nothing calls them: the IBM code restored here never branches
  to `IKJEFTRX` or `IKJCT437`. They still count against the load module size,
  and an AMBLIST shows CSECTs no SMP entry accounts for.
- **To really take such a usermod out, restore the load modules from a backup
  taken before the APPLY.** RESTORE alone does not do it. For a product
  FUNCTION with its own single-module LMODs, see `ECO-0007`: there RESTORE
  deletes the module outright.
- **Reinstalling a rebuilt usermod under the same id works after RESTORE**,
  because the id is unknown again. RECEIVE (JOB01310) and APPLY (JOB01312) went
  through. The new decks are included first and replace the leftover CSECTs of
  the same name (first occurrence wins). The result was byte-identical to the
  same decks linked by hand (JOB01313).
- Only for an unpublished test id. Once a usermod id has left the building it
  is spent, like an FMID.
- A RECEIVE that fails with `HMA3980 SYNTAX OR CONSTRUCTION ERROR` names its
  cause in the line above. Here it was `HMA3482 … MORE THAN ONE ++VER`, after a
  text edit had duplicated the `++VER` block (JOB01308).
