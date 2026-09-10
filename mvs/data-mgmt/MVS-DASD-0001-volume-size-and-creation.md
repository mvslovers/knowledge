---
id: MVS-DASD-0001
title: DASD volume size limit and volume creation under Hercules — 32,767 tracks, and dasdinit alone is not enough
status: tested
platform: [mvs38j]
sources:
  - "Jay Moseley, 'Modern DASD' — https://www.jaymoseley.com/hercules/installMVS/modernDASD/modernDASD.htm"
  - "Jay Moseley, 'Adding DASD Volumes' — https://www.jaymoseley.com/hercules/installMVS/addingDasdV8.htm"
  - "Observed on MVSTK5-BLD (TK5 under Hercules 4.10.0), 2026-09-10: IEF193I on a 3390-3, successful allocation on a dasdload 3390-2, no VSAM object on any build volume"
verified_on: 2026-09-10
applies_to: [mvs38src, mvsmf]
tags: [dasd, volume, vtoc, dscb, dasdinit, dasdload, ickdsf, 3390, 3380, vsam, catalog, track-address, hercules, geometry, space]
related: [PM-2026-003, MVS-JCL-0001]
---

## The limit

**MVS 3.8j holds a track address in a signed halfword. A volume must not exceed
32,767 tracks.** `[source: Jay Moseley, Modern DASD]`

> "MVS 3.8j will almost certainly have difficulty with any DASD image where the
> total number of tracks (data cylinder count multiplied by the tracks per
> cylinder count) exceeds 32,767"

Tracks, not cylinders, and not bytes. For a 3390 (15 tracks/cylinder):

| model | cylinders | tracks | usable |
|---|--:|--:|---|
| 3390-1 | 1,113 | 16,695 | **yes** — the safe default |
| 3390-2, custom | 2,184 | 32,760 | **yes, with caveats** — seven tracks under the ceiling |
| 3390-3 | 3,339 | 50,085 | **no** |
| 3390-9 | 10,017 | 150,255 | no |

**A 3390-3 is rejected.** Not with a clear message — every allocation on it ends

```
IEF193I <job> <step> <ddname> - SPACE NOT OBTAINED BECAUSE OF PERMANENT I/O ERROR
```

which reads like a broken image rather than an unsupported geometry. `[tested]`

## What an oversized volume can and cannot hold

Staying under 32,767 tracks is necessary but not sufficient. A volume larger
than 3390-1 needs the Morrison/Prins User Modification, and even with it only
some dataset types work. Jay measured each type on a 2,184-cylinder 3390-2
`[source: Jay Moseley, Modern DASD]`:

| Dataset type | Result |
|---|---|
| Physical sequential | works |
| Partitioned | works |
| VSAM Dataspace | works |
| VSAM object, `UNIQUE` or suballocated from a Dataspace | works |
| **VSAM User Catalog** | **MVS locks up completely, re-IPL required** |

The catalog case is not a rejected allocation. The job starts, and the system
stops — no message, no abend, nothing to diagnose. The same happened on a
3380-3, and even a standard 3380-2 failed; 3390-1, 3380-1 and 3375 were fine.

Nothing you can do to a running MVS makes this recoverable, so the rule is
preventive: **never define a VSAM catalog on a volume larger than 3390-1.**

On MVSTK5-BLD the twelve 2,184-cylinder 3390-2 build volumes carry 199
partitioned, 6 sequential and 8 unopened FB datasets and no VSAM object at all
`[tested]`. Dave's SMP chain defines VSAM exactly once — `ZSTAGE1O` puts a
Dataspace and the cluster `SYS1.STGINDEX` on `MVSRES`, a standard 3390-1 — so
the build never touches the failing case.

## Creating a volume MVS will accept

Two routes, and the obvious one does not work on its own.

### `dasdinit` alone is not enough

```
dasdinit -a -z BLDSR2.196 3390-1 BLDSR2
```

produces the right geometry — and MVS refuses to allocate on it, with the same
`IEF193I` as above. `dasdls` on such an image ends `rc=1` where a usable volume
ends `rc=0`; that difference is the quickest offline check. `[tested]`

