---
id: ECO-0007
title: Installing our products through SMP 4 — SMP copies host-bound load modules, it does not re-bind them
status: tested
platform: [mvs38j]
sources:
  - "GC28-0673-6 — OS/VS System Modification Program (SMP) System Programmer's Guide"
  - "smptest/doc/SMP-COOKBOOK.md — prototype run 2026-08-08 on mvsdev, SYSMOD TSMP100/USMP001"
  - "smptest/jcl/smpxinl.jcl, smpxrej.jcl — inline-delivery experiment; mvsdev (MVS/CE) JOB01066/JOB01067, drnmig3a (TK5) JOB00021/JOB00022"
  - "smptest/jcl/smplist.jcl — LIST syntax probe and SYSMOD inventory, both distributions"
  - "mbt/scripts/mbt/distribution.py, mbt/scripts/mbtdist.py — the generator"
  - "ufsd/project.toml [distribution] — the reference declaration"
  - "mvsdev, 2026-08-14 — TFTP100 removal: JOB01078 RESTORE, JOB01079 REJECT, JOB01080 UCLIN"
  - "ftpd/doc/uninstall.md, ufsd/docs/uninstall.md — the operator procedure"
verified_on: 2026-08-14
verified_platforms: ["MVS/CE (mvsdev)", "TK5 (drnmig3a)"]
applies_to: [ufsd, ftpd, httpd, mvsmf, rexx370, nsf370, mbt]
tags: [smp, smp4, sysmod, fmid, jclin, lklib, mcs, installation, distribution, xmit]
related: [ECO-0001, ECO-0008, MVS-SMP-0001, MVS-SMP-0002, MVS-SMP-0003, MVS-SMP-0004, MVS-SMP-0005]
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

**The SYSMOD can travel inline in the install job** — measured on **both
distributions** (2026-08-13, SMP 4 level 04.48). `//SMPPTFIN DD DATA,DLM=@@`
received RC 0 on MVS/CE (`mvsdev`, job `SMPXINL`/JOB01066) and on TK5
(`drnmig3a`, JOB00021), and on MVS/CE `SYS1.SMPPTS(TXPR100)` came back
byte-identical to what was sent — including the JCLIN cards starting with `//`
and the `/*` card closing the inline copy statements. Cleaned up by `REJECT`
on both, verified absent afterwards.

**The MCS limit is column 72**, not 71 (same jobs, both distributions). A
`++VER` statement whose terminating period sat in column 72 parsed correctly.

**The whole generated flow installs** (2026-08-13, a TK5 system): allocate,
receive both XMITs, RECEIVE/APPLY CHECK/APPLY/ACCEPT, all `COND CODE 0000`.

**`LIST` needs a zone operand.** `LIST SYSMODS .` is SMP/E and gets
`HMA2033 SYNTAX ERROR`. SMP 4 wants `LIST CDS .` (applied) or `LIST ACDS .`
(accepted), optionally qualified: `LIST CDS SYSMOD(TUFS120) .`. **RC 04 with
an empty list means the id is unknown to that zone** — the free-id test we
previously did not have. *Unknown to the zone is not the same as not received:
a SYSMOD creates its zone entry at APPLY, not at RECEIVE — see `MVS-SMP-0002`.*
A hit prints `TYPE`, `STATUS` (`REC`/`APP`/`ACC`) and
the owning `FMID`. Unqualified is 116 172 lines on MVS/CE, 87 602 for `ACDS`.

**IBM's function FMIDs on MVS 3.8j are `E??nnnn`.** `EBB1102` is MVS 3.8j
itself — `TYPE=FUNCTION`, `STATUS=REC ACC RGN` on both distributions —
alongside `EAS1102`, `EBT1102`, `EDE1102`, `EDM1102`, `EDS1102`, `EJE1103`,
`EVT0108`, `ETV0108`. The `T???nnn` ids one sees on a running system are
**USERMODs**, and they are distribution-specific: `TMVS804/816`, `TIST801`,
`TJES801`, `TNIP800`, `TTSO801` are all applied USERMODs on MVS/CE and are
**absent from TK5**. Our `T` prefix is therefore correct for the reason of
avoiding `E??nnnn`, not because it mirrors a sysgen convention — there is no
such convention.

