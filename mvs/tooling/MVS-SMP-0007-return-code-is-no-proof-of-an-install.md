---
id: MVS-SMP-0007
title: A condition code says whether a job ran, not whether the work happened — read the inventory (case in point: "^" mangled on the mvsMF job-submit path)
status: tested
platform: [mvs38j]
sources:
  - "Three independent cases met on 2026-09-14: NOT SEL install (MVS/CE system, JOB00291, mbt#98); upgrade whose STEPLIB was not re-pointed (MVS/CE system, ftpd#146 arm D, JOB00325); multi-line IDCAMS scratch submitted through the mvsMF REST API (TK5 system, as reported in the inbox note — no job number carried)"
  - "Addition 2026-10-26: fourth case, TK5 throwaway container, 2026-10-22 — FTPD 1.3.0 upgrade (TFTP130) whose XMIT upload failed; the install job pointed at the image's stale XMIT data sets (job numbers not carried over)"
  - "mvsmf src/jobsapi.c function submit_jcl_content, origin/main 5487621 — http_xlate(content, content_length, httpx->xlate_cp037->atoe)"
  - "httpd src/httpxlat.c, origin/main 52732cf — cp037_atoe[0x5E] = 0xB0; the IBM-1047 table maps 0x5E to 0x5F"
verified_on: 2026-09-14
verified_platforms: ["MVS/CE (3.0.0)", "TK5 Update 5"]
applies_to: [ufsd, ftpd, httpd, mvsmf, mbt]
tags: [smp, smp4, return-code, verification, idcams, mvsmf, encoding, cp037, idc4229i, not-sel]
related: [ECO-0007, MVS-SMP-0006, MVS-SMP-0008, MVS-SMP-0010, MVS-SMP-0015]
---

## The claim

**A condition code says whether a job ran. It never says whether the work
happened.** The inventory — a member list, a `LIST` stanza, a startup banner —
answered correctly each time; the return code did not. `[tested]`

## Three cases, same day, three projects (a fourth added below)

1. **`NOT SEL` install.** RECEIVE, APPLY CHECK, APPLY and ACCEPT all RC 00,
   `HMA2270 … SUCCESSFULLY COMPLETED`, `STATUS = REC APP ACC` in both zones, and
   an empty target library (`MVS-SMP-0006`).
2. **Upgrade whose `STEPLIB` was never re-pointed.** Every step RC 00 and the
   old server still serving. Reason: a deleting SYSMOD resolves the old
   element's ddname in its own job, so the new library is installed into, the
   old library is left populated, and a `STEPLIB` still naming it keeps loading
   the old module (`MVS-SMP-0010`, same-last-qualifier case).
3. **Multi-line IDCAMS scratch that deleted one of six data sets** and reported
   a single non-zero code. The cause is the transport, below.

4. **Stale input after a failed upload (added 2026-10-26).** The TK5 image carries
   `HERC01.FTPD.LOAD.XMIT` and `HERC01.FTPD.SAMP.XMIT` of FTPD 1.2.0. When the upload of the
   new XMIT files fails, or goes to other data set names, and the install job still names those
   data sets, RECEIVE succeeds and SMP reports TFTP130, but the installed module is the old one.
   The SMP output showed `Receiving 'FTPD.V1R2M0.LINKLIB'` and the started task printed
   `FTPD 1.2.0`; the return codes were clean. `[tested]` Delete the old data sets before the
   upload, and read the banner afterwards. The upgrade return codes themselves differ by image
   (`MVS-SMP-0015`).

Where to read the truth instead: the member list of the target library after an
install (`MVS-SMP-0006`, `MVS-SMP-0008`), the `LIST CDS` / `LIST ACDS` stanza
after a removal (`MVS-SMP-0009`), the product's startup banner after an
upgrade.

## Case 3: "^" does not survive the mvsMF REST API

Measured transport observation, TK5 system, 2026-09-14 (inbox report; the job
text and number were not carried over): `IF LASTCC ^= 0` arrived at IDCAMS as
`.=`. IDCAMS answered

```
IDC4229I INVALID RELATIONAL EXPRESSION
```

and then **discarded the rest of the input stream**. Every statement after the
bad card was skipped, so the job reported one error instead of five omissions.
`[tested]` Write `NE` instead of `^=`, and list afterwards.

Where the byte goes wrong. `[source]`

- mvsMF's job-submit path translates the JCL body ASCII to EBCDIC with the
  **CP037** table before it splits it into cards (`submit_jcl_content`).
- That table maps ASCII `^` (X'5E') to EBCDIC X'B0' (`cp037_atoe`). The
  IBM-1047 table in the same file maps it to X'5F'.

That the `.` in the IDCAMS echo is X'B0' shown as an unprintable character is
an inference. `[inferred]` The mapping was read at the commits above; the
2026-09-14 run was not repeated against them, and the transport version that was
running then was not checked. `NE` carries no such character.

## Rules

- After an install: list the target library. After a removal: read every
  `LIST` stanza. After an upgrade: read the startup banner.
- In IDCAMS input that travels through the mvsMF REST API, use the keyword
  comparison (`NE`) instead of `^=`.
