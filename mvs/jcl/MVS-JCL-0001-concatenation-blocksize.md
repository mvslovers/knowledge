---
id: MVS-JCL-0001
title: A concatenation takes its DCB from the first dataset — a later library with larger blocks gives WRNG.LEN.RECORD
status: tested
platform: [mvs38j]
sources:
  - "Observed on MVSTK5-BLD (TK5 under Hercules 4.10.0), 2026-09-10: BLDSTG1A/JOB00325, six steps CC 0020"
  - "IBM OS/VS2 MVS JCL, unlike-attribute concatenation"
verified_on: 2026-09-10
applies_to: [mvs38src]
tags: [jcl, dcb, blksize, concatenation, syslib, bsam, ifo261, wrng-len-record, assembler, ifox00, sysgen]
related: [MVS-DASD-0001]
---

## The rule

**A concatenated DD gets its DCB from the FIRST dataset in the concatenation.**
Every dataset behind it is read into buffers of that size. A later dataset whose
blocks are larger than the first one's `BLKSIZE` cannot be read: BSAM reports a
wrong-length record and the access method calls it a permanent I/O error.
`[tested]`

It is not a media error, nothing is damaged, and the same libraries read
perfectly in any other order.

## What it looks like

Under the assembler, on a `SYSLIB` concatenation:

```
IFO266  LAST ASSEMBLER PHASE LOADED WAS IFOX11
IFO261  ASSEMBLY TERMINATED -- PERM I/O ERROR  BLDSTG1A,A,390,DA,SYSLIB
IFO261       READ, WRNG.LEN.RECORD, 00000040000300, BSAM
IEF142I BLDSTG1A A SG5 - STEP WAS EXECUTED - COND CODE 0020
```

Two details make it hard to read:

* **The unit number in the message is not the one in `IEF237I`.** Allocation
  reports the *first* dataset's device (`IEF237I 392 ALLOCATED TO SYSLIB`); the
  error names the device the oversized block actually sits on (`390`). Reading
  those as the same device sends you looking at the wrong volume.
* **`CC 0020` from the assembler looks like a source problem and is not one.**
  The assembly never reached the point of issuing a severity. In a listing that
  concatenates many assemblies, every `HIGHEST SEVERITY WAS` line can read `0`
  while steps are failing — the failing ones printed no such line at all.

## Diagnosing it

The whole question is one comparison. For each dataset in the concatenation, in
order, take `BLKSIZE`; if any later one exceeds the first, that is the bug:

```
SYS1.AMODGEN   BLKSIZE 19040   <- first, sets the buffers
SYS1.MACLIB    BLKSIZE 27920   <- does not fit
```

On MVS 3.8j `BLKSIZE` is per dataset and visible in the VTOC, so this is
answerable without running anything. Across the 274 members of one build's JCL
library, checking every `SYSLIB` concatenation this way found exactly one
defect — every other concatenation put the largest first or used libraries of
equal blocksize.

## Fixing it

Two repairs, and they are not equivalent:

| fix | effect |
|---|---|
| `DCB=BLKSIZE=<largest>` on the first DD | buffers grow; **search order unchanged** |
| reorder so the largest comes first | buffers grow; **search order changes** |

**Prefer the `BLKSIZE` override.** Reordering a macro library concatenation
changes which copy of a duplicated macro wins, and that silently changes the
object code — the failure mode is a wrong assembly rather than a stopped one,
which is worse. Only reorder when nothing in the concatenation is duplicated,
and check rather than assume.

## The trap behind the trap

A build chain may assemble the same modules more than once. Here the six modules
lost in `$08STG1A` (step 7 of 260) are re-assembled by `ZSTAGE2` (step 239) from
`MVSSRC.BLD.AMODGEN` and `MVSSRC.BLD.MACLIB`, both at 27,920 — so the chain
repairs itself and the defect never surfaces as a missing object at the end.

That is why it survived several full runs unnoticed, and it is the reason to
check the return code of every step rather than only the state of the output at
the end. **A defect that a later step covers up is still a defect**, and the
next chain that does not happen to include the covering step will fail on it.

## Confirming a member really is absent

`MVSSRC.BLD.OBJPDS01(IEFEDTTB)` returned zero bytes over the REST API after the
failure. Zero bytes is ambiguous on this stack — see `PM-2026-003`, where a read
error also produced an empty body with HTTP 200. The check that settles it is
the status code plus a control read in the same batch:

```
OBJPDS01(IEFEDTTB)   HTTP 404,  65 bytes   <- genuinely not there
OBJPDS01(IEFWMAS1)   HTTP 200, 720 bytes   <- reader is working
```
