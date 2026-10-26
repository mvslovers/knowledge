---
id: MVS-SEC-0005
title: JESSPOOL entities are cut to 8 characters; generic profiles match by prefix, star-less profiles differ by RAKF build
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers (RAKF built into the images) and an MVS/CE container with RAKF 2.0.0 (release deck, CLPA IPL), 2026-10-21; probe: AC(1) program, libc370 2.25.1, racf_login without password then racf_auth READ/UPDATE/ALTER; job output is container-local and not kept"
  - "RAKF v2.0.0 (commit 019acf4), SRCLIB/CJYRCVT.hlasm (CDT, line 'DC AL1(8),CL8''JESSPOOL''', added in commit 0edc3d3, 2026-10-21); SRCLIB/CJYRPROF.hlasm (TRT over max-length+1 bytes, labels TRT/BRANCTBL/ASTRKFND/BLANKFND); SRCLIB/ICHSFR00.hlasm ENTYCLLP/ENTYENFN (CLC RPEENTYN(0),0(ENTYREG))"
  - "Rob Prins (RAKF maintainer), 2026-10-22, reply to the measurements (his statements, not measured by us)"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf]
tags: [rakf, jesspool, entity, generic-profile, prefix, cdt, jes2, security]
related: [MVS-SEC-0004, MVS-SEC-0006, MVS-SEC-0010, ECO-0021, ECO-0022, MVS-SEC-0008, MVS-JES2-0001]
---

## The claims

- **A JESSPOOL profile entity is capped at 8 characters**; the checked entity is compared on its first
  8 characters. The cap is the length byte of the class in the class descriptor table
  (`DC AL1(8),CL8'JESSPOOL'`), not a property of the profile text. `[tested]` on the image RAKF
  and on 2.0.0; `[source: RAKF v2.0.0 CJYRCVT CDT]`. The CDT lengths for the other classes: FACILITY 39,
  DATASET 44, DASDVOL and TAPEVOL 6, everything else 8 (`[source]`; the image loader uses the same fixed
  lengths, MVS-SEC-0010).
- **A star within the first 9 characters of the profile entity cuts the prefix there**, star excluded.
  `[tested]` `[source: CJYRPROF searches entity bytes 1..max+1 for blank or star; the one-byte
  correction for the star is commented out]`
  - `ZQUSR1.*` matches `ZQUSR1.` and `ZQUSR1.…`, not `ZQUSR1`, not `ZQUSR1X`.
  - `LOCAL.*` matches `LOCAL.…`, not `LOCAL`, not `LOCALX.A`.
  - `ZQUSR2*` matches `ZQUSR2X…`. `ZQUSR123.*` is cut to `ZQUSR123`.
  - `ABC.PROD*` UPDATE: RC 0 for `ABC.PRODX.JOB00001`, RC 8 for `ABC.TESTX.JOB00002` and `ABC.PRO`.
- **Consequence for a resource name `<owner>.<jobname>.<jobid>`: only the first 8 characters can
  discriminate.** `[tested]` The profile `LOCAL.IBMUSER` (also written `LOCAL.IBMUSER.*` or `LOCAL.*`)
  becomes `LOCAL.IB` and matches `LOCAL.IBMUSER.JOBA.JOB00012`, `LOCAL.IBMUSERX.JOBA.JOB00013`,
  `LOCAL.IBMUSE`, `LOCAL.IB`, `LOCAL.IBM.X`; it does not match `LOCAL.I` or `LOCAL.ZZ`.
  - A node prefix of several characters eats the budget and cannot separate owners.
  - With the owner first, `OWNER.*` works for userids up to 7 characters: `ABCDEFG.*` matches
    `ABCDEFG.J.JOB00001`. `ABCDEFGH.*` is cut to `ABCDEFGH` and matches every entity starting with
    those 8 characters. Owner, jobname and job id cannot be told apart beyond the cap.
  - `ABC.*` matches `ABC.JOBA.JOB00012` but not `ABCD.JOBA.JOB00012`.
  - An 8-character userid: `ABCDEFGH.*` and `ABCDEFGH` decide alike.
- **A profile without a star differs by build.** `[tested]`
  - **Image RAKF (older build):** discrete match of the first 8 characters, blank padded. `SHORT`
    does not match `SHORT.A`; `ZQUSR123` matches `ZQUSR123.A` but not `ZQUSR124`.
  - **RAKF 2.0.0:** **prefix** up to the first blank (or star). With `ABC` UPDATE and `ABCD` READ,
    `ABC.JOBA.JOB00012` gives R0/U0/A8 on 2.0.0 and RC 8 on the image RAKF.
    `[source: CJYRPROF BLANKFND: length = position of the first blank; the length is applied to
    every class]`
- **What the RAKF maintainer says (his statements):** a prefix match for a profile without a star
  is meant only for the class DATASET, so the star-less prefix in JESSPOOL on 2.0.0 is probably a
  RAKF defect; write `OWNER.*` in other classes and do not rely on star-less profiles there.
  `MIKE1.*` is a valid generic profile in JESSPOOL; the entity length is limited to 8 (IBM allows
  246, too long for RAKF). `[attributed, not measured]`
- Entities containing characters outside `[A-Z0-9$#@]` (blank, a leading star, lowercase, `-`, `*`,
  `.`, `A.B.C`) all fall to the `*` NONE profile with RC 8 and no special return code. `[tested]`
  The entities `X..` and `X.` match `X.*`, while `..` matches only `*` (RC 8). `[tested]`

## The evidence

Match rows measured on 2.0.0 and on the image RAKF (identical for starred profiles), user with
permit UPDATE on `ABC.PROD*`:

```
entity               result
ABC.PRODX.JOB00001   RC 0
ABC.TESTX.JOB00002   RC 8
ABC.PRO              RC 8
```

Ordering when several profiles match the same entity is MVS-SEC-0006; what happens at RC 8/4 is
MVS-SEC-0004.
