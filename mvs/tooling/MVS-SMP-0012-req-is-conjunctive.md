---
id: MVS-SMP-0012
title: REQ(a,b) is an AND — one absent id in the list fails the APPLY CHECK, so REQ cannot express a version floor
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE system, SMP 4 HMASMP LVL 04.48, 2026-09-14 — job TZMFREQ, throwaway ids TTST005, TTST006 and TTST007, APPLY CHECK only, all three REJECTed afterwards (output as quoted in the inbox note; not carried in a public issue)"
verified_on: 2026-09-14
verified_platforms: ["MVS/CE (3.0.0)"]
applies_to: [mbt, ufsd, httpd, mvsmf]
tags: [smp, smp4, req, pre, requisite, conjunctive, apply-check, hma3022, hma3590, hma3971, version-floor]
related: [MVS-SMP-0001]
---

## The claim

**A `REQ` list is conjunctive: every id in it must be satisfied.** A present
requisite does not rescue a list that also names an absent one. `[tested]`

## The measurement

Three SYSMODs carrying nothing but a `++VER`, APPLY CHECK only. `THTP410` was
installed on the system, `TZZZ999` was not:

| `REQ` | APPLY CHECK |
|---|---|
| `REQ(THTP410)` — installed | **CC 0000** |
| `REQ(TZZZ999)` — absent | CC 0012 |
| `REQ(THTP410,TZZZ999)` | **CC 0012** |

```
HMA3022 ** APPLY PROCESSING TERMINATED FOR SYSMOD TTST007
        - REASON = MISSING/NOGO REQUISITES:
HMA3590     --- TZZZ999 REQ
```

Only the absent id is named; the installed one is not reported. The zone that is
checked is the one the function writes (`MVS-SMP-0001`).

## Consequence

- **`REQ(v1,v2,v3,…)` cannot say "any of these".** Listing every level a
  dependency can have, and adding the next one each release, demands all of them
  installed at once. With one function id per release and each release deleting its
  predecessor, that cannot be true: a system holds one level of the dependency and
  the earlier ones are tombstones (`MVS-SMP-0009`). Such a list makes the product
  uninstallable everywhere. `[inferred]` from the measurement and from the DELETE
  behaviour; no such list was installed.
- **There is no range syntax in what was probed**, so `REQ` can only say "exactly
  this level". That fails both ways for a dependency that moves: an older level
  does not satisfy it, and a system where a newer level was installed fresh never
  saw the id named. `[inferred]`
- **A version floor on another product therefore belongs in the installation
  guide as prose.** `REQ` stays right for a genuinely fixed co-requisite that will
  not move.

## Two side findings from the same probe

- A `++FUNCTION` with no elements is received without complaint:
  `HMA3971 … HAS NO ELEMENTS` is a warning and `HMA3930 SUCCESSFULLY RECEIVED`
  follows. A requisite test therefore needs no throwaway module names, because the
  APPLY CHECK fails long before elements matter. `[tested]`
- `REJECT` cleans a received-but-never-applied id out of the inventory (`HMA2270`,
  then `LIST` reports RC 04 not found). The id is still spent: it was received
  once and must not be reused as a released id. `[tested]` for the cleanup,
  convention for the spent id (`ECO-0007`).
