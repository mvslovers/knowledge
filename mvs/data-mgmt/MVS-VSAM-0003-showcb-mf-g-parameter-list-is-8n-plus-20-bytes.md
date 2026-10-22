---
id: MVS-VSAM-0003
title: SHOWCB with MF=G needs a parameter list of 8n+20 bytes for n fields — a 64-byte list fails for seven
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE throwaway containers (image ghcr.io/mvslovers/mvsce:latest as of 2026-10-20; image digest and Hercules version not recorded), 2026-10-20: container A JOB00022, JOB00024, JOB00026; container B JOB00022 (container-local job numbers)"
  - "libc370 PR #698 (merged 2026-10-20, released in 2.25.0, closes #623): body, last bullet of 'What MVS 3.8j / MVS/CE did'; src/mvs/vsam/@@vsinfo.c and test/mvs/tstvsox.c at v2.25.0"
  - "mvslovers/mvs38src, work/macros/mvsce-2.1.4-target: SHOWCB and IDACB2 macros (MF=G generation: PLLEN, header length, element stride; SHOWCB field type codes)"
verified_on: 2026-10-20
verified_platforms: ["MVS/CE"]
applies_to: [libc370]
tags: [vsam, showcb, mf-g, parameter-list, acb, keylen, lrecl, buffers, idacb2, r15, libc370]
related: [MVS-VSAM-0001, MVS-VSAM-0002]
---

## The claim

`SHOWCB ...,FIELDS=(f1,...,fn),MF=(G,list)` builds its parameter list in the
caller's area, and that area must be **8n+20 bytes**: n+1 address words
(4(n+1)), a 16-byte header, and one word per field (4n). For seven fields
that is 76 bytes. A 64-byte list, the size the other libc370 VSAM functions
use, made the seven-field SHOWCB return R15 4 on every call. `[tested]`

Size the list for `8n+20`, not `4n` plus a little. (TESTCB and MODCB list forms
were not measured.)

## The measurement

Platform: MVS 3.8j, MVS/CE image. Container A, JOB00026, exploration program
VSEX2 (scratch, not in the repo):

```
SHOWCB ACB=...,FIELDS=(KEYLEN,RKP,LRECL,CINV,BUFND,BUFNI,BUFSP),
       LENGTH=28,AREA=...,MF=(G,list)        list area: 128 bytes
```

R15 0; values `8 0 80 4096 0 0 0`. Afterwards the list area held:

- 8 address words: the first points to the 16-byte header, the next seven to
  one word each, the last with the high bit set (`800AA338`);
- the header `A0030000 000A9B28 000AA370 001C0000`;
- 7 field-code words `00100000 001F0000 00110000 00080000 00040000 00050000 00070000`.

That is 32 + 16 + 28 = 76 bytes = 8*7+20. The field-code words are the SHOWCB
type codes of KEYLEN X'10', RKP X'1F', LRECL X'11', CINV X'08', BUFND X'04',
BUFNI X'05', BUFSP X'07' `[source: SHOWCB macro, ACB keyword scan]`.

Failure and cure:

- With a 64-byte list (16 words) the same seven-field SHOWCB returned R15 4 on
  every call (container A JOB00022, step GREEN of an early build).
- The same fields one at a time with 64 bytes returned R15 0 (container A
  JOB00024, program VSEX); two and four fields also returned 0 (JOB00026).
- With an 80-byte list (`unsigned pl[20]`, `src/mvs/vsam/@@vsinfo.c` in libc370
  2.25.0) the probe passed 40/40 (container B JOB00022).

## Where the formula comes from

The arithmetic is read off one dump with n=7 and fits the 64-byte failure and
the successes with n=1, 2 and 4 (8n+20 is 28, 36, 52: all within 64 bytes).
The generating macro agrees. In IDACB2, standard (non-reentrant) form:
`&PLLEN SETA 4*(&IDAENO+1)` is the address-word part; the first element value
sits at `&PLLEN+&IDACB03+4` with the header length `&IDACB03` = 16 (set in
SHOWCB); each further element follows at `EOFF(i-1)+&IDAELEN(i-1)+4`; the
area used is `EOFF(n)+IDAELEN(n)`. For SHOWCB the element loop jumps straight
to code generation and skips the "default element length 4" assignment, so
`IDAELEN` stays 0. That gives 4(n+1) + 16 + 4n = 8n+20
`[source: SHOWCB and IDACB2 macros, MVS/CE 2.1.4 copy in mvslovers/mvs38src]`.
This is a reading of the macro text, not a trace of the run-time routine, and
the `MF=G` expansion was not assembled at ingest; the match with the measured 76
bytes is what supports it.

A prediction, not measured: with 64 bytes, up to five fields fit (60 bytes) and
six or more do not (68 and more) `[inferred]`.

## How the overflow produces R15 4 `[inferred, not measured]`

Presumably the generated list overruns the area and corrupts the parameter list
itself. Only the R15 4 is measured.
