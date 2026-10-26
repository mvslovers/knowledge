---
id: MVS-DASD-0003
title: On a fresh TK5 the first new member copied into SYS1.PARMLIB abends D37-04 — a compress or a PARMLIB of your own clears it, and what D37-04 means here is not established
status: tested
platform: [mvs38j]
sources:
  - "TK5 throwaway container, 2026-10-22 — IEBGENER copy of FTPDPRM0 into SYS1.PARMLIB (PARMCPY, JOB00045: IEC031I D37-04, IEF450I ABEND SD37), IEBCOPY self-copy compress (JOB00046, CC 0000), the copy again (JOB00047, CC 0000), private PARMLIB (PRIVPL, JOB00048, CC 0000). Job numbers are container-local, the container is gone"
  - "mvslovers/ftpd tag v1.3.0, docs/installation.md step 7 ('Which PARMLIB') and the troubleshooting row for IEC031I D37-04; mvslovers/ftpd#286"
verified_on: 2026-10-22
verified_platforms: ["TK5"]
applies_to: [ftpd]
tags: [dasd, space, d37, iec031i, parmlib, tk5, pds, iebgener, iebcopy, compress, directory]
related: [PM-2026-003, MVS-DASD-0001]
---

## The claims

1. **The first new member copied into `SYS1.PARMLIB` of a fresh TK5 ends `SD37`.** `[tested]`

   ```
   IEC031I D37-04,IFG0554T,PARMCPY,COPY,SYSUT2,390,TK5RES,SYS1.PARMLIB
   IEF450I PARMCPY COPY - ABEND SD37 U0000
   ```

   The step was an IEBGENER copy, member to member, of `FTPDPRM0` (JOB00045).
2. **Compressing the library clears it.** An IEBCOPY `COPY` of `SYS1.PARMLIB` onto itself
   (`IEB161I COMPRESS TO BE DONE USING INDD NAMED PARMLIB`, JOB00046, CC 0000), then the same
   member copy again (JOB00047, CC 0000). `[tested]`
3. **A PARMLIB of your own avoids the library altogether.** Allocate `HERC01.PARMLIB`, copy
   `FTPDPRM0` into it (JOB00048, CC 0000) and start the task with `/S FTPD,D='HERC01.PARMLIB'`;
   `F FTPD,CONFIG` then lists the values from that member. `[tested]`
4. **MVS/CE does not have the problem for this member.** It has `SYS2.PARMLIB` with room, and
   the shipped procedure's default `D='SYS2.PARMLIB'` works without a change. `[tested]`
   (`SYS2.PARMLIB` does not exist on TK5. `[source: ftpd docs/installation.md at v1.3.0]`)

## What D37-04 means here — not established

The inbox note reads the abend as "the directory has no room for another member". The product's
guide says "the member did not fit". The measurements do not settle which:

- `PM-2026-003` reads `D37` as "space exhausted, no secondary extents left". That is the
  data-extent reading.
- A compress of a PDS gives back the **data** space held by deleted or replaced members. It does
  not enlarge the directory. That the compress cured the abend fits a data-space shortage at
  least as well as a full directory. `[inferred]`
- The sub-code `04` was not looked up in an IBM manual at ingest, so neither reading rests on the
  code itself.

Neither reading was separated by a measurement: the directory block count and the extent usage
of `SYS1.PARMLIB` before and after the compress were not listed.

What can be said without choosing: the abend happens on the first **new** member, the library
accepts the copy after a compress, and a private library has no such problem. Do not write
"directory full" in a document or an error message for this abend until the extent and
directory figures have been listed.

## What to do

- Before adding a member to `SYS1.PARMLIB` of TK5, list the library (`LISTDS` with `MEMBERS`
  and the space attributes, or an `IEHLIST LISTVTOC`) and keep the figures with the job.
- Prefer a PARMLIB of your own for a product's configuration members; the product's `D=`
  start parameter exists for that. Leaving `SYS1.PARMLIB` alone also leaves out the compress,
  which rewrites a system library in place.
- A compress of `SYS1.PARMLIB` rewrites the library under the running system: do it when
  nothing else reads it, and keep a backup copy first. `[inferred]`

## What was not established

- The cause of D37-04 here (data extents or directory), see above.
- Whether a TK5 that has been in use for a while behaves the same; the measurement is on a
  fresh container.
