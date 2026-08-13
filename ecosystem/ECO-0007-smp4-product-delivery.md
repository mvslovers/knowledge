---
id: ECO-0007
title: Installing our products through SMP 4 — SMP copies host-bound load modules, it does not re-bind them
status: tested
platform: [mvs38j]
sources:
  - "GC28-0673-6 — OS/VS System Modification Program (SMP) System Programmer's Guide"
  - "smptest/doc/SMP-COOKBOOK.md — prototype run 2026-08-08 on mvsdev, SYSMOD TSMP100/USMP001"
  - "smptest/jcl/smpxinl.jcl, smpxrej.jcl — inline-delivery experiment, JOB01066/JOB01067"
  - "mbt/scripts/mbt/distribution.py, mbt/scripts/mbtdist.py — the generator"
  - "ufsd/project.toml [distribution] — the reference declaration"
verified_on: 2026-08-13
applies_to: [ufsd, ftpd, httpd, mvsmf, rexx370, nsf370, mbt]
tags: [smp, smp4, sysmod, fmid, jclin, lklib, mcs, installation, distribution, xmit]
related: [ECO-0001]
---

## Context

MVS 3.8j ships **SMP Release 4**, not SMP/E. There are no CSI zones, no DDDEFs
and no data element type; libraries are found by ddname, supplied as DD
overrides on the SMP procedures. The inventory is `SYS1.SMPCDS` / `SMPPTS` /
`SMPACDS` and the `SMPREC` / `SMPAPP` procedures, both single-step (`HMASMP`).

We bind on the host with ld370. The question that decided whether SMP was
usable at all was therefore: **does SMP install our finished load module, or
does it re-bind it?** Re-binding would restore attributes the build
deliberately cleared — a `norent` C module re-marked RENT takes an S0C4 on its
first static store, and only when entered at the READY prompt, so batch and
`IKJEFT01 CALL` would both pass while the module was broken.

## The mechanism

**`++MOD(name) LKLIB(ddname) DISTLIB(ddname)` combined with a COPY-style
`++JCLIN`** — an `EXEC PGM=IEBCOPY` step, not a link-edit step. The copy step
is what tells SMP the module is copied out of a library rather than built, so
the `++MOD` supplied via `LKLIB` is copied verbatim.

```
++FUNCTION(TUFS120) .
++VER(Z038) .
++JCLIN .
//COPYLOAD EXEC PGM=IEBCOPY
//AUFSDLOD DD  DISP=SHR,DSN=UFSD.V1R2M0.AUFSDLOD
//LINKLIB  DD  DISP=SHR,DSN=UFSD.V1R2M0.LINKLIB
//SYSIN    DD  *
  COPY INDD=AUFSDLOD,OUTDD=LINKLIB
  SELECT MEMBER=(UFSD,UFSDSSIR,UFSDCLNP,UFSFMT)
/*
++MOD(UFSD) LKLIB(UFSDLOAD) DISTLIB(AUFSDLOD) .
```

Three rules the copy step must obey: the copy control statements **inline**
behind `//SYSIN DD *` (SMP reads them during the JCLIN scan and cannot follow
a dataset), ddnames equal to the **last qualifier** of the dataset name, and
`SELECT MEMBER=()` present — without it SMP records the DLIB as *totally*
copied, which also caps a DLIB at two target libraries.

SMP never executes this JCL. It scans it to learn the build description.

## What was measured

**SMP copies, it does not re-bind** (2026-08-08, mvsdev, SYSMOD `TSMP100`).
SMP said so — `HMA2380 COPY SUCCESSFUL - MOD=SMPTEST - LMOD=SMPTEST -
LIBRARY=CMDLIB - RETURN CODE=00` — and `SYS2.CMDLIB(SMPTEST)` came back
**byte-identical** to the host-built module (71 503 bytes). `norent` survived
because nothing was bound.

