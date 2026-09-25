---
id: MVS-SMP-0004
title: APPLY of a ++MOD re-links the installed target load module, not the DLIB — whatever is in the target survives
status: tested
platform: [mvs38j]
sources:
  - "MVSCE-LAB (MVS/CE 3.0.0 under Hercules), SMP 4 level 04.48, 2026-09-25 — APPLY SELECT(UY43678,UZ42826) JOB01231, LKDPRINT; AMBLIST of the four LMODs JOB01232"
  - "Same system — ACCEPT SELECT(UY43678,UZ42826,UY16532) JOB01234, LKDPRINT; AMBLIST of SYS1.AOST4 JOB01235"
  - "SMPCDS LMOD entries IKJEFT01, IKJEFT02, IKJEFT04, IKJEFT07 (LIST CDS LMOD, JOB01219/JOB01226)"
  - "Same system — USERMOD ZMG0002 (++JCLIN + 4 ++MOD), APPLY JOB01261 LKDPRINT; LIST CDS and AMBLIST compare JOB01262"
verified_on: 2026-09-25
verified_platforms: ["MVS/CE 3.0.0 (mvsdev)"]
applies_to: [rexx370, mvs38src]
tags: [smp, smp4, apply, accept, link-edit, lmod, jclin, target-library, dlib, usermod, iewl]
related: [ECO-0007, MVS-SMP-0001, MVS-SMP-0002, MVS-SMP-0003, MVS-SMP-0005]
---

## The claim

**When APPLY replaces a module that is link-edited into a load module, SMP 4
link-edits the new element into the load module as it currently sits in the
target library.** It does not rebuild the load module from the distribution
library. `[tested]`

So every other CSECT in that load module (applied-but-not-accepted PTFs,
usermods, and anything put there by hand) is carried forward unchanged.

## The evidence

`UZ42826` replaces `MOD(IKJEFT06)`, which the CDS lists in four LMODs
(`IKJEFT01`, `IKJEFT02`, `IKJEFT04`, `IKJEFT07`, all `SYSTEM LIBRARY =
LPALIB`). The LKDPRINT of the APPLY, for `IKJEFT01`:

```
IEW0000        ORDER IKJEFT01(P)
IEW0000        ORDER IKJEFT06
IEW0000        ALIAS IKJEFT0A
IEW0000        ENTRY IKJEFT01
IEW0000        SETCODE AC(1)
IEW0000     INCLUDE SMPWRK3(IKJEFTSC)              UY43678
IEW0000        IDENTIFY   IKJEFTSC('UY43678')
IEW0000     INCLUDE SMPWRK3(IKJEFT06)              UZ42826
IEW0000        IDENTIFY   IKJEFT06('UZ42826')
IEW0000     INCLUDE LPALIB(IKJEFT01)
IEW0000     NAME IKJEFT01(R)
```

The same shape for the other three, each ending `INCLUDE LPALIB(<lmod>)` /
`NAME <lmod>(R)`, followed by one line per LMOD:

```
HMA2390    LINK SUCCESSFUL - MOD=IKJEFT06 - LMOD=IKJEFT02 - LIBRARY=LPALIB - SYSMOD=UZ42826 - RETURN CODE=00
```

What the listing shows:

- **The control statements are the CDS `LKED CONTROL` of the LMOD entry,
  verbatim**: `ORDER`, `ALIAS`, `ENTRY`, `SETCODE`.
- **New elements come first** from `SMPWRK3`, and each gets an `IDENTIFY`
  with the SYSMOD id. After the link the IDR carries it.
- **The rest comes from `INCLUDE <target ddname>(<lmod>)`**, the installed
  load module. There is no `REPLACE` statement. The old copy of a replaced
  CSECT drops out because the linkage editor keeps the first occurrence of a
  CSECT name.
- No `INCLUDE` of the DLIB (`AOST4`) appears anywhere in the APPLY.