**RAKF is not a usable prerequisite.** `RAK0001` is an applied USERMOD on
MVS/CE and **absent from TK5's CDS** (RC 04) — while SVC 244 demonstrably
works on TK5 (see `ECO-0001`). A `PRE(RAK0001)` would therefore fail an APPLY
on a system where the facility it stands for is present and working. The SMP
inventory carries no information about SVC 244 availability.

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
  there is no previous level to return to. **The price is that the FMID becomes
  permanent**: see below.
- **An accepted function SYSMOD cannot be removed by `RESTORE` or `REJECT`, only
  by `UCLIN`** (2026-08-14, `mvsdev`, `TFTP100`). The two documented routes
  close each other off:

  ```
  HMA2452 ** SYSMOD TFTP100 SELECTED FOR RESTORE HAS BEEN ACCEPTED    RC 12
  HMA2462 ** SYSMOD TFTP100 NOT FOUND ON SMPPTS LIBRARY               RC 12
  ```

  `RESTORE` refuses because the SYSMOD was accepted. `REJECT` then fails for a
  reason that looks unrelated: the `ACCEPT` **removes the MCS from
  `SYS1.SMPPTS`**, and `REJECT` works from that member — verified directly, the
  PTS holds 3091 members and `TFTP100` is not among them. `UCLIN` on both zones
  works and is the only way:

  ```
   UCLIN CDS .                       (and the same block for ACDS)
    DEL SYSMOD(TFTP100) MOD(FTPD) .
    DEL MOD(FTPD) .
    DEL LMOD(FTPD) .
    DEL SYSMOD(TFTP100) .
   ENDUCL .
  ```

  Every `DEL` answers `HMA2550 UPDATE COMPLETE`, both blocks end RC 00, and a
  following `LIST` reports the id unknown to both zones. `UCLIN` edits the
  inventory only — the target and distribution libraries keep their members and
  must be scratched separately before a re-install. Documented for operators in
  each product's `uninstall.md`.
- **This makes "a new minor is a clean cut (RESTORE + REJECT the old)" wrong as
  written** — that is how the ecosystem registry describes a minor bump, and it
  cannot work for a shipped `accept_fmid = true` package. Either the uninstall
  goes through `UCLIN`, or the accept default is reconsidered. Raised for
  discussion as an mbt ticket.
- **A ddname says nothing about the dataset behind it.** SMP reports
  `LIBRARY=LINKLIB` whether the override took effect or not, so a DD-override
  mistake is invisible in the log. Every DD that *overrides* one the procedure
  already has must precede every DD that is *added* to the step, all qualified
  with `HMASMP.`; in the wrong order both datasets are allocated and SMP uses
  the procedure's.
- **FMIDs are spent once.** The live registry is the ecosystem `CLAUDE.md`
  (§ SMP4 FMIDs). A test install should still use a throwaway id, though the
  `UCLIN` route above means an id occupied by a half-applied SYSMOD is now
  recoverable rather than lost. What has not changed is that you cannot find
  out by asking: the CDS stores hashed member names, and `LIST CDS SYSMOD(x)`
  is the only reliable probe. The SMPPTS *can* be listed, because MCS entry
  names are the documented exception — but after an ACCEPT the member is gone,
  so its absence proves nothing about whether the id is free.
- Authorization is orthogonal and remains the weak point: an install can
  complete cleanly and the product still not start. See `ECO-0001`.

## Open

- ~~Whether `REQ()`/`PRE()` is checked against the CDS (applied) or the ACDS
  (accepted).~~ **Answered 2026-09-23: each function checks the zone it writes.
  `APPLY` resolves against the CDS, `ACCEPT` against the ACDS.** See
  `MVS-SMP-0001`. For the ufsd → httpd chain: a prerequisite that is applied but
  not accepted satisfies an APPLY and blocks every ACCEPT naming it.
- The behaviour of three target libraries fed from one DLIB. Documented as
  "the third silently overwrites the second SYSLIB sub-entry"; not observed.
  No product needs it yet.
- Whether DDDEF entries via UCLIN work in SMP 4, which would replace the DD
  overrides and remove the ordering trap above. `UCLIN` itself is now known to
  work for zone entries (`DEL SYSMOD/MOD/LMOD`, RC 00), so what is untested is
  the DDDEF entry type, not the mechanism.
