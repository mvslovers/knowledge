---
id: MVS-LNK-0005
title: A LINKed module does not survive its LINK; a copy held by LOAD in the job step task is found by every LINK, also from subtasks
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/httpd#250 (comments: JPQ walk of 2026-10-14; probe RESP of 2026-10-19), probe internals/fetchprobe/resp.asm, resp.py, rprbs.asm"
  - "mvslovers/httpd#198 (comment: 'Step 2 implemented ... verified in throwaway TK5 containers'), PR mvslovers/httpd#305 merged as 7003d75 on 2026-10-19; src/httpd.c resident_hold()/resident_release(), src/httpprm.c, include/httpd.h on origin/main"
  - "RESP ran in two throwaway containers on 2026-10-19 (mvs-docker images, Hercules a7423980): TK5 Update 5, container-local JOB 44; MVS/CE, container-local JOB 19. HTTPD verification: TK5 containers, image build c34e331, container-local JOB00045 to JOB00048"
verified_on: 2026-10-19
verified_platforms: ["TK5 Update 5 container and MVS/CE container (RESP)", "TK5 Update 5 container, Hercules a7423980 (HTTPD RESIDENT=YES)", "an MVS 3.8j system (JPQ walk, 2026-10-14)"]
applies_to: [httpd, mvsmf, libc370]
tags: [link, load, delete, use-count, job-pack-area, contents-supervisor, resident, rent, reus, program-fetch, httpd, erret]
related: [MVS-LNK-0002, MVS-LNK-0003, MVS-LNK-0004]
---

## The claims

1. **A module brought in by LINK is deleted as soon as its use count drops to
   0.** The next LINK fetches it from the library again. `[tested]`
2. **A copy held by `LOAD` in the job step task is found by the LINK of every
   task of the job step**, including subtasks, and then no fetch happens.
   `[tested]` The hold ends with `DELETE`.
3. **It works on the path libc370's `__load(NULL, ...)` uses**:
   `BLDL` + `LOAD DE=,DCB=0`. `[tested]`
4. **A module linked without RENT and without REUS was also found and re-run
   from the held copy** (case C), when nobody was using it. `[tested]`
5. Concurrent LINKs of a held module: a RENT module is shared, a REUS-only
   module serialises its callers, a module that is neither gets a fresh copy
   per concurrent caller. **Not measured**: only one LINK was active at a time.
   `[assumed]` (from MVS's rules, as stated in httpd#250)

## Evidence: the copy does not survive its LINK

On an MVS 3.8j system, 2026-10-14 (HTTPD 4.2.0-DEV, mvsMF `99a423c`): HTTPD's
job pack queue was walked twice through its `/.dm` page while no mvsMF request
ran (worker TCB `+7C` TCBJSTCB gives the jobstep TCB; its `+2C` TCBJPQ starts
the chain, followed through CDCHAIN; `/.dm` reads without LINKing MVSMF):

```
CDE 9BA018 HTTPDM   EP 144340 USE 1
CDE 9DD028 HTTPD    EP 0A5A08 USE 6
CDE 9DE080 CTHREAD  EP 0A5530 USE 0
```

No MVSMF on the queue. A few minutes earlier `/zosmf/test?fn=textsum` had
reported MVSMF at CDE `9BA018`, loaded at `0x140258`, 335,272 bytes, use count
1 *during its own request*. By the walk, that CDE cell and part of that extent
belonged to HTTPDM; the same walk 20 s later gave the same result.
Consequence: every dispatch after an idle gap is a full program fetch (for
MVSMF a contiguous 335 KB GETMAIN placed wherever the region has room).

Case A below confirms this on TK5 and on MVS/CE.

## Evidence: probe RESP, LINK after the member is gone

`RESP` (IFOX00) and five trivial modules `RPRBA`-`RPRBE` (`SR 15,15 / BR 14`)
in a library that is also in `STEPLIB`. After each LOAD the probe deletes the
module's member (`STOW ... D`) and checks with `BLDL` that it is gone (RC 4
every time). A LINK that still works used the copy in storage; one that fails
`806-4` went to the library. LINK is the SVC 6 form `__link()` uses: no DCB,
with an error exit (MVS-LNK-0004). `[source: resp.asm, resp.py]` Same result on
TK5 and MVS/CE, line for line.

