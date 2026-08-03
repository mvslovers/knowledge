---
id: ECO-0004
title: Cross-address-space POST and WAIT on MVS 3.8j
status: source
platform: [mvs38j]
sources:
  - "libc370/src/clib/@@xmpost.c — the CVT0PT01 branch entry and its register contract"
  - "libc370/src/clib/@@ecbpst.s:21 — ecb_post issues the plain POST macro form"
  - "libc370/sysmac/post.macro — the MVS 3.8j POST macro prototype and its .XMPOST path"
  - "ufsd/docs/cross-as-reference.md — five abends, symptom / root cause / fix, observed under Hercules"
  - "ufsd/src/ufsd#ssi.c, ufsd#que.c — the working design"
  - "ufsd commit 23dbb73 — AP-1b + AP-1c, where the rules were established"
verified_on: 2026-08-01
applies_to: [ufsd, libc370, nsf370, mvsmf]
tags: [post, wait, ecb, cross-address-space, ssi, cvt0pt01, xmpost, storage-key, s102, s202, x201, s047]
related: [ECO-0005]
---

## The rule

Cross-address-space POST goes through the **POST branch entry addressed by
`CVT0PT01`**, issued from supervisor state, key 0. That is what libc370's
`__xmpost(ascb, ecb, postcode)` does. The reply WAIT is the ordinary `WAIT`
(SVC 1) from **problem** state, on an ECB in **key-8** storage.

## Three POST paths exist on 3.8j. Know which is which.

| Path | What it generates | Status here |
|---|---|---|
| `POST (ecb),(code)` — plain form | `LA 1,ECB` then `SVC 2` | `[tested]` fails cross-AS: **S102** from problem state, **S202** from supervisor state |
| `POST ecb,code,ASCB=,ERRET=[,ECBKEY=]` — XMPOST form | 3- or 4-word parameter list (ECB / ASCB / ERRET / ECBKEY), high-order bit on in R1, then `SVC 2` | **never tried in this ecosystem** — see the gap note below |
| `__xmpost()` → `CVT0PT01` branch entry | `L 15,CVTPTR` / `L 15,CVT0PT01-CVTMAP(,15)` / `BALR 14,15` | `[tested]` works, supervisor state / key 0 |

The XMPOST form **does exist on MVS 3.8j**. `libc370/sysmac/post.macro:3` reads:

```
&LABEL   POST   &ECB,&CODE,&ASCB=,&ECBKEY=,&ERRET=,&MF=I,&RELATED=
```

`ECBKEY=` arrived by APAR `@ZA15373`. The `.XMPOST` path builds the parameter list
and falls through to `.SVC` at line 230, which is `SVC 2`. `[source: post.macro]`

What the macro does **not** have is `LINKAGE=`. That keyword is MVS/XA and later;
there are 0 occurrences in the 3.8j macro. An answer that codes `LINKAGE=BRANCH` is
describing a different release. See **ECO-0005**.

**Gap.** Whether the XMPOST form works on 3.8j is unknown. ufsd measured the *plain*
form (`ecb_post`, `@@ecbpst.s:21` is `POST (3),(2)` — no `ASCB=`) and went straight to
the branch entry. Abend 4's own root cause says SVC 2 fails cross-AS from problem
state "**without special cross-memory authority**" — which is exactly what the XMPOST
parameter list supplies. Settling this is a cheap experiment: a small assembler
program issuing `POST ecb,0,ASCB=,ERRET=` from supervisor state against a waiting STC.

## `__xmpost` register contract

`[source: libc370/src/clib/@@xmpost.c]`

| Register | Contents |
|---|---|
| R13 | ASCB address of the **target** address space |
| R11 | ECB address, high-order bit forced on |
| R10 | post code, `(code \| 0x40000000) & 0x7FFFFFFF` |
| R12 | ERRET routine address |
| R15 | `CVT0PT01` from `CVTPTR`, then `BALR 14,15` |

**Only R13 is preserved across the call.** `@@xmpost.c` saves it in R9 before the
BALR and restores from there afterwards; everything else must be reloaded. The
routine issues no SVC 2 at any point.

