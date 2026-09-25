---
id: UFSD-ADR-0001
title: Session identity is supplied by the client via UFSREQ_SETUSER, never derived in the SSI router
status: source
platform: [mvs38j]
sources:
  - "ufsd commit 0b63fda — fix: remove racf_get_acee() from SESS_OPEN in SSI router. Fixes #10"
  - "ufsd/include/ufsd.h:329,331 — UFSREQ_SESS_OPEN 0x0010, UFSREQ_SETUSER 0x0012"
  - "ufsd/src/ufsd#ses.c:217 — 'Owner/group start empty — set by SETUSER after SESS_OPEN'"
  - "ufsd/src/ufsd#ses.c:276,285 — ufsd_sess_setuser(UFSD_ANCHOR *anchor, UFSREQ *req)"
  - "ufsd/client/libufs.c:273,287 — ufs_setuser(UFS *ufs, const char *userid, const char *group)"
  - "mvsmf/src/ussapi.c:115 — ufs_setuser(ufs, userid, group), the mvsMF side of the contract"
  - "libc370/src/racf/racgacee.c:13-14, racsacee.c:15-16,34,53 — ACEE **asxbsenv = (ACEE **) &asxb[0xC8/4]"
verified_on: 2026-08-04
applies_to: [ufsd, mvsmf, libc370]
tags: [ufsd, ssi, session, identity, racf, acee, asxbsenv, race-condition, s0c4, setuser, mvsmf, adr]
related: [ECO-0004]
---

## Decision

**The client tells ufsd which user a session belongs to. The SSI router never works it
out for itself.**

`UFSREQ_SESS_OPEN` (**0x0010**) creates the session with owner and group **empty**. The
client then issues a separate `UFSREQ_SETUSER` (**0x0012**) request to set them.
`[source: ufsd.h:329,331; ufsd#ses.c:217 "Owner/group start empty — set by SETUSER after
SESS_OPEN"]`

- Router side: `ufsd_sess_setuser(UFSD_ANCHOR *anchor, UFSREQ *req)` `[ufsd#ses.c:285]`
- Client side: `ufs_setuser(UFS *ufs, const char *userid, const char *group)` in libufs
  `[libufs.c:287]`
- Caller: mvsMF, `ufs_setuser(ufs, userid, group)` `[mvsmf/src/ussapi.c:115]`

**`racf_get_acee()` must not be called during SESS_OPEN.** That is the whole point of the
decision, and it was arrived at by removing code that did.

## Why not the caller's ACEE — the trap is that it looks legal

The SSI router runs in the caller's address space and under the caller's task. The
textbook MVS identity rule therefore appears to apply directly: find the ACEE via TCBSENV
if non-zero, otherwise ASXBSENV, and use it. That reasoning is fluent, well-formed, and it
is **exactly the design that was removed**.

The reason it fails is a lifetime problem that the MVS rule cannot show you:

> ASXBSENV is per-address-space and shared across all worker threads. Concurrent
> racf_login/racf_logout from parallel HTTP requests creates a race condition where
> `racf_get_acee()` returns a stale pointer, causing **S0C4 in ufsdssir** when accessing
> the freed ACEE.

`[source: ufsd commit 0b63fda]`

The pointer lives at **ASXB + X'C8'**, and libc370's get and set both go through it:

```c
ACEE **asxbsenv = (ACEE **) &asxb[0xC8/4];   /* A(ASXBSENV) */
```

`[source: racgacee.c:13-14 (get), racsacee.c:15-16 and :34,:53 (set)]`

**ASXBSENV is per address space, not per task.** That is the fact the whole failure turns
on. httpd serves parallel requests on multiple worker threads inside one address space;
every one of them reads and writes the same slot. A `racf_login` or `racf_logout` on any
other thread can replace or free the ACEE between the moment the router reads the pointer
and the moment it dereferences it.

## Why the client is the right source

It already knows. mvsMF authenticated the user before it ever opened the session — the
identity is not something the router has to rediscover, and rediscovering it is strictly
worse: it is racy, and it is a second source of truth for something that was already
established.

## What this decision is not

- **Not "the SESS_OPEN request carries the userid."** It does not. SESS_OPEN opens an
  anonymous session; identity arrives in a separate request afterwards. Two round trips,
  deliberately.
- **Not "ufsd does its own RACINIT/RACHECK."** It performs no independent verification to
  establish the session identity. It takes what the client sets.
- **Not a claim that ACEEs are unreachable.** `racf_get_acee()` still exists and still
  works. What was removed is its use *on the SESS_OPEN path in the router*, where the
  concurrency makes it unsafe.

## Trust boundary — worth stating explicitly

This design accepts identity from the caller. That is defensible here because the caller
is mvsMF running inside httpd's own address space, on the same system, having already
authenticated the user — but it *is* a trust relationship, and it should be named rather
than assumed. If a future client is not in that position, this contract does not by itself
authenticate anything. `[assumed]` — no document in the repos records the intended trust
model for a third-party client, and nsf370 is about to implement the protocol
independently.
