---
id: MVS-SEC-0006
title: When several RAKF profiles match, the last one in EBCDIC sort order wins, not the longest
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers (RAKF built into the images) and MVS/CE containers with RAKF 2.0.0, 2026-10-21; AC(1) probe, libc370 2.25.1; job output container-local and not kept"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/CJYRPROF.hlasm (SORT01-SORT07 bubble sort over the 80-byte record; each new profile block points to the previous one via LASTRPE), SRCLIB/ICHSFR00.hlasm ENTYCLLP (walks the chain from its head, first match wins)"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf]
tags: [rakf, jesspool, profile-order, ebcdic, sort, generic-profile, security]
related: [MVS-SEC-0004, MVS-SEC-0005, MVS-SEC-0009, MVS-SEC-0008, MVS-JES2-0002]
---

## The claims

- Among several profiles that match one entity, **the one that sorts last in ascending EBCDIC order
  wins**, not the longest and not the file order. `[tested]` The loader sorts the PROFILES records by
  the 80-byte line (class, entity, id, access) and the chain head is the last in sort order, which the
  check tries first. `[source: CJYRPROF sort + LASTRPE chain; ICHSFR00 ENTYCLLP]`
- Therefore (JESSPOOL, 8-character cap): `[tested]`
  - `OWN*` vs `OWN1.*`: `OWN1.*` wins.
  - `OWN*` vs `OWN-*`: `OWN-*` wins.
  - `OWN*` vs `OWN.*`: **`OWN*` wins**, the less specific one, because `*` (X'5C') sorts above `.` (X'4B').
  - A discrete 8-character profile beats `ZQ1.*`.
  - A specific profile beats `*`.
  - The same ordering on the image RAKF and on RAKF 2.0.0.
- **A `.*` NONE profile does not shield against a `*` READ profile**: `*` sorts after `.*`, so the
  `*` profile wins. This matters for an entity with an empty owner (`.JOBA.JOB00001`, a reader job
  submitted without USER, MVS-JES2-0002). `[tested]` `[source: sort order]`
- A profile that matches the entity but has no row for the caller falls to **its own UACC**; it does
  not fall through to a less specific profile. See MVS-SEC-0008, fixture 2 without ADMIN rows.

## The evidence

Entity `.JOBA.JOB00001` (empty owner) and `ZQOTHER.JOBA.JOB00001`, user MVSCE02, own ACEE, RAKF
2.0.0, READ/UPDATE/ALTER:

| profiles | `.JOBA.JOB00001` | `ZQOTHER.JOBA.JOB00001` |
|---|---|---|
| `.*` NONE and `*` READ | R0 U8 A8 (READ wins) | R0 U8 A8 |
| `.*` NONE only | R8 U8 A8 | R4 U4 A4 |
| `*` READ only | R0 U8 A8 | R0 U8 A8 |

The sort is done by the loader itself: unsorted input is accepted (MVS-SEC-0009), so file order is
irrelevant for precedence.
