---
id: ECO-0022
title: mvsMF restjobs — the owner is a client-set display filter, any authenticated user can read or purge any job; cancel answers 404
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 (VER 3.8J REL P6.2007.JAN.01) throwaway containers, 2026-10-21 (container-local), two users per system, curl with HTTP Basic authentication; mvsMF 1.3.0. TK5: a job purged by a normal user through GET/DELETE restjobs: HTTP 200 (container-local JOB number)"
  - "mvslovers/mvsmf tag v1.3.0 (commit d454edf, 2026-10-15): src/jobsapi.c (list handler owner default and `*`, should_skip_job, purge handler: jescanj, ERR_MSG_STC_PURGE), include/jobsapi_msg.h, docs/endpoints/jobs/purge.md, docs/endpoints/auth/authenticate.md"
  - "mvslovers/mvsmf#345 (open): restjobs has no authorization model; mirror of mvslovers/ftpd#90"
verified_on: 2026-10-21
applies_to: [mvsmf]
tags: [mvsmf, restjobs, zosmf, jes, spool, authorization, owner, purge, mvsmf-345]
related: [MVS-SEC-0003, MVS-SEC-0005, MVS-JES2-0001, MVS-JES2-0002, ECO-0020, ECO-0021]
---

## The claims

mvsMF 1.3.0 (tag `v1.3.0`, commit `d454edf`) is the released version; the measurements ran against it.

- **The default job list is filtered by the owner, which is the HTTP userid.** `GET
  /zosmf/restjobs/jobs` without `owner` uses `http_get_userid()` of the request; `owner=*` clears the
  filter and lists every job. The filter is a display filter: the client chooses it. `[tested]` `[source:
  src/jobsapi.c list handler]`
- **The owner compare is a prefix compare over the shorter of the two strings.** `should_skip_job()`
  uses `strncmp(job->owner, owner, MIN(strlen(job->owner), strlen(owner)))`, so an owner that is a prefix of
  the requested one, or the other way round, matches; a job with an empty owner never matches a given owner
  (MVS-JES2-0002). `[source: src/jobsapi.c should_skip_job]`
- **`files`, `records`, status and `DELETE` (purge) work for any authenticated user on any job:** HTTP 200.
  The by-jobid paths do not look at the owner. `[tested]` (a normal user purged a job of another user on
  TK5: 200). The purge handler calls `jescanj(jobname, jobid, 1)` after looking the job up. `[source:
  src/jobsapi.c purge handler]`; the repository's own `docs/endpoints/jobs/purge.md` says: "The purge
  handler authorizes nothing (#345)".
- **`DELETE` of an active started task is refused:** `400 Cannot purge a started task`
  (`ERR_MSG_STC_PURGE`, reason 5). That is a rule about the job type, not an authorization check.
  `[tested]` `[source: include/jobsapi_msg.h]`
- **`PUT {"request":"cancel"}` answers 404** with `{"rc":4,"category":6,"reason":7,"message":"Not Found"}`.
  The inbox note adds that hold and release are not implemented; only cancel was run, and no handler for
  these requests was found by searching the v1.3.0 sources for `cancel` and `hold`. `[tested]` for the cancel
  404 only.
- **Authentication is Basic or a token cookie.** The measurements used HTTP Basic; the v1.3.0
  documentation (`docs/endpoints/auth/authenticate.md`) also describes a login that returns an
  `LtpaToken2` cookie. Either way the identity is the RACF-canonical userid from the ACEE; nothing
  after that checks it against the job. `[source: docs/endpoints/auth/authenticate.md; src/jobsapi.c
  comment on http_get_userid]`

## The evidence

Per system and user, twelve jobs (IEBGENER, TYPRUN=HOLD for the waiting ones; names with and without the
userid prefix, owner and name prefix crossed). Results as above: list with `owner=*`, `files`, `records` and
`DELETE` on a foreign job answer 200 for a normal user; the default list shows only the caller's jobs; cancel
answers 404; the active STC answers 400.

The same gap in FTPD: ECO-0021. TSO, in contrast, checks the job-name prefix and the UADS OPER flag
(MVS-SEC-0003).

## Limits

- Container results, not a stand. The MVS/CE image has the products copied in; TK5 has them SMP-installed
  (ECO-0007).
- Waiting jobs were modelled with TYPRUN=HOLD; no truly running batch job was used.
- Hold and release were not run against mvsMF; the source search for a handler is negative, not proof.
