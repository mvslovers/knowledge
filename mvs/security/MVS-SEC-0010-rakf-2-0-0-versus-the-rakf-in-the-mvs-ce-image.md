---
id: MVS-SEC-0010
title: RAKF 2.0.0 versus the older RAKF in the MVS/CE image: same banner, different behaviour
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers, 2026-10-21: ICHSFR00 from SYS1.LPALIB fetched in binary and searched for message texts; AC(1) probe, libc370 2.25.1; the same 600 racf_auth checks against the image RAKF and against RAKF 2.0.0 installed from the TRKF200 release deck with a CLPA IPL"
  - "MVS/CE container built from an image that ships RAKF 2.0.0 (mvslovers/mvs-docker#27), 2026-10-22: undefined class gives RC 8 + RAKF0012"
  - "mvslovers/mvs-docker#27 (PR text): mainframed767/mvsce:3.0.0 ships an older RAKF under the same FMID (TRKF200) and the same banner (RAKF V2R0M0) as RAKF 2.0.0; only the content tells them apart"
  - "RAKF v2.0.0 (commit 019acf4, release published 2026-10-21): SRCLIB/CJYRCVT.hlasm CDT; SRCLIB/ICHSFR00.hlasm ENTYCLLP, WTOUNKN; SRCLIB/CJYRPROF.hlasm RACSTAT block (commit 0edc3d3, 2026-10-21, added JESSPOOL to the CDT)"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf, httpd]
tags: [rakf, rakf-2.0.0, trkf200, cdt, jesspool, undefined-class, rakf0012, build, security]
related: [MVS-SEC-0004, MVS-SEC-0005, MVS-SEC-0009, MVS-SEC-0011, MVS-SEC-0012, ECO-0008, ECO-0020, MVS-SEC-0008, MVS-VSAM-0002]
---

## Terms used in the security documents

- **Image RAKF**: the RAKF built into the MVS/CE image (banner `RAKF V2R0M0`, FMID TRKF200, but an older
  build than the release); the TK5 image carries RAKF 1.2.x, and both behaved alike in the checks of
  MVS-SEC-0004 to MVS-SEC-0007.
- **RAKF 2.0.0**: the release deck of tag `v2.0.0` (commit `019acf4`, release published 2026-10-21),
  installed with SMP4 and a CLPA IPL (MVS-SEC-0011). The 2026-10-21 container runs used the TRKF200 release
  deck of that day and were verified by content (below), not by version string; the 2026-10-22 run used an
  image that ships it.

## The claims

- **The banner and the FMID do not tell the builds apart.** Both print `RAKF V2R0M0` and carry
  `TRKF200`. Check the content: `[tested]`
  - `ICHSFR00` of the image RAKF contains RAKF0005/0007/0008/000B but neither `UNDEFINED CLASS` nor
    RAKF0012; RAKF 2.0.0 contains both.
  - The CDT in `ICHSEC00` (CJYRCVT) of 2.0.0 carries `X'08' JESSPOOL`
    (length byte 8; FACILITY X'27', DATASET X'2C', APPL X'08').
  - Behaviour: `racf_auth` on a class that nobody defined (`NOSUCHCL`) gives RC 4 on the image RAKF and
    RC 8 on 2.0.0.
- **Undefined class.** Image RAKF: the loader has fixed per-class entity lengths (FACILITY 39, DATASET 44,
  DASDVOL 6, every other class name, JESSPOOL and an invented `ZQUNKWN` included, 8); a class nobody defined is
  not an error and profile lines with that class are all it takes to "create" it. Without any JESSPOOL line the
  check returns 4, no message. `[tested]` RAKF 2.0.0: a class not in the CDT returns **RC 8** and the console
  message `RAKF0012 UNDEFINED CLASS NOSUCHCL`, three messages per READ/UPDATE/ALTER probe, **not suppressed by
  `racf_auth`** (whose LOG=NONE flag silences RAKF0005/000A/000B, ECO-0020). `[tested]`
  `[source: ICHSFR00 ENTYCLLP calls RACSTAT (RCVTREXP in CJYRCVT); a non-zero return goes to WTOUNKN and
  AUTHFAIL; WTOUNKN does not look at WORKNLOG]` An *empty* class (in the CDT, no profiles) is RC 4 on
  2.0.0. `[tested]` JESSPOOL itself was not removed from the CDT to test it; "no JESSPOOL in the CDT gives
  RC 8 + RAKF0012" is `[source]` only.
- **JESSPOOL is in the 2.0.0 CDT** with entity length 8, the same value the image loader falls back to,
  so the 8-character cap is the same on both. `[source: commit 0edc3d3]` `[tested]` (MVS-SEC-0005)
- **A profile without a star** matches by prefix on 2.0.0 and discretely on the image RAKF
  (MVS-SEC-0005). `[tested]`
- **The cold-start behaviour with invalid tables is different** (MVS-SEC-0011) and so is **the
  STC user and group handling** (MVS-SEC-0012). `[tested]`
- **Everything else measured in the 600-check comparison was identical**: levels via user, group and UACC;
  multi-group users; the 8-character cap on profile and checked entity; the ordering rule (MVS-SEC-0006); no
  bypass for ACEEOPER (MVS-SEC-0007); no console message on a `racf_auth` denial; effect of `S RAKFPROF` in a
  running process; U0300/U0400/U0500 at reload with the old chain kept (MVS-SEC-0009). `[tested]`

## The evidence

Of 600 checks (4 profile phases x 150 checks; phase A no JESSPOOL profiles, B only `*` UACC NONE, C 64 test
profiles, D C + `*` NONE), 4 differed: one check, four phases.

| Check | image RAKF | RAKF 2.0.0 |
|---|---|---|
| `racf_auth` class not in the CDT (`NOSUCHCL`) | RC 4 (R/U/A) | **RC 8** (R/U/A), `RAKF0012 UNDEFINED CLASS NOSUCHCL` |
| JESSPOOL without matching profile (phases A, C) | RC 4 | RC 4 |
| `*` UACC NONE (phases B, D) | RC 8 | RC 8 |

`RAKF0005`/`RAKF000A` did appear in the same log, but only for other callers: the started-task SVC244 check
and a batch DATASET check.

Verified-by-content at install (2026-10-21): installed `ICHSFR00` contains `UNDEFINED CLASS` / `RAKF0012`; installed
`ICHSEC00` carries the CDT entry `X'08' JESSPOOL`; IPL banner `RAKF V2R0M0 ... RCVT WAS PROCESSED SUCCESSFULLY`.

Not measured: a libc370 older than 2.25.1 (the `racf_auth` flag byte, ECO-0020, is a source fact for
those). Container results, not a stand.
