---
id: ECO-0011
title: libc370 rename() before 2.18.1 cuts the new data set name at column 72 — a 33-character name arrives as 32, or fails
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/libc370#590 (closed): table of three renames measured on an MVS/CE system, 2026-10-18 — 32-, 33- and 33-character new names from a 24-character old name"
  - "oftpd, 2026-10-18/19, on TK5 and MVS/CE systems: OFTP221E 'NOT RENAMED' with OFTPD 2253a7a on libc370 2.17.0; the same 33-, 35- and 41-character names received intact with OFTPD 7a9d9a9 on libc370 2.21.0 (mvslovers/oftpd PR #40; job numbers system-local)"
  - "libc370 v2.17.0 and v2.18.0: src/stdio/rename.c line 75, sprintf(buf, \" ALTER %s NEWNAME(%s)\", old, newnam), and src/mvs/idcams/idcams.c OP_GET, reclen = strlen(cmds)"
  - "libc370 v2.18.1: src/mvs/idcams/@@idcrec.c, idcams.c OP_GET; release notes of v2.18.1 (2026-10-18, tag v2.18.1 = d7a6ba7)"
verified_on: 2026-10-19
verified_platforms: ["MVS/CE (3.8j)", "TK5"]
applies_to: [libc370, oftpd, ftpd, ufsd, httpd]
tags: [libc370, rename, idcams, alter, newname, column-72, truncation, data-set-name, silent-failure]
related: []
---

## The claims

1. **Up to and including libc370 2.18.0, `rename()` of a whole data set builds one
   IDCAMS statement, `" ALTER <old> NEWNAME(<new>)"`, and hands it to IDCAMS as a
   single input record. IDCAMS reads columns 2 to 72 of it, so the new name is cut
   there.** With a 24-character old name the new name starts in column 41 and 32 of
   its characters fit. A longer old name leaves less room. `[source]` `[tested]`
2. **A cut name is one of two things.** If the cut falls just after a dot, the name
   is invalid, the ALTER fails and `rename()` reports it. Otherwise the cut name is a
   valid, shorter name, IDCAMS ends with condition code 0, and **the data set is
   catalogued under a name nobody asked for**. `[tested]`
3. **The caller cannot see the second case.** A `rename()` that returns 0 on a library
   before 2.18.1 is no proof that the name is the requested one. A DELETE of the long
   name then answers "not found" and a DELETE of the short one succeeds. `[tested]`
4. **libc370 2.18.1 fixes it.** `idcams()` now gives IDCAMS the command record by
   record, each within column 72: a line is broken at the last blank outside quotes
   with IDCAMS's `-` continuation; a line that cannot be broken makes `idcams()`
   return -1 with `errno` `EINVAL` without calling IDCAMS. `[source]` `[tested]`
5. **A data set already renamed by an older library may sit under a shortened name.**
   The 2.18.1 release notes say so; look for one in the catalog. `[source]`
6. `remove()` builds ` DELETE %s` (at most 52 columns) and is not affected.
   `[source: libc370#590]` Any other `idcams()` caller that formats two data set names
   into one statement may be.

Consumers that rename with `rename()` need **libc370 2.18.1 or later**; oftpd raised
its floor to 2.18.1 for this (mvslovers/oftpd PR #40).

## The evidence

Names below are edited to remove the system names of the test setups; the lengths are
the measured ones.

**Measured on an MVS/CE system, 2026-10-18 (libc370#590).** A server received into a
temporary data set and renamed it. Old name `IBMUSER.OFTPTMP.T0000152` (24 characters):

| new name requested | length | statement length | catalogued as |
|---|---|---|---|
| `IBMUSER.OFTPIN.COLL.SYSA.TO.SYSB` | 32 | 73 | the full name (the `)` in column 73 was dropped, IDCAMS still renamed) |
| `IBMUSER.OFTPIN.COLL2.SYSA.TO.SYSB` | 33 | 74 | `IBMUSER.OFTPIN.COLL2.SYSA.TO.SYS` |
| `IBMUSER.OFTPIN.COLL3.SYSA.TO.SYSB` | 33 | 74 | `IBMUSER.OFTPIN.COLL3.SYSA.TO.SYS` |

The caller believed the full name (its own message and records named `...TO.SYSB`).
A catalog listing showed only the 32-character names.

**Measured with OFTPD `2253a7a` on libc370 2.17.0, MVS/CE.** A file relayed over two
hops arrived with the virtual name `SYSX.SVC.TO.SYSB.F` and the final name
`IBMUSER.OFTPIN.SYSX.SVC.TO.SYSB.F` (**33 characters**, cut at 32 =
`IBMUSER.OFTPIN.SYSX.SVC.TO.SYSB.`, ending in a dot). Console, read by the
maintainer:

```
OFTP221E <partner>: IBMUSER.OFTPTMP.T0000157 NOT RENAMED TO IBMUSER.OFTPIN.SYSX.SVC.TO.SYSB.F
SYSX.SVC.TO.SYSB.F not accepted, EFNA 12
```

The same for the second file of the pair (`.T`). Nothing was left behind: no
`IBMUSER.OFTPTMP.*`, no `IBMUSER.OFTPIN.SYSX.*`. The sender saw reason 12.
`[tested]` The statement behind this: the 32-character cut ends in a dot, which no
data set name may do, so the ALTER fails. `[inferred]` from the arithmetic and the
`OFTP221E` message; IDCAMS's own message for it was not captured.

**Measured with OFTPD `7a9d9a9` on libc370 2.21.0, on five systems (MVS/CE and TK5).**
The 33-character name arrived (system-local JOB00652), so did a 41-character one
`IBMUSER.OFTPIN.SYSR.SVC.TO.SYSB.LONG.NAME` (JOB00921) and a 35-character one on a TK5
system. Each received data set was identical to its source. `[tested]`

**The library's own measurement, 2.18.0 against 2.18.1, same job (v2.18.1 release
notes):**

| call | 2.18.0 | 2.18.1 |
|---|---|---|
| `rename()` to a 33-character name from a 24-character one | catalogued with 32 characters, condition code 0 | the full name |
| `rename()` between two 44-character names | catalogued as a 12-character name | the full name |

## What to do

- A rename that returns 0 proves nothing on a library older than 2.18.1: read the
  catalog for the full new name.
- Test names over 32 characters on purpose, both one cut after a dot (the rename
  fails) and one cut elsewhere (the rename "succeeds" under the short name).
- Two 44-character names need 105 columns, so a valid pair can be cut by about
  33 characters. `[source: libc370#590]`