The disk after the APPLY (AMBLIST, JOB01232): `IKJEFTSC` in `IKJEFT01` went
from `86104 UZ82014` (0xE78) to `89300 UY43678` (0xED0). `IKJEFT06` in all
four LMODs now carries the APAR OZ88816 text change (`IKJ56644I … NO
VALID/TSO USERID` became `NO VALID TSO USERID`).

## ACCEPT is different

ACCEPT links each element **alone** into its own DLIB member. There is no
`INCLUDE` of an old copy:

```
IEW0000     INCLUDE SMPWRK3(IKJCT430)              UY16532
IEW0000        IDENTIFY   PARS('UY16532'),
IEW0000                   IKJCT430('UY16532')
IEW0000     NAME IKJCT430(R)
HMA2391    LINK SUCCESSFUL - MOD=IKJCT430 - LMOD=IKJCT430 - LIBRARY=AOST4 - SYSMOD=UY16532 - RETURN CODE=04
```

The RC 04 is `IEW0461` (NCAL, unresolved external references such as
`IKJCT435` from `IKJCT431`). That is expected for a single module in a DLIB
and not an error.

## Consequences

- **A usermod that ships only object decks for a few CSECTs keeps everything
  else in the load module.** Rebuilding the whole load module from source is
  unnecessary, and wrong wherever the target carries service the source does
  not have. `[tested]` for PTFs. For a `++USERMOD` the path is assumed to be
  the same, because APPLY processing does not distinguish SYSMOD types for
  link-edit. `[inferred]`
- **The target load module must be what the inventory says before an APPLY.**
  A module replaced by hand (IEBCOPY, a manual link-edit) is carried forward
  into the SMP-built result, with an IDR that claims SMP made it. On
  MVSCE-LAB the hand-built `IKJEFT01` was therefore relinked from `AOST4`
  first (JOB01229), before the APPLY. `[inferred]` The mechanism above
  predicts it. The hand-built module was never actually put through an APPLY.
- **A target library restored from an older volume keeps its old contents**
  while the CDS keeps the newer RMIDs, and the next APPLY builds on the old
  contents. The inventory will not show this. Check the disk (eyecatcher,
  IDR, AMBLIST) before trusting an RMID. See `MVS-SMP-0003`.
- **Re-APPLY re-links through the same path** (`MVS-SMP-0001`: not refused,
  RC 0000). It needs the SYSMOD's MCS in `SMPPTS`, which an ACCEPT deletes
  (`MVS-SMP-0002`).

## New modules added by ++JCLIN go the same way

A `++USERMOD` that brings **new** modules into existing LMODs through
`++JCLIN` (and replaces existing ones with `++MOD`) is link-edited the same
way. `[tested]` MVSCE-LAB 2026-09-25, `ZMG0002`, APPLY JOB01261:

```
HMA4180    INLINE JCLIN PROCESSING SUCCESSFUL FOR SYSMOD=ZMG0002
IEW0000     INCLUDE SMPWRK3(IKJEFT01)              ZMG0002
IEW0000     INCLUDE SMPWRK3(IKJEFTRX)              ZMG0002
IEW0000     INCLUDE LPALIB(IKJEFT01)
IEW0000     NAME IKJEFT01(R)
IEW0000     INCLUDE SMPWRK3(IKJCT430)              ZMG0002
IEW0000     INCLUDE SMPWRK3(IKJCT437)              ZMG0002
IEW0000     INCLUDE CMDLIB(EXEC)
IEW0000     NAME EXEC(R)
```

The JCLIN's own `INCLUDE AOST4(…)` list is **not** what APPLY executes. It
only records the LMOD structure. The `ORDER`, `ALIAS`, `ENTRY` and `SETCODE`
statements it carries **replace** the LMOD's `LKED CONTROL` in the CDS, so a
JCLIN must restate the complete existing control and add to it. Anything it
leaves out is lost from the next link. The SMP-built modules were
byte-identical to the same decks linked by hand in the same order (JOB01262).
The element ownership wall (`NOT SEL`) did not apply: the usermod's
`++VER` names the owning FMID `EBB1102`.
