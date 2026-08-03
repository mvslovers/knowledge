---
id: ECO-0001
title: Runtime self-authorization instead of APF library authorization
status: assumed
platform: [mvs38j]
sources:
  - "Mike Großmann, 2026-07-27 — statement of intent"
  - "libc370/src/clib/@@autask.c, @@uatask.c, @@apfset.c"
  - "nsf370/m5-stage0a-ssi-probe.md:35-40, 72-74 — live run on MVSCE"
verified_on: 2026-07-27
applies_to: [libc370, ufsd, httpd, mvsmf, nsf370]
tags: [apf, authorization, svc244, portability]
related: [CF-2026-001]
---

## Context

The classic MVS path to running authorized has three requirements, all of which
must hold at once: the load library is listed in `SYS1.PARMLIB(IEAAPF0x)`, the
module is link-edited `AC(1)`, and it is entered as the job step program. Any one
missing and the program runs unauthorized. Changing `IEAAPF0x` requires an IPL.

Our servers need authorization for `IEFSSREQ`, for key-0 work in the caller's
address space, and for cross-address-space `POST` via the `CVT0PT01` branch entry.
Requiring every user of the ecosystem to edit their parmlib and re-IPL in order to
install one of our components was judged unacceptable.

## Decision

We bypass the APF mechanism entirely. Programs authorize themselves at run time
through **SVC 244**, driven by libc370, and never rely on their load library being
APF-authorized.

This is a deliberate circumvention of the control MVS provides for exactly this
purpose. It is acceptable here because our target systems are single-user emulated
installations with no security boundary to defend. It is **not** a pattern to carry
to z/OS, where SVC 244 does not exist and where this would be an integrity
violation.

## Mechanism

`clib_apf_setup(pgm)` is the entry point callers use. It drives, in order:

- `__autask()` — `TESTAUTH FCTN=1`, then SVC 244 to authorize, then a second
  `TESTAUTH FCTN=1`, then records `CRTAUTH_ON` in `crt->crtauth`
- `__austep()` — authorizes the STEPLIB
- `clib_auth_name(pgm)` and `clib_auth_name("CTHREAD")`

`__uatask()` is the inverse and drops authorization. Call `clib_apf_setup()` early.
No `IEAAPFxx` change and no IPL are required.

## Consequences

- **The whole ecosystem depends on SVC 244 being present on the target system.**
  This is why the document is `assumed` rather than `tested`: SVC 244 lies in the
  user-SVC range, which is installation-defined by definition — there is no "always
  present" for it in stock MVS 3.8j. Confirmed on MVSCE only. TK4- and TK5 are
  unverified. The origin is unrecorded; it may be shipped by the distributions, or
  it may have been installed by us via USERMOD long enough ago that it reads as a
  system property.
- Nothing currently detects a missing SVC 244 or reports it usefully. On a system
  without it, `clib_apf_setup()` will fail in whatever way an unassigned SVC fails,
  which is a poor first contact with our stack for a community user. The abend that
  appears there is itself worth documenting once observed.
- `AC(1)` on our load modules confers nothing on its own, since it takes effect only
  when the module is loaded from an APF-authorized library as the job step program.
  Where `AC(1)` still appears in a build, it is either vestigial or evidence that
  some target system does authorize the library — see `CF-2026-001`.
- Documentation and community material must not tell users to add libraries to
  `IEAAPF0x`. That instruction would be harmless but would misdescribe how the
  system actually works.

## To promote this to `tested`

Run a program that issues SVC 244 on each target distribution — MVSCE, TK4-, TK5 —
and record both the success and, where it fails, the exact abend. Then record where
the SVC comes from.
