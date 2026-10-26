---
id: MVS-LNK-0004
title: ERRET exit registers - LOAD passes completion code in R1 and reason in R15, LINK only the completion code
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/httpd#300 (comment: 'The ERRET convention on MVS 3.8j, measured'); probe LDLP, internals/fetchprobe/ldlp.asm"
  - "mvslovers/httpd#250 (comment of 2026-10-19: 'LINK reuses a copy that LOAD holds', side finding); probe RESP, internals/fetchprobe/resp.asm"
  - "mvslovers/libc370#553 (measurements and decision), PR mvslovers/libc370#669; src/mvs/link/@@link.c, @@linkx.c, @@loadx.c and include/mvs/link.h on main; release v2.24.0"
  - "Probe RESP ran in two throwaway containers on 2026-10-19 (mvs-docker images, Hercules a7423980): TK5 Update 5, container-local JOB 44; MVS/CE, container-local JOB 19"
verified_on: 2026-10-19
verified_platforms: ["TK5 Update 5 and MVS/CE 3.0.0 (LOAD, probe LDLP)", "TK5 Update 5 container and MVS/CE container (LINK, probe RESP)"]
applies_to: [httpd, libc370]
tags: [erret, load, link, svc6, iea703i, abend106, abend806, completion-code, reason-code, libc370, linkx, loadx]
related: [MVS-LNK-0002, MVS-LNK-0003, MVS-LNK-0005]
---

## The claims

1. **`LOAD ... ERRET=`: the exit receives the completion code right-aligned in
   R1 and the reason code in R15.** `[tested]`
2. **`LINK` (SVC 6, parameter list with error exit, no DCB): the exit
   receives the completion code right-aligned in R1, but R15 holds no reason
   code.** `[tested]`
3. R1 is `0x00000806` or `0x00000106`, not the `0x00sss000` form of an abend
   code. `[tested]`

## Evidence

LOAD, probe LDLP (TK5 and MVS/CE, same on both):

| failure | console | R1 | R15 |
|---|---|---|---|
| member not found | `IEA703I 806-4` | `00000806` | `00000004` |
| fetch I/O / channel program error | `IEA703I 106-F` | `00000106` | `0000000F` |

LINK, probe RESP (missing module: LINK after the member had been deleted
from the library, case A of MVS-LNK-0005):

| system | console | R1 in the exit | R15 in the exit |
|---|---|---|---|
| TK5 container | `IEA703I 806- 4` | `00000806` | `000A5AF2` |
| MVS/CE container | `IEA703I 806- 4` | `00000806` | `00095AF2` |

R15 is no reason code (the console said reason 4). The values look like an
address in the probe's own region; that is the reading in httpd#250, not
verified. `[inferred]`

The LINK form is the one libc370's `__link()` issues: `OI 4(plist),X'80'`,
`LA 0,ERRET`, no DCB. `[source: libc370 src/mvs/link/@@link.c, main
ae319e1]` The ERRET path of `__link()` loads `-1` into R15 and never reads R1.

## What libc370 does with it

- `__link()` and `__linkds()` return -1 on the error exit and throw the
  completion code away. `[source: @@link.c]`
- libc370#553 was closed by PR #669 (merged 2026-10-19), released in libc370
  v2.24.0: new entries `__linkx()`, `__linkdsx()` (completion code via
  `unsigned *abcode`, from R1; no reason code) and `__loadx()` (completion code
  and reason code, from R1 and R15). `abcode` is nonzero only on the ERRET
  path, which also separates it from the plain -1 case. The existing entries
  are unchanged. `[source: include/mvs/link.h, @@linkx.c, @@loadx.c, main
  ae319e1; release notes of v2.24.0]` Whether HTTPD908E now prints the code was
  not checked.

## Consequences

- A diagnostic for a failed LINK can name the completion code (`106`, `806`)
  but not the reason (`0F`, `4`). Only the console `IEA703I` line carries the
  reason for LINK.
- For `106-0F` as a module-fetch fault, see MVS-LNK-0002; for what a failed
  fetch costs, MVS-LNK-0003.
