---
id: ECO-0008
title: RAKF gives every started task the same identity, and grants ALTER to everything it does not know
status: tested
platform: [mvs38j]
sources:
  - "RAKF/README.md — User's Guide, sections 'Users and Profiles Tables', 'Batch Jobs and Started Task Considerations', 'PROFILES table'"
  - "RAKF/PROCLIB/RAKF.jcl — the started task (PGM=ICHSEC00)"
  - "RAKF/SRCLIB/ICHSFR00.hlasm — the hardcoded STC identity, quoted in mvslovers/ftpd#97"
  - "ftpd/src/ftpd.c:196-217 — the startup RACINIT that drops out of it"
  - "ftpd/doc/FTPD_RAKF_SETUP.md — the FTPD-specific setup written from these findings"
  - "TK5 system, 2026-08-14 — FTPD004I, RAKFUIDS2 and the group-connection test"
verified_on: 2026-08-14
verified_platforms: ["TK5"]
applies_to: [ftpd, httpd, mvsmf, libc370]
tags: [rakf, racf, security, authorization, acee, racinit, stc, identity]
related: [ECO-0001, ECO-0007]
---

## Context

Every server we ship runs as a started task on a system whose security is RAKF,
and each of them has had to answer the same three questions independently:
what identity does the address space have when nobody set one, what does RAKF
say when no profile covers a resource, and how does an administrator actually
enter the definitions. The answers are the same for all of them and are not
obvious from either the RACF documentation RAKF emulates or from RAKF's own
guide, which is why they are recorded here rather than per project.

**The deployed baseline is RAKF 1.2.6** (October 2021) — what TK4-, TK5 and
MVS/CE ship. RAKF 2.0.0 (August 2026) changes the password model in a way that
breaks assumptions below; see *Version boundary*.

## Every started task has the same identity, and it is powerful

RAKF has **no started-procedures table**. `ICHSFR00` decides only *that* a
caller is an STC, never *which* one, and answers with one hardcoded pair:

```hlasm
STCUID   DC    AL4(0),X'03',CL8'STC',X'08',C'STCGROUP'
```

| Type | USERID | GROUP |
|------|--------|-------|
| Batch jobs | `PROD` | `PRDGROUP` |
| Started tasks | `STC` | `STCGROUP` |

The `STC` userid carries **Operations authority, hardcoded** — "always allow
access unless explicitly denied by a rule". Combined with the
`DATASET * STCGROUP ALTER` entry that stock profile tables carry, a started
task that does nothing about its identity can reach every data set on the
system. Adding `USER=` to the PROC does not change it: that RACINIT path
consults nothing.

**The mitigation is one call at startup.** Log on to a low-privilege userid and
install the ACEE address-space-wide:

```c
ACEE *stc = racf_login("FTPD", NULL, "USER", &rc);   /* pass NULL => PASSCHK=NO */
if (stc) racf_set_acee(stc);
```

FTPD does this (`src/ftpd.c:196-217`); HTTPD has the same finding as
`mvslovers/httpd#177`. The identity it lands on **must not have Operations
authority** — column 28 of its users-table line must be `N`, or the switch
achieves nothing.

**`RAKF0010I STC <name> STARTED USING DEFAULT STC ACCOUNT` does not tell you
the resting identity.** RAKF issues it when the started task is created, before
the server's own code runs. It reports the initial assignment only. The server's
own message after its RACINIT is the reliable indicator — for FTPD, `FTPD004I`
against `FTPD004W`.

## What was measured

**The requested group wins; RAKF does not check the connection** (TK5,
2026-08-14). With `FTPD` carrying group `FTPD` in the users table and the code
requesting `USER`, the resulting ACEE was `FTPD/USER`. A configured group
naming a group the userid is not connected to will therefore be accepted
silently — RAKF will not validate our configuration for us.

**A blank password is rejected** (same system). RAKF 1.2.x refuses the users
line and terminates the load:

```
RAKFUIDS2  INPUT DATA INVALID OR OUT OF SEQ.
FTPD     FTPD     ******** N                                            00000706
RAKFUIDSX  ** PROGRAM TERMINATED **
```

Two things make this expensive to diagnose. The echoed card **always** prints
the password column as `********`, whether it was set or empty — so the field
that caused the rejection is the one the diagnostic will not show. And nothing
is updated: the in-core table keeps its previous contents, which presents as
"my change had no effect" rather than as a failure.

The consequence for us is not the inconvenience. It is that **the service's own
userid necessarily carries a real password and is therefore a login-able
account** through whatever front door the service offers. It must be excluded
from the service's own authorization gate — for FTPD, not permitted on
`FTPAUTH`.

