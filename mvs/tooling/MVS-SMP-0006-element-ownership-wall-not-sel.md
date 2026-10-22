---
id: MVS-SMP-0006
title: SMP 4 keys element ownership on MOD(name) in the CDS — a SYSMOD that does not own the module prints NOT SEL, copies nothing and ends RC 00
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE system, SMP 4 HMASMP LVL 04.48, 2026-09-14 — install of a fresh, free FMID into a throwaway library, JOB00291 (job numbers are from that system; output quoted in mvslovers/mbt#98)"
  - "mvslovers/ftpd#143 — the same failure first sighted 2026-09-13 with a product install: every condition code RC 00, target library empty"
  - "mvslovers/httpd#266 — NOT SEL install JOB00269 (all RC 00, libraries empty), then the same package after UCLIN removed the old owner's MOD and LMOD entries, JOB00281, HMA2380 present (MVS/CE system)"
  - "ufsd docs/installation.md section 10 at commit 6804ee7 — NOT SEL next to a DELETED predecessor in an upgrade; NOT SEL in place of HMA2380 as the failure"
verified_on: 2026-09-14
verified_platforms: ["MVS/CE (3.0.0)"]
applies_to: [ufsd, ftpd, httpd, mvsmf, mbt]
tags: [smp, smp4, not-sel, element-ownership, mod, cds, hma2380, hma2270, fmid, install]
related: [ECO-0007, MVS-SMP-0004, MVS-SMP-0007, MVS-SMP-0008, MVS-SMP-0009, MVS-SMP-0014]
---

## The claim

**SMP 4 decides who may install `MOD(x)` from the owner recorded in the CDS, not
from the library the element is going to live in.** A SYSMOD that does not own
`MOD(x)` cannot install it. `[tested]`

The element summary then prints `NOT SEL` for the module:

```
ELEM   ELEMENT   ELEM
TYPE   NAME      STATUS
MOD    FTPD      NOT SEL
```

Nothing is copied, and everything else reports success: RECEIVE, APPLY CHECK,
APPLY and ACCEPT all end RC 00, APPLY and ACCEPT print `HMA2270 … SUCCESSFULLY
COMPLETED`, `STATUS = REC APP ACC` is recorded in both zones, and the target
library is empty.

## The evidence

- Measured twice. First sighted 2026-09-13 with a product install (ftpd#143),
  then reproduced 2026-09-14 (JOB00291, MVS/CE system, mbt#98): a **fresh, free**
  FMID installing into a throwaway library that belonged to no other install
  still lost to the existing owner of the module name. All steps RC 00, `REC APP
  ACC`, library empty.
- httpd#266 shows the other half: the same package installed correctly (JOB00281,
  `HMA2380 COPY SUCCESSFUL - MOD=HTTPD - LMOD=HTTPD - LIBRARY=LINKLIB`) once
  UCLIN had removed the old owner's `MOD` and `LMOD` entries from the CDS and
  ACDS (`MVS-SMP-0009`). Only the inventory changed.

## What separates a real install from the empty one

```
HMA2380 COPY SUCCESSFUL - MOD=… - LMOD=… - LIBRARY=…
```

It appears for every module that was installed and is absent from the NOT SEL
run. **Verify every install by listing the members of the target library**; the
condition codes do not tell (`MVS-SMP-0007`).

`NOT SEL` alone is not proof of failure. In an upgrade that deletes its
predecessor the element report can show `NOT SEL` next to the predecessor's
`DELETED` row while the install worked; the pair `HMA2240` (predecessor module
deleted) and `HMA2380` (new module copied) per module is what shows the upgrade
happened (`MVS-SMP-0008`). `[source: ufsd docs/installation.md §10, 6804ee7]`

## Consequences

- **Versioning the product data sets never bought a clean cut between releases.**
  The collision is on the module name in the inventory, not on the data set.
  `[tested]`
- **A test install needs throwaway module names as well as a throwaway id.** A
  throwaway FMID alone measures this wall instead of whatever the test meant to
  measure. `[tested]`
- **A release that deletes only its immediate predecessor leaves an older owner
  of the module in place, and then SMP installs nothing.** ufsd's guide
  documents this for a system still on an older release than the predecessor
  (1.2.x or 1.3.0 installing 1.5.0). `[source: ufsd docs/installation.md §10,
  6804ee7]` The way out is to remove the older owner from the inventory first
  (`MVS-SMP-0009`).
- The wall does not apply to a usermod whose `++VER` names the FMID that already
  owns the module (`MVS-SMP-0004`).
