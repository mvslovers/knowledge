---
id: MVS-LNK-0003
title: A failed program fetch (106-0F) never gives back the module's storage
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/httpd#300 (description: HTTPD free-storage samples, 335,352-byte MVSMF text; comments: probe LDLP, MOVED page, S0C4 case)"
  - "mvslovers/httpd internals/fetchprobe/ldlp.asm and README.md (MOVED counter)"
  - "Soak run of HTTPD 4.3.0 / mvsMF 1.3.0 (libc370 2.12.1) on a TK5 system, 2026-10-15; probe runs on TK5 and MVS/CE systems, 2026-10-16 to 2026-10-19; job numbers are system-local"
verified_on: 2026-10-19
verified_platforms: ["TK5 Update 5 system (HTTPD soak)", "TK5 and MVS/CE systems (probe LDLP)"]
applies_to: [httpd, mvsmf]
tags: [program-fetch, iea703i, abend106, storage, leak, getmain, erret, httpd]
related: [MVS-LNK-0002, MVS-LNK-0004, MVS-LNK-0005]
---

## The claims

1. **When program fetch fails (`IEA703I 106-0F`) and the caller has an ERRET
   exit, the storage fetch had obtained for the module stays allocated.** MVS
   does not free it, with or without HTTPD in the picture. `[tested]`
2. **A fetch that completes and then abends is cleaned up normally.** Only the
   failed fetch orphans storage. `[tested]` (one observation)
3. **The size lost is the module's size rounded up to 4 KB pages.**
   `[tested]` (MVSMF: 82 pages.)

## Evidence

**Plain MVS, probe LDLP** (see MVS-LNK-0002): after every FAIL, all following
loads of the 4 KB module IEMRA land one page higher (`0xA6000` to `0xA7000`
and on); the probe counts these as MOVED. Seen on TK5 and on MVS/CE.

**Inside HTTPD**, 24 h soak on a TK5 system: one LINK of MVSMF failed in
fetch,

```
18.13.10 STC   78  IEA703I 106- F HTTPD    HTTPD    MODULE ACCESSED MVSMF
18.13.10 STC   78  HTTPD908E EXTERNAL PROGRAM MVSMF could not be loaded
```

and from that request on the free storage of HTTPD's private area (SP0) was
lower by exactly the module's pages:

| sample (after soak run) | total_requests | SP0 free | blocks | largest block at |
|---|---|---|---|---|
| baseline | 1,887 | 7,274,496 | 1 | `0x1C4000` |
| runs 1-11 | ... 19,858 | 7,274,496 | 1 | `0x1C4000` |
| 106-F at 18.13.10, during run 12 | | | | |
| runs 12-16 | ... 28,834 | 6,938,624 | 1 | `0x216000` |

- 7,274,496 - 6,938,624 = 335,872 bytes = 82 pages = `0x52000`: the bottom of
  the free area moved up by `0x52000`.
- MVSMF's text is 335,352 bytes (`file370 -v`, sum of the text records of that
  build); rounded up to 4 KB pages that is 82 pages = 335,872 bytes.
- The loss stayed for the remaining roughly 9,000 requests of the soak
  (19,858 to 28,834 `total_requests`). Over about 27,000 module requests
  nothing else moved: 0 bytes per request before and after the step.
- A second TK5 system showed the same failed MVSMF fetch twice in HTTPD; the
  2 x 82 pages there were presumed, not measured.

**Contrast, completed fetch then abend:** an MVSMF S0C4 at module start on the
same system left HTTPD's free storage unchanged, 6,938,624 before and after.

## Consequences

- A failed fetch costs the module's size for the life of the address space.
  HTTPD never sees an address it could free: `__link()` returns -1 on ERRET
  and gets no storage address.
- With about 7 MB free after a start and MVSMF at 82 pages, around 20 failed
  fetches of MVSMF leave no room for a module's 256 KB startup stack (arithmetic
  from the figures above, not measured); every module request fails from then
  on.
- The remedy for a server is to avoid repeated fetches: hold the module
  (MVS-LNK-0005).
- Who frees the storage on the ERRET path was open when the description was
  written (by design, by defect, or something on the caller's side); the probe
  shows plain MVS does not, but the owning subpool was not identified.
