---
id: MVS-SEC-0009
title: The RAKF profile loader sorts its own input; U0300, U0400 and U0500 abort a reload and keep the old table
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE container with the RAKF built into the image, and a second with RAKF 2.0.0 installed from the release deck (TRKF200, CLPA IPL), 2026-10-21; probe: AC(1) program, libc370 2.25.1, racf_auth R/U/A; console and job output container-local and not kept"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/CJYRPROF.hlasm (header RRKF007 'Remove the need to sort the input'; SORT01-SORT07; labels OUTOFORD, NOUAR, PERMINVL, NOACCAUT), SRCLIB/CJYRUIDS.hlasm (same RRKF007 sort; ABEND2)"
  - "Rob Prins (RAKF maintainer), 2026-10-22: create profiles with the RAKF commands, not by hand (his statement)"
verified_on: 2026-10-21
applies_to: [ftpd, mvsmf, libc370]
tags: [rakf, cjyrprof, rakfprof, loader, sort, u0300, u0400, u0500, reload, security]
related: [MVS-SEC-0006, MVS-SEC-0008, MVS-SEC-0011, ECO-0008, MVS-SEC-0010]
---

## The claims

- **`S RAKFPROF` with an unsorted `SYS1.SECURE.CNTL(PROFILES)` loads normally**, on the image RAKF and
  on RAKF 2.0.0: `RAKFPROF7  RAKF PROFILES UPDATED`. File order does not matter. `[tested]`
  `[source: CJYRPROF reads all non-comment records into a table of 2,000 entries and sorts it
  with a bubble sort over the 80-byte record before processing (change RRKF007)]`
- **`U0300` happens only for duplicates of class + entity + id** (the same key twice), never for merely
  unsorted order: the compare covers the record up to the access field, and "not greater than the
  previous" means equal. `[tested]` `[source: CJYRPROF READLOOP, CLC INRECNEW(ACCAUTH-INREC) / BNH OUTOFORD]`
  ```
  RAKFPROF3  I/P RECORDS OUT OF ORDER
  RAKFPROF3  **  PROGRAM TERMINATED  **
  IEF450I RAKFPROF RAKFPROF - ABEND S000 U0300
  ```
- `U0400`: a permit record (an id in columns 53-60) without a preceding universal record (blank id) for
  the same class and entity; `RAKFPROF4  PERMIT RECORD WITHOUT UNIVERSAL ACCESS RECORD`. `[tested]`
  `[source: NOUAR]`
- `U0500`: an entity record without access authority; `RAKFPROF6  ENTITY RECORD WITH NO ACCESS
  AUTHORITY`. `[tested]` `[source: NOACCAUT]` The source also has `RAKFPROF5  PERMIT RECORD WITHOUT
  GROUPID/USERID` (PERMINVL, also ABEND 500); not measured.
- **All three abort the load and leave the old chain in place** on a reload: the probe after the failed
  reload showed the previous levels; a raised access level in the same file was not applied.
  `[tested]` on the image RAKF and on 2.0.0.
- The USERS loader (CJYRUIDS) carries the same sort change (RRKF007): unsorted users input is
  accepted; invalid input gives `RAKFUIDS2  INPUT DATA INVALID OR OUT OF SEQ.` `[source: CJYRUIDS]`
  (the sort itself was measured only for PROFILES).
- The maintainer advises creating profiles with the RAKF commands (`RDEFINE`/`RDEF`, `PERMIT`/`PE`, then
  `S RAKFPROF`) rather than editing PROFILES by hand; `PERMIT` refuses without a universal-access
  record (HELP member PERMIT). `[attributed]`
- A failing loader at **IPL** is a different case: on 2.0.0 JES2 does not start (MVS-SEC-0011). A duplicate in the file at IPL is
  therefore worse than at `S RAKFPROF`. `[tested]`

## The evidence

Unsorted test input (JESSPOOL before DASDVOL and FACILITY, entity blocks reversed, two user lines swapped);
`racf_auth` results (R=READ U=UPDATE A=ALTER; 0 allowed, 4 no profile, 8 denied), identical on both builds:

```
MVSCE02 JESSPOOL ZQSORT.X   R0 U8 A8
MVSCE02 JESSPOOL ZQALPHA.X  R0 U0 A8
MVSCE01 JESSPOOL ZQALPHA.X  R0 U8 A8
MVSCE01 JESSPOOL ZQSORT.X   R8 U8 A8
MVSCE02 JESSPOOL OTHER.X    R8
MVSCE02 FACILITY FTPAUTH    R8 (unchanged)
MVSCE02 DATASET SYS1.SECURE.CNTL  R8 (unchanged)
MVSCE02 NOSUCHCL X.Y        image RAKF R4, RAKF 2.0.0 R8 (tells the builds apart, MVS-SEC-0010)
```

So `racf_auth` is level-correct after the loader's own sort. Duplicate case: the same input plus a duplicate
`JESSPOOL ZQSORT.* MVSCE02 READ` line (and a variant that also raises an access level in a non-duplicate
line) gave the three console lines above on both builds.

Reload mechanics: `S RAKFPROF` reloads PROFILES, `S RAKFUSER` USERS, `S RAKF` both; the earlier
statement in ECO-0008 that RAKFUSER/RAKFPROF are not the path on an installed system does not hold
for these images (see the marked addition there).
