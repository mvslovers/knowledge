---
id: ECO-0005
title: MVS/XA-and-later services that MVS 3.8j does not have
status: myth
platform: [mvs38j]
sources:
  - "SRC-0001 — SYS1.MACLIB member list from the live MVS 3.8j system, 742 members, retrieved via zowe 2026-08-03 (sources/sys1-maclib-members-mvs38j.txt)"
  - "libc370/sysmac/post.macro — the 3.8j POST macro; no LINKAGE= keyword"
  - "knowledge/benchmark/results/2026-07-31-baseline.md §6.3 — 3 of 3 Q-01 answers built on absent services"
verified_on: 2026-08-03
applies_to: [ufsd, libc370, nsf370, httpd, mvsmf, rexx370]
tags: [mvs38j, macros, sys1-maclib, anachronism, srb, schedule, getmain, pc, linkage-index, name-token, resmgr, model-priors, myth]
related: [ECO-0004]
---

## The myth

Asked how to do authorized cross-address-space work on this system, a model designs
against the MVS/XA-and-later service set: schedule an SRB with `IEAMSCHD` and a
`TARGETSTOKEN`, validate the target with a STOKEN out of the ASSB, register cleanup
with `RESMGR`, escalate through a stacking PC built with `ETDEF`/`ETCRE`/`LXRES`/
`AXSET`, publish anchors with `IEANTRT` name/token pairs, obtain storage with
`STORAGE OBTAIN,SP=241,KEY=`.

In the 2026-07-31 without-KB baseline, **3 of 3** answers to the cross-AS question did
this. The designs were coherent and internally consistent. Not one of the services
they rest on exists here.

## The evidence

`SYS1.MACLIB` on the live 3.8j system holds **742 members**, catalogued as **SRC-0001**
and kept in this repo at `sources/sys1-maclib-members-mvs38j.txt`. Checked directly:

| Wanted | In SYS1.MACLIB | Use instead |
|---|---|---|
| `IEAMSCHD` — schedule an SRB | **absent** | `SCHEDULE` + `IHASRB` |
| `RESMGR` — resource manager | **absent** | ESTAE / task-level recovery; no RESMGR equivalent |
| `ETDEF` `ETCRE` `ETCON` `ETDES` — entry tables | **absent** | — no stacking PC |
| `AXSET` `AXRES` `AXEXT` — authorization index | **absent** | — |
| `LXRES` `LXFRE` — linkage index | **absent** | — |
| `PCLINK` | **absent** | — |
| `IEANTRT` `IEANTCR` — name/token pairs | **absent** | SSCT/SSVT, or a CSA anchor found through the SSI |
| `STORAGE` (OBTAIN/RELEASE) | **absent** | `GETMAIN` / `FREEMAIN` |
| `DSPSERV` `ALESERV` — data spaces, access lists | **absent** | — |
| `SYSEVENT` | **absent** | — |
| `POST` with `ASCB=` `ERRET=` `ECBKEY=` | **present** | exists — but see ECO-0004 |

Present and authorized, i.e. the set you actually have: `SCHEDULE`, `IHASRB`,
`SETLOCK`, `SETFRR`, `PURGEDQ`, `CIRB`, `SDUMP`, `MODESET`, `TESTAUTH`, `ESTAE`,
`SPIE`, `STIMER`, `ATTACH`, `IEFSSREQ`, `GETMAIN`, `FREEMAIN`, `POST`, `WAIT`,
`WAITR`, `EVENTS`.

`LINKAGE=` does not appear in the 3.8j `POST` macro at all — 0 occurrences.
`[source: libc370/sysmac/post.macro]`

### One caveat, and it matters

`CVT`, `IHAPSA` and `IHAASCB` are **also** absent from that member list — because on
MVS 3.8j the **mapping macros live in `SYS1.AMODGEN`, not in `SYS1.MACLIB`**.

So the list above is conclusive for *executable service* macros, which is what every
row of the table is. It is **not** conclusive for mapping macros. `IHAASSB` / `ASSB`
— the control block a STOKEN would be read from — is therefore **`[assumed]` absent,
not proven**, until the AMODGEN member list is checked.

Do not generalise "absent from SYS1.MACLIB" to "absent from the system" without
asking which kind of macro it is.

## Why the substitution happens

Public material on authorized MVS programming is overwhelmingly MVS/XA, ESA and z/OS.
The MVS/370 service set was superseded around 1983 and is barely represented. A model
reaching for "how do I do authorized cross-memory work on MVS" retrieves the later
answer because it is nearly the only answer in the corpus.

The failure is well-formed by construction: `IEAMSCHD` with `TARGETSTOKEN` really is
the right answer — on a system built after 1988. Nothing in the question's shape
signals which release is meant, so nothing suppresses it.

## What a correct answer looks like instead

For the ecosystem's own cross-AS pattern, see **ECO-0004**. In outline:

- Wake a task in another address space: the `CVT0PT01` POST branch entry from
  supervisor state, key 0 — not an SRB, not a PC.
- Serialize: `SETLOCK`, or compare-and-swap on a CSA field, not a lock service that
  does not exist.
- Publish an anchor: the SSCT/SSVT registered through the SSI, not a name/token pair.
- Obtain common storage: `GETMAIN` with an explicit subpool and key, not `STORAGE`.
- Clean up after a failure: an ESTAE that deregisters, because there is no RESMGR to
  fall back on. This is why ufsd documents its deregistering ESTAE as **mandatory** —
  an abend without it leaves the SSCT registered until IPL.

## How to check an answer in ten seconds

Take every macro name the answer uses and look it up in
`sources/sys1-maclib-members-mvs38j.txt` (SRC-0001). Any *service* macro that is not
there is not on this system. That test would have caught all three baseline answers.
