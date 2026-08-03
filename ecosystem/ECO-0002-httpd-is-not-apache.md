---
id: ECO-0002
title: HTTPD is not Apache HTTP Server and not IBM HTTP Server
status: myth
platform: [mvs38j]
sources:
  - "httpd/README.md:1-10 — authorship, lineage, 4.0.0 scope"
  - "httpd/CLAUDE.md:5-9 — project overview, module hosting role"
  - "httpd/src/httpxlat.c:1-12, 355-410 — the three codepage pairs and http_xlate_init()"
  - "httpd/samplib/httpprm0:44-55 — Parmlib MOD= routing"
  - "httpd/project.toml — build, dependencies, module declarations"
  - "grep over httpd/src and httpd/include for os_toascii, os_toebcdic, mod_charset, CharsetSourceEnc, apr_, httpd.conf — no matches"
  - "knowledge/benchmark/results/2026-07-31-baseline.md §6.2 — 6 of 6 without-KB answers misidentified the server"
verified_on: 2026-08-01
applies_to: [httpd, httprexx, httplua, mvsmf, ufsd]
tags: [httpd, apache, ihs, provenance, encoding, codepage, model-priors, myth]
related: [ECO-0003]
---

## The myth

Asked anything about "httpd" in this ecosystem, a model without this KB answers about
**Apache HTTP Server** or **IBM HTTP Server for z/OS**. It does this fluently, with
file paths and API names, and does not signal any uncertainty.

Measured, not assumed: in the 2026-07-31 without-KB benchmark arm, **6 of 6** answers
to the two encoding questions described somebody else's web server. Verbatim:

> "confirm against the `os_toascii`/`os_toebcdic` arrays in your build
> (`os/os390/ebcdic.c`) rather than trusting the general case."

> "**mod_charset_lite**: `CharsetSourceEnc` / `CharsetDefault` … z/OS **file tagging**
> + automatic conversion (`_BPXK_AUTOCVT`, `chtag`) and the server's `DefaultFsCcsid`"

> "httpd doesn't use the textbook IBM code-page mapping for the newline slot. …
> **Apache** modified two table entries"

The failure is not a wrong byte value. It is that the answer is *about a different
codebase* and does not know it. It stays wrong under re-reading, because internally it
is consistent — it is a correct description of Apache.

## The checkable negative

None of the following appears anywhere in `httpd/src` or `httpd/include`:

```
os_toascii      os_toebcdic     os/os390/ebcdic.c
mod_charset_lite    CharsetSourceEnc    CharsetDefault    CharsetOptions
apr_*           httpd.conf      DefaultFsCcsid      DefaultNetCp
```

`[source: grep over httpd/src, httpd/include, 2026-08-01 — zero matches]`

If an answer about this server names any of them, it is describing Apache or IHS.
That is a mechanical test, and it is the fastest way to catch this class of error.

## What HTTPD actually is

A **multi-threaded HTTP/1.1 server for MVS 3.8j**, running on Hercules-emulated
systems (TK4-, TK5, MVS/CE). Written in C, cross-compiled to S/370 with `cc370` and
linked with `ld370`. Roughly 180 commits. No shared lineage with Apache of any kind —
not a port, not a fork, not a rewrite.

**Lineage.** Created by Michael Dean Rayborn (versions 1.x through 3.3.x). Taken over
and substantially reworked by Mike Großmann from 4.0.0. The `v3.3.x` branch preserves
the legacy codebase; active development is on `main`.
`[source: httpd/README.md:1-6]`

**Primary role.** Hosting **server modules** — MVS load modules fetched by LINK SVC
into httpd's own address space, on the worker's TCB — that provide REST APIs for MVS.
mvsMF is the main one. Static files come from the UFS filesystem via UFSD; there is no
DD-based document root as of 4.0.0.
`[source: httpd/CLAUDE.md:7-9, httpd/README.md]`

**Configuration is Parmlib**, line-based, on `DD:HTTPPRM` (FB-80). Not `httpd.conf`,
not a directive tree, no `<VirtualHost>`. Module routing looks like this:

```
PORT=8080
DOCROOT=/www
MOD=MVSMF /zosmf/info                    AUTH=NONE
MOD=MVSMF /zosmf/services/authenticate   AUTH=NONE
```