`-a` (alternate cylinders) is required — Jay: "MVS utilities expect them" — and
it is not sufficient. A `dasdinit` image must still be initialised **under MVS**
by ICKDSF.

### ICKDSF: which one, and the two traps

| release | initialises | on TK5 |
|---|---|---|
| **6** (base `ICKDSF`) | 2314, 3330, 3340, 3350 | `SYS1.LINKLIB(ICKDSF)` |
| **13** (`ICKDSF13`) | + 3375, 3380, 3390 | `SYS2.LINKLIB(ICKDSF13)`, from `Packages/ICKDSF13` |

Release 6 against a 3390 answers `ICK30712I <cuu> DEVICE TYPE VERIFICATION
FAILED`. `[tested]`

```jcl
//ICKDSF EXEC PGM=ICKDSF13,REGION=4096K
//SYSPRINT DD  SYSOUT=*
//SYSIN    DD  *
  INIT UNITADDRESS(<cuu>) NOVERIFY VOLID(<volser>) OWNER(HERCULES) -
               VTOC(0,1,<tracks>)
/*
```

Two things that are easy to miss:

1. **The volume must be OFFLINE.** That is the default for a freshly attached
   device; `V <cuu>,OFFLINE` otherwise.
2. **ICKDSF stops for an operator reply.** `*nn ICK003D REPLY U TO ALTER VOLUME
   <cuu> CONTENTS, ELSE T` — a job that appears to hang is waiting for `R nn,U`.

`NOINDEX` is not a keyword at this level: `ICK30211I KEYWORD 'NOINDEX' IS
IMPROPER`. `[tested]`

**Unresolved:** `ICKDSF13 INIT` on a 3390 attached with `cu=3990` answers
`ICK31851I EXTENDED CKD FUNCTIONS CANNOT BE ACTIVATED - COMMAND TERMINATED`.
Jay's page specifies **`cu=3880`** for 3390 attachments; TK5's own configuration
uses `cu=3990` throughout. Whether the control-unit type is the cause has **not
been tested** `[assumed]`.

### `dasdload` — the route that bypasses ICKDSF

For a non-standard cylinder count, or when ICKDSF is not available, `dasdload`
writes a VTOC MVS accepts. A two-line control file is enough:

```
BLDSR2 3390-2 2184
sysvtoc vtoc trk 60
```

```
dasdload -z ctlfile BLDSR2.196
```

`dasdls` ends `rc=0`, and an `IEFBR14` allocation of five cylinders succeeds.
`[tested]` This is how the twelve build volumes on `MVSTK5-BLD` were made.

## `IEHLIST` lies about free space on a `dasdload` volume

A freshly loaded volume reports

```
THERE ARE 0 EMPTY CYLINDERS PLUS 0 EMPTY TRACKS ON THIS VOLUME
```

and allocation on it works. `dasdload` writes no **Format-5 free-space DSCBs**,
so `IEHLIST LISTVTOC` computes zero, while DADSM allocates regardless. `[tested]`

**Test the allocation, not the report.** An `IEFBR14` with a `SPACE=` DD is the
one-job check and it is definitive:

```jcl
//S1     EXEC PGM=IEFBR14
//D       DD  DSN=<hlq>.ALLOCTST,DISP=(,CATLG),
//             UNIT=3390,VOL=SER=<volser>,SPACE=(CYL,(5,5,10)),
//             DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
```

On a genuinely full volume the same report is true — see `[PM-2026-003]` for
how to tell the two apart.

## Bringing a volume up

```
attach <cuu> 3390 dasd/<file> cu=3990        Hercules console
/V <cuu>,ONLINE                              MVS console
/M <cuu>,VOL=(SL,<volser>),USE=STORAGE        optional, sets the use class
```

Persist it in the Hercules configuration and, for a volume MVS should mount at
IPL, in `SYS1.PARMLIB(VATLST00)` (fixed columns: volser 1–6, residency 8, use
class 10, device type 12–19, mount flag 21).

**A volume attached to a running system shows a blank VOLSER in `D U`** even
when the label is present and `dasdls` reads it. After the next IPL it displays
correctly. `[tested]` — do not chase this as damage.