| case | what | LINK after the member is gone |
|---|---|---|
| A | no LOAD: LINK, delete member, LINK | **806-4**: the first copy did not survive its LINK |
| B | `LOAD EP=` (RENT, REUS), delete member, LINK | **OK** |
| B | then `DELETE`, LINK | **806-4** |
| C | as B, module linked without REUS (link-edit `PARM='LIST'`: also no RENT) | **OK** |
| D | `LOAD EP=` in the job step task, LINK from a subtask (`ATTACH`) | **OK** |
| E | `BLDL 0` + `LOAD DE=,DCB=0` (libc370 `__load(NULL, ...)`), BLDL `Z=2` (job/step library); LINK in the same task and from a subtask | **OK**, both |

- The `RPRBC` link-edit step in `resp.py` uses `PARM='LIST'` only (the others
  `LIST,RENT,REUS`). `[source: internals/fetchprobe/resp.py]` httpd#250 words
  case C as "linked without REUS".
- Whether C holds while the held copy is in use is part of the concurrency
  question, not measured.

## What HTTPD does with it: `RESIDENT=YES`

HTTPD PR #305 (merged as `7003d75` on 2026-10-19, issue #198 step 2, remedy of
#300; `RESIDENT=YES|NO`, default `YES`): startup LOADs each distinct `MOD=`
module once in the job step task, `terminate()` DELETEs it after the workers
are gone, dispatch stays a LINK.
`[source: httpd src/httpd.c resident_hold(), resident_release(); src/httpprm.c
default cfg_resident = 1; origin/main]`

- `resident_hold()` BLDLs the module and holds it with `__load(NULL, name,
  NULL, NULL)` only if its load attributes carry RENT or REUS. A module that
  is neither (`HTTPD441W`), missing (`HTTPD440W`) or fails to load
  (`HTTPD442W`) is not held and keeps the fetch per request.
  `F HTTPD,D CONFIG` shows `HTTPD137I RESIDENT YES  MODULES HELD n`.
- The reason for the RENT/REUS rule: one copy of a module that is neither may
  not run twice, and the held copy would be reused (case C).
- Status in the ecosystem: merged to HTTPD main; the latest HTTPD release at
  the time of checking (2026-10-22) is v4.3.0 (2026-10-15), so `RESIDENT=` is
  not in a release yet. The #300 closing comment says the default is `YES`
  "from 4.4.0 on".

Verification, throwaway TK5 containers (TK5 Update 5, Hercules `a7423980`,
HTTPD build `c34e331`; the test deletes the module's member while the server
runs: a request that still answers used the held copy, one that fetches
fails `806-4`):

| | `RESIDENT=YES` (JOB00046) | `RESIDENT=NO` (JOB00047) |
|---|---|---|
| startup | `HTTPD441W MODULE NOREUS NOT REUSABLE, FETCHED PER REQUEST`, `HTTPD440W MODULE NOSUCHXX NOT FOUND AT STARTUP, NOT HELD` | no 44x lines |
| `D CONFIG` | `HTTPD137I RESIDENT YES  MODULES HELD 3` | `HTTPD137I RESIDENT NO  MODULES HELD 0` |
| member `MVSMF` scratched (IEHPROGM, JOB00048), 1 request then 30 in parallel | **31 x 200**, no `IEA703I` | **31 x 503**, 31 x `IEA703I 806- 4` + `HTTPD908E` |

- Key 8 (batch instances from a private library): as in the table.
- Key 0 (the STC from APF libraries after a re-IPL):
  `HTTPD002I AUTHORIZED BY LIBRARY (MODULE KEY 0)`, `HTTPD137I RESIDENT YES
  MODULES HELD 1`; with `MVSMF.LINKLIB` emptied (JOB00045), 31 of 31 mvsMF
  requests answered 200, no `IEA703I`; `P HTTPD` ended `HTTPD099I`, 46
  requests, 0 errors.
- Not verified: `HTTPD442W` (not provoked); a REUS-only module under
  concurrent requests (every ecosystem module is RENT and REUS); whether the
  shutdown DELETE frees the copy before step end (step end frees it either
  way).

## Consequences

- A server that keeps its modules in memory fetches once per module and per
  server life, so a `106-0F` (MVS-LNK-0002) can cost storage (MVS-LNK-0003)
  only at that one fetch.
- A held module is not replaced by a new level in the library until the server
  is restarted: a new module level takes effect without a restart only with
  `RESIDENT=NO`.
- Hold the copy with LOAD in the job step task. A copy brought in by LINK
  gives no such hold (case A).