## RAKF grants ALTER to resources it does not know

> *"it is RAKF's standard behavior to grant ALTER access requested for an
> undefined resource"* — RAKF User's Guide

This is the single most consequential difference from the RACF mental model,
and it runs the wrong way from every intuition about defaults. **"No profile"
does not mean closed, it means wide open** — and at `ALTER`, not at `READ`.
The guide's own example is that a user can scratch any file on any volume as
long as no `DASDVOL` profile exists.

For our services, which all call `racf_auth()` and act on the SAF return code:

| RC | Meaning | What a service must do |
|----|---------|------------------------|
| 0 | a profile permits the access | allow |
| 4 | no profile covers the resource | **allow** |
| 8 | a profile refuses the access | deny |

RC 4 is an allow. Data set OPEN, IDCAMS and the catalog all act on it that way,
so a service that treated it as a refusal would become the only path on the
system unable to reach an unprotected data set. FTPD settled this in
`mvslovers/ftpd#82`.

The corollary belongs in every installation guide we write: a facility profile
that protects one of our services is **not optional**. Leaving it undefined is
not a permissive default an administrator chose, it is an open door — and it
also lets the service's own account in through the front.

## Administration is by hand, and the tables are fragile

On 1.2.x there is **no administration tooling**. Both tables are plain
80-column, column-positioned members that an administrator edits directly:

```
SYS1.SECURE.CNTL(USERS)     userid 1-8, group 10-17, '*' 18, password 19-26,
                            Operations 28, comment 31-50
SYS1.SECURE.CNTL(PROFILES)  class 1-8, resource 9-52, group 53-60 (blank =
                            universal), permission 61-66
```

Some distributions add a `RAKFCL` command processor that wraps this in
RACF-like syntax. **It is a distribution extension, not part of RAKF** — MVS/CE
has it, TK4-/TK5 do not. Our documentation must not depend on it, and must not
show RACF command syntax as if it were a table line.

Three properties that bite:

- **Both tables must be in ascending sort order.** A sort error does not skip
  the bad line, it inhibits initialization of the table — one misplaced entry
  takes down authorization for the whole system, not just for the service that
  needed it.
- **The universal entry (blank group) must precede** the group-specific ones,
  because the table is searched from the bottom upwards so the most specific
  hit wins.
- **Reload is `S RAKF`**, on every system, after any change to either member.
  There is no MODIFY command; RAKF reads the tables when it starts. The
  `RAKFUSER`/`RAKFPROF` procedures in the RAKF distribution are not the path on
  an installed system.

## Version boundary

| | RAKF 1.2.x (deployed) | RAKF 2.0.0 (August 2026) |
|---|---|---|
| Password in `USERS` cols 19-26 | **required** | **blank** |
| Credential | in the users table | salted SHA-256 in `SYS1.SECURE.SHADOW` |
| Administration | by hand | `ADDUSER` / `ALTUSER` in `SYS2.CMDLIB` |

A guide written against the wrong one fails in both directions: a blank
password is rejected on 1.2.x, and a filled one points at nothing on 2.0.0.
State the baseline explicitly in anything we publish.

## Consequences

- **Every STC we ship needs its own userid, its own group, and Operations `N`.**
  A service that skips the startup RACINIT runs with ALTER on every data set,
  and nothing in its log says so.
- **The identity a service switches to must stay least-privilege**, not as
  hygiene but because recovery paths reset `ASXBSENV` to it. While it is
  minimal, a session transiently pulled onto it can only lose authority; give
  it broad authority and the same switch becomes fail-open. See
  `mvslovers/ftpd#64`.
- **The userid and group belong in configuration, not in a string literal.**
  FTPD currently hardcodes `racf_login("FTPD", NULL, "USER", ...)`; the
  keywords are tracked in `mvslovers/ftpd#97`.
- **RAKF's inventory says nothing about SVC 244**, and vice versa — see
  `ECO-0001` for why RAKF cannot be named as an SMP prerequisite, and
  `ECO-0007` for the delivery side.

## Open

- Whether `PROD`/`PRDGROUP` deserves the same treatment for anything we ship
  that runs as a batch job. No product needs it yet.
- Whether a started-procedures table lands upstream in RAKF, which would remove
  the need for the startup RACINIT entirely. Drafted per `mvslovers/ftpd#97`;
  the mitigation should not wait for it.
- TK4- is unverified for all of the above. Only TK5 was measured.