**The SYSMOD can travel inline in the install job** (2026-08-13, mvsdev,
SMP 4 level 04.48, job `SMPXINL`/JOB01066). `//SMPPTFIN DD DATA,DLM=@@`
received RC 0, and `SYS1.SMPPTS(TXPR100)` came back byte-identical to what was
sent — including the JCLIN cards starting with `//` and the `/*` card closing
the inline copy statements.

**The MCS limit is column 72**, not 71 (same job). A `++VER` statement whose
terminating period sat in column 72 parsed correctly.

**The whole generated flow installs** (2026-08-13, a TK5 system): allocate,
receive both XMITs, RECEIVE/APPLY CHECK/APPLY/ACCEPT, all `COND CODE 0000`.

## Two corrections to our own earlier notes

- `SMP-COOKBOOK.md` §3.1 recommends `//SMPPTFIN DD *`. **That cannot work.** An
  instream stream ends at a `/*` card *or* any card with `//` in columns 1-2,
  and a SYSMOD carrying a `++JCLIN` contains both. `DD DATA,DLM=` is required,
  and the delimiter must not appear at the start of any card in the payload.
- `SMP-COOKBOOK.md` F2 gives the card limit as column 71, and
  `smptest/scripts/smpspike.py` enforces it. It is **72** — strict enough that
  the check rejects its own committed `smp/TSMP100.mcs`, whose line 6 is 72
  columns and was received successfully. 71 is the *JCL* limit (72 is JCL's
  continuation column), which is why generated JCLIN cards are still held to it.

## Consequences

- **Only the load modules go through SMP.** Sample material — procedures,
  PARMLIB patterns, jobs — ships as its own XMIT built by `xmit370` and
  restored by TSO RECEIVE. An MCS card ends at column 72, and routing a
  configuration pattern through the SYSMOD makes its content answer to a
  delivery mechanism; ufsd's `UFSDPRM0` had three `MOUNT` statements at 76
  columns. Since the target datasets are versioned, every release brings a
  fresh library anyway, so SMP tracking would buy nothing there.
- **The staging library is a delivery channel, not a system component** — the
  role a RELFILE plays for a tape product. SMP reads it during APPLY and
  ACCEPT and never again; RESTORE takes its copy from the DLIB. It is
  scratched after the ACCEPT: a load library holding the same members invites
  a STEPLIB pointed at it, which a later PTF would then silently bypass.
- **Accept the FMID once, never the PTFs.** Without an ACCEPT the DLIB stays
  empty, and a `RESTORE` then *deletes* the module instead of reverting it —
  there is no previous level to return to.
- **A ddname says nothing about the dataset behind it.** SMP reports
  `LIBRARY=LINKLIB` whether the override took effect or not, so a DD-override
  mistake is invisible in the log. Every DD that *overrides* one the procedure
  already has must precede every DD that is *added* to the step, all qualified
  with `HMASMP.`; in the wrong order both datasets are allocated and SMP uses
  the procedure's.
- **FMIDs are spent once.** The live registry is the ecosystem `CLAUDE.md`
  (§ SMP4 FMIDs). A test install must use a throwaway id: a half-applied FMID
  leaves the real one occupied, and the CDS cannot be queried to find out —
  its member names are hashes. The SMPPTS *can* be listed, because MCS entry
  names are the documented exception.
- Authorization is orthogonal and remains the weak point: an install can
  complete cleanly and the product still not start. See `ECO-0001`.

## Open

- Whether `REQ()`/`PRE()` is checked against the CDS (applied) or the ACDS
  (accepted). With the FMID accepted and service never accepted, both would
  find it — untested, and it first matters for the ufsd → httpd chain.
- The behaviour of three target libraries fed from one DLIB. Documented as
  "the third silently overwrites the second SYSLIB sub-entry"; not observed.
  No product needs it yet.
- Whether DDDEF entries via UCLIN work in SMP 4, which would replace the DD
  overrides and remove the ordering trap above.