## The working design (ufsd AP-1c)

| Operation | Mechanism | State | ECB location |
|---|---|---|---|
| router wakes the STC | `__xmpost(anchor->server_ascb, &anchor->server_ecb, 0)` | supervisor | `anchor->server_ecb`, CSA, key 0 |
| router WAITs for the reply | `ecb_timed_wait(&local_ecb, …)` | **problem** | `local_ecb`, **stack local in the router**, key 8 |
| STC wakes the client | `__xmpost(req->client_ascb, req->client_ecb_ptr, 0)` | supervisor | the router's stack local |

`server_ascb` is captured at STC startup via `__ascb(0)`; `req->client_ascb` in the
router, likewise via `__ascb(0)`. `[source: ufsd#ssi.c]`

**The client's reply ECB must not live in CSA.** It is a local stack variable in the
router's own frame, and only a pointer to it is handed to the server. That is both a
storage-key requirement (below) and a lifetime one — CSA is freed and reused, a stack
frame is not.

## The five abends, and what each one teaches

`[tested: ufsd AP-1c, Hercules / TK4-, dump analysis; ufsd/docs/cross-as-reference.md]`

1. **S047 — WAIT protection error.** The router WAITed on `anchor->server_ecb` (CSA,
   key 0). An unauthorized task cannot WAIT on a key-0 ECB. → use a key-8 ECB.
2. **S0C4 at router entry.** libc370's `iefssreq` passes **R1 = SSOB address**, the MVS
   SSI convention; the C calling convention expects R1 = pointer to a parameter list.
   Declaring `ufsdssir(SSOB *ssob)` dereferenced the raw SSOB. → declare
   `void ufsdssir(void)` and extract with `__asm__("LR %0,1")`.
3. **S202 — SVC 2 POST from supervisor state.** `ecb_post` inside a `__super`/`__prob`
   window. The plain POST is not permitted from supervisor state.
4. **S102 — plain SVC 2 POST cross-AS from problem state.** Both directions. → replaced
   by `__xmpost` in both places.
5. **X'201' — WAIT on a key-0 ECB from problem state.** The ECB sat inside a UFSREQ
   block in CSA (SP=241, key 0). PSW at abend: problem state, key 8. → move the ECB to
   a key-8 stack local.

Abends 1 and 5 are the same rule from two directions: **the storage key of the ECB
must match the state the waiter is in.** The STC waits in supervisor state on a key-0
CSA ECB and that is fine; the client waits in problem state and needs key 8.

## The WAIT evolved; the state and key rules did not

The plain blocking `WAIT` was later replaced by a timed, liveness-checked loop:
`ecb_timed_wait(ecbp, UFSD_WAIT_INTERVAL, UFSD_TIMEOUT_CODE)` with
`UFSD_WAIT_INTERVAL` = 500 hundredths (5 s) and `UFSD_TIMEOUT_CODE` = X'0FFFF' as a
sentinel post code, distinct from the STC's normal reply code 0. Still a key-8 local
ECB, still problem state — only SVC 1 became a timed `STIMER` + `WAIT`.

On a timer pop the router revalidates the anchor eyecatcher (`memcmp(anchor->eye,
"UFSDANCR", 8)`) **before** re-testing `UFSD_ANCHOR_ACTIVE`, because freed CSA (SP=241)
is reused rather than zeroed and a stale flag alone would loop forever on an ECB
nobody will post. `[source: ufsd#ssi.c]`

An in-flight counter (`anchor->inflight`, key-0 CSA) is incremented inside the entry
key-0 window and decremented on every exit path; shutdown drains it to zero before
freeing the router module and the CSA pools, so CSA is never freed under a request
still copying its result.

## Whether these timings are contractual is not recorded

`UFSD_WAIT_INTERVAL`, `UFSD_TIMEOUT_CODE` and the `2 *` drain wait in `ufsdclnp.c` are
not documented as tuned, derived or arbitrary, and it is not stated whether an
independent client implementation must match them. `[assumed]` — see gap G-4 in
`benchmark/questions.md`.