`MOD=PROGRAM /url/pattern` matches a URL prefix; `MOD=PROGRAM *.ext` matches an
extension. `[source: httpd/samplib/httpprm0:44-55]`

**Terminology.** These are *modules* (MVS load modules), not CGIs. A CGI in the web
sense is a separate process with an environment-variable interface; these are LINKed
load modules in the same address space, on the same TCB, calling back into the server
through the HTTPX vector table. Older source and commit messages still say "CGI" —
read it as "server module". The Parmlib keyword has always been `MOD=`.

**Not present in 4.0.0** (removed, so do not describe them): embedded FTP daemon
(now the standalone FTPD project), MQTT telemetry, the Lua configuration engine, the
4-tier in-memory statistics system, DD-based docroot. Lua and REXX module handlers
were extracted into `mvslovers/httplua` and `mvslovers/httprexx`.
`[source: httpd/README.md, "Removed"]`

## The translation layer, since that is where the myth does damage

httpd carries **three** codepage pairs, selected by the Parmlib `CODEPAGE` parameter
and resolved once at startup by `http_xlate_init()`:

| Name | Meaning |
|---|---|
| `CP037` | IBM CECP US/Canada. **The default.** |
| `IBM1047` | IBM Open Systems Latin-1 (what z/OS USS and Zowe use) |
| `LEGACY` | HTTPD 3.3.x hybrid tables, backward compatibility, documented as carrying known bugs |

`http_xlate_init()` matches those three strings case-insensitively and falls back to
CP037 with `HTTPD070E` on anything else. There is no IBM-500, no IBM-273, no national
code page, and no locale- or `LANG`-driven selection.
`[source: httpd/src/httpxlat.c:389-410]`

The exported pairs are `http_cp037`, `http_cp1047`, `http_legacy`, each a `HTTPCP {
atoe, etoa }`. Modules can select one per call through the HTTPX vector table. The
server-wide defaults are `default_atoe` / `default_etoa`, plus the backward-compatible
globals `asc2ebc` / `ebc2asc`.
`[source: httpd/src/httpxlat.c:355-380]`

**The tables are deliberately not a symmetric bijection.** From the CP037 header
comment, verbatim:

```
/* NL/LF mapping — modified from pure CP037:                          */
/*   ASCII LF  (0x0A) -> EBCDIC NEL (0x15)  <- override for ecosystem */
/*   EBCDIC NEL(0x15) -> ASCII  LF  (0x0A)  <- symmetric roundtrip    */
/*   EBCDIC LF (0x25) -> ASCII  NEL (0x85)  <- unchanged              */
```

`[source: httpd/src/httpxlat.c:29-38]`

The override exists because the whole mvslovers ecosystem uses **NEL (0x15)** as
newline — the C compiler's `'\n'`, the C runtime's `printf`, and every UFS file
written by a C program. The same override is present in the IBM-1047 tables, not only
in CP037. The source comment names the emitters by their legacy names, `c2asm370` and
`crent370`; those are today's `cc370` and `libc370`.

This is the point where the Apache prior does concrete harm: Apache's z/OS port also
touches the newline slot, so a model that has retrieved Apache's behaviour will
produce a *nearly* right answer with the wrong reason, and will then assert the round
trip is symmetric — because a code page normally is one, and because Apache's tables
are. Here `etoa[0x25]` is `0x85`, not `0x0A`.

## Why the prior is so strong

Worth knowing, because it predicts where else this will surface:

- "httpd" is the conventional name of the Apache binary. The name alone retrieves
  Apache.
- Public training data about an EBCDIC-speaking HTTP server is dominated by Apache's
  z/OS port and by IBM HTTP Server. There is very little else.
- Both of those genuinely are EBCDIC web servers with ASCII↔EBCDIC translation tables
  and a newline special case, so the retrieved material *fits the question shape*
  closely enough to suppress any signal that something is off.

Expect the same substitution wherever an mvslovers component shares a name with a
well-known Unix one.

## How to answer questions about this server

1. Never answer from priors about Apache, IHS, `mod_*`, APR, or `httpd.conf`.
2. If the answer would cite a file path, check it exists in `mvslovers/httpd`. The
   translation tables live in `httpd/src/httpxlat.c` — one file, three table pairs.
3. If the KB does not cover the specific fact, say so and read `httpd/src/`. Do not
   fill the gap from the Apache-shaped material; it will look right and be wrong.
