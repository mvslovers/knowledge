---
id: MVS-SMP-0011
title: Load-module aliases reach the target library only through TALIAS on the ++MOD — without it SMP copies the main member and every step ends RC 00
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE system, SMP 4 HMASMP LVL 04.48, 2026-09-27, throwaway FMIDs and throwaway module names in libraries that belong to no product — measurement A (no TALIAS) TTST008 JOB00505 to JOB00512; measurement B (TALIAS) TTST009 JOB00513, JOB00515, JOB00516; measurement C (upgrade with DELETE) TTST010 JOB00517 to JOB00519. Output in mvslovers/mbt#112 (comments) and mvslovers/mbt#114"
  - "mbt scripts/mbt/distribution.py, the ++MOD assembly (TALIAS card), origin/main b6f43e7"
  - "mvslovers/mbt#113 (aliases on [[module]], MERGED 2026-09-27), mvslovers/mbt#114 (TALIAS in the SMP package, MERGED 2026-09-27), mvslovers/mbt#115 (a release that drops an alias; OPEN, unmeasured)"
verified_on: 2026-09-27
verified_platforms: ["MVS/CE (3.0.0)"]
applies_to: [mbt, brexx370]
tags: [smp, smp4, alias, talias, mod, copy, jclin, delete, mbt]
related: [MVS-SMP-0008, ECO-0007]
---

## The claims

1. **A `++MOD` without `TALIAS(…)` makes SMP copy the main member only.** The
   target library and the DLIB end up with no alias, and every step ends CC 0000.
   `[tested]`
2. **`++MOD … TALIAS(a,b)` with the unchanged COPY-style JCLIN installs true
   aliases in both libraries**, re-binds nothing (`AC=1` and `norent` survive)
   and records `TALIAS = …` on the **MOD** entry in both zones. `[tested]`
3. **An upgrade with `DELETE` moves the aliases onto the new module.** All three
   names ran the new code. `[tested]`
4. **A release that drops an alias is not measured.** `[inferred]` (below)

## Measurement A: no TALIAS

Throwaway module `ALTSTM` with aliases `ALTSTA1` / `ALTSTA2`; the package is the
generator's own, with the alias refusal bypassed for this run. The staging library
after TSO RECEIVE holds true aliases (alias bit set, main member `ALTSTM`).

- Install (JOB00509): RECEIVE, APPLY CHECK, APPLY, ACCEPT all CC 0000,
  `HMA2380 COPY SUCCESSFUL - MOD=ALTSTM`, `HMA2270` for APPLY and ACCEPT.
- The APPLY and ACCEPT IEBCOPY runs each report `ALTSTM HAS BEEN SUCCESSFULLY
  COPIED` and nothing else.
- Target library = `[ALTSTM]`, DLIB = `[ALTSTM]`, staging library =
  `[ALTSTA1, ALTSTA2, ALTSTM]`.
- `LMOD(ALTSTM)` carries only `SYSTEM LIBRARY` and `LKED ATTRIBUTES = COPY`;
  `LMOD(ALTSTA1)` is not found (JOB00510).

## Measurement B: with TALIAS

The only change was one line (JOB00513 / JOB00515, `TTST009`, module `ALTSBM`,
`ac = 1`, `norent`):

```
++MOD(ALTSBM) LKLIB(ALTSBLKL) DISTLIB(AALTSBLD)
      TALIAS(ALTSBA1,ALTSBA2) .
```

The JCLIN stays COPY. Every step CC 0000; the APPLY and ACCEPT IEBCOPY runs each
copy `ALTSBA1`, `ALTSBA2` and `ALTSBM`. IEHLIST DUMP (JOB00516) of the target
library and the DLIB:

```
ALTSBA1   000016B1  ... 00000043F2 ... C1D3E3E2C2D4 40400101   <- alias bit, main member ALTSBM, AC=1
ALTSBA2   000016B1  ...
ALTSBM    0000162C  ... 00000043F2 ... 00010100                <- REUS, no RENT; APF section AC=1
```

Nothing is re-bound, so `norent` and `AC=1` survive. SMP records
`TALIAS = ALTSBA1 ALTSBA2` on the MOD entry in both zones; `LMOD(ALTSBA1)` does
not exist.

The SMP 4 manual covers this case: with a module supplied on an LKLIB and defined
by copy JCL, SMP copies it, and aliases named for it must exist in the LKLIB.
(As quoted in the measurement notes of mbt#112; the manual was not re-read at
ingest.)

## Measurement C: upgrade with DELETE

`TTST010` with `++VER(Z038) DELETE(TTST009)`, the same names and aliases and a
changed module body (the new code ends RC 4, the old ended RC 0):

- APPLY RC 04 (`HMA2461 … TTST009 NOT FOUND ON SMPSCDS`, as with any DELETE,
  `MVS-SMP-0008`), ACCEPT ran through the relaxed gate (JOB00518).
- `EXEC PGM=ALTSBM`, `PGM=ALTSBA1` and `PGM=ALTSBA2` with `STEPLIB` on the target
  library: **CC 0004 each**, so all three names ran the new code (JOB00519). The
  old module was not executed in that job.
- `MOD(ALTSBM)`: `FMID/RMID = TTST010`, `TALIAS` in both zones; `TTST009` stays
  as a tombstone.
- **The two libraries are treated differently.** APPLY deletes only the LMOD in
  the target library (`HMA2240 … LMOD ALTSBM ON ALTSBLNK LIBRARY`); ACCEPT deletes
  the module and both aliases in the DLIB (`HMA2240 … MODULE ALTSBM / ALTSBA1 /
  ALTSBA2 ON AALTSBLD LIBRARY`). In the target library the aliases were replaced
  only because the new SYSMOD copied the same names again.

## Not measured: a release that drops an alias `[inferred]`

From the asymmetry above: if a release no longer lists an alias, nothing replaces
it, and in the target library it most likely stays behind as an alias of a
deleted member, with the old TTR. Running it would either execute stale code or
fail, the CDS would no longer list it, and every condition code would read
success. This is an inference, not a measurement (mvslovers/mbt#115, open at
ingest). Read that issue before removing an alias from a shipped product.

## Generator

mbt emits `TALIAS` on the `++MOD` of every module that has `aliases`, on a card of
its own. `[source: mbt scripts/mbt/distribution.py, b6f43e7; mvslovers/mbt#114]`
The alias list is declared per module (`aliases = [...]` on `[[module]]`,
mvslovers/mbt#113).
