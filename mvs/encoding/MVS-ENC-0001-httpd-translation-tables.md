---
id: MVS-ENC-0001
title: httpd's three ASCII/EBCDIC translation table pairs — CP037, IBM1047, LEGACY
status: source
platform: [mvs38j]
sources:
  - "httpd/src/httpxlat.c:29-38 — the CP037 header comment and the NL/LF override rationale"
  - "httpd/src/httpxlat.c:60-61, 70-71, 88-99 — cp037_atoe / cp037_etoa rows read directly"
  - "httpd/src/httpxlat.c:181-182, 190-191, 209-218 — ibm1047_atoe / ibm1047_etoa"
  - "httpd/src/httpxlat.c:268-278 — the LEGACY header with its Known issues list"
  - "httpd/src/httpxlat.c:282, 292-293, 297-298, 317-333 — legacy_atoe / legacy_etoa"
  - "httpd/src/httpxlat.c:355-410 — the exported HTTPCP pairs and http_xlate_init()"
  - "httpd commits 71b21b3, 00119cb (2026-03-21) — the NEL override and the CP037 bracket fix"
verified_on: 2026-08-04
applies_to: [httpd, httprexx, httplua, mvsmf]
tags: [encoding, ebcdic, ascii, codepage, cp037, ibm1047, legacy, brackets, pipe, newline, nel, httpxlat]
related: [ECO-0002]
---

## Three pairs, selected once at startup

httpd ships exactly three codepage pairs. The Parmlib `CODEPAGE` parameter picks one;
`http_xlate_init()` matches `"CP037"`, `"IBM1047"` and `"LEGACY"` case-insensitively and
falls back to CP037 with **`HTTPD070E`** on anything else. Server modules can also select
a pair per call through the HTTPX vector table.

```c
HTTPCP http_cp037  = { cp037_atoe,    cp037_etoa    };
HTTPCP http_cp1047 = { ibm1047_atoe,  ibm1047_etoa  };
HTTPCP http_legacy = { legacy_atoe,   legacy_etoa   };
```

`[source: httpxlat.c:355-410]`

There is no IBM-500, no IBM-273, no national code page, and no locale- or `LANG`-driven
selection. If a diagnosis reaches for one of those, it is not describing this server —
see **ECO-0002**.

## The characters that actually differ

Everything alphanumeric is invariant across all three. What moves is the punctuation
JSON and shell-ish payloads care about.

| Char | ASCII | CP037 | IBM-1047 | LEGACY |
|---|---|---|---|---|
| `[` | 0x5B | **0xBA** | **0xAD** | **0xAD** (1047 position) |
| `]` | 0x5D | **0xBB** | **0xBD** | **0xBD** (1047 position) |
| `\|` | 0x7C | **0x4F** | **0x4F** | **0x6A** ← known bug |
| `^` | 0x5E | 0xB0 | 0x5F | 0x5F |
| `\` | 0x5C | 0xE0 | 0xE0 | 0xE0 |
| `_` | 0x5F | 0x6D | 0x6D | 0x6D |

`[source: httpxlat.c:60-61 / 70-71 (CP037), 181-182 / 190-191 (IBM-1047), 292-293 /
297-298 (LEGACY)]`

**CP037 and IBM-1047 differ on the brackets and agree on the pipe.** So a CP037↔IBM-1047
mismatch mangles `[` and `]` and leaves `|` alone. If the pipe is also broken, the
mismatch is not between those two.

## LEGACY is a hybrid, not a third clean code page

The source says so in its own header:

```
/* LEGACY — HTTPD 3.3.x hybrid tables (backward compatibility)        */
/*                                                                    */
/* Known issues:                                                      */
/*   - Brackets [/] patched to IBM-1047 positions (0xAD/0xBD)         */
/*   - Pipe | left at non-standard position (0x6A atoe, wrong etoa)   */
/*   - NEL(0x15)->LF(0x0A) from httpetoa.c switch baked in            */
```

`[source: httpxlat.c:268-278]`

It is otherwise CP037-shaped but carries the IBM-1047 bracket positions. It exists only
for compatibility with httpd 3.3.x and is documented in the source as carrying known
bugs. Do not describe it as "an older CP037" or "an alias for IBM-1047".

### The pipe under LEGACY — state this precisely

- `legacy_atoe[0x7C]` = **0x6A**, with the source comment
  `| at 0x6A instead of 0x4F (KNOWN BUG)`.
- `legacy_etoa[0x6A]` = 0x7C — so within LEGACY the pipe **does** round-trip.
- `legacy_etoa[0x4F]` = **0x5D**, i.e. `]`, with the source comment
  `NB: [0x4A] = 0x5B([), [0x4F] = 0x5D(]) — legacy`.

So the breakage is **interoperation, not self-consistency**: every other producer in the
world encodes `|` at 0x4F, and LEGACY decodes 0x4F as `]`. Payload that a CP037 or
IBM-1047 side wrote comes back through LEGACY with the pipe turned into a closing
bracket. `[source: httpxlat.c:297-298, 328-329]`

**LEGACY is the only one of the three that touches the pipe at all.**

## The newline override, and where LEGACY diverges again

CP037 and IBM-1047 both carry a deliberate deviation from the pure code pages:

```
/*   ASCII LF  (0x0A) -> EBCDIC NEL (0x15)  <- override for ecosystem */
/*   EBCDIC NEL(0x15) -> ASCII  LF  (0x0A)  <- symmetric roundtrip    */
/*   EBCDIC LF (0x25) -> ASCII  NEL (0x85)  <- unchanged              */
```

Because the whole mvslovers ecosystem uses **NEL (0x15)** as newline — `cc370`'s `'\n'`,
`libc370`'s `printf`, every UFS file written by a C program. Verified in the tables:
`cp037_etoa[0x15]` = 0x0A, `cp037_etoa[0x25]` = **0x85**; `ibm1047_etoa` identical.
`[source: httpxlat.c:29-38, 88-96, 209-218]`

**The pair is therefore not a bijection.** `0x0A → 0x15 → 0x0A` round-trips; an EBCDIC
`0x25` arriving from elsewhere comes out as `0x85`, not as a newline.

LEGACY does not have the override and collapses instead:

- `legacy_atoe[0x0A]` = **0x25** — the un-overridden pure value `[source: httpxlat.c:282]`
- `legacy_etoa[0x15]` = 0x0A **and** `legacy_etoa[0x25]` = 0x0A — both map to LF
  `[source: httpxlat.c:317-323]`

So LEGACY is lossy in the other direction: two distinct EBCDIC bytes decode to the same
ASCII byte, and only 0x25 comes back out.

## Diagnosing a mangled payload

| Symptom | Configuration |
|---|---|
| `[` `]` wrong, `\|` fine | CP037 ↔ IBM-1047 mismatch |
| `\|` wrong (arrives as `]`) | **LEGACY** — the only pair that moves the pipe |
| EBCDIC 0x25 from outside not becoming a newline | correct behaviour under CP037/IBM-1047; it becomes 0x85 |
| unknown `CODEPAGE=` value silently behaving as CP037 | look for `HTTPD070E` on the console |
