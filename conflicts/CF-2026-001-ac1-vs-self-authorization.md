---
id: CF-2026-001
title: Does any AC(1) setting in our builds actually carry load?
status: disputed
platform: [mvs38j]
sources:
  - "ufsd commit bf859e0 — restores setcode AC(1) on the UFSD load module"
  - "nsf370/m5-stage0a-ssi-probe.md:35-40"
  - "ECO-0001"
verified_on: 2026-07-27
applies_to: [ufsd, libc370]
tags: [apf, authorization, svc244, ac1]
related: [ECO-0001]
---

## The two positions

**A.** ufsd commit `bf859e0` restores `setcode AC(1)` on the UFSD load module, with
the reasoning that UFSD is an APF-authorized STC and that the v2 migration had
dropped the v1 setting. This presupposes that `AC(1)` does something.

**B.** `nsf370/m5-stage0a-ssi-probe.md` states that a task self-authorizes at run
time via `clib_apf_setup` → `__autask()` → SVC 244, *independent of its library*,
and that UFSD's and HTTPD's STEPLIBs are not in `IEAAPF00` — yet both run
authorized. This presupposes that `AC(1)` is unnecessary.

## Why they cannot both be the whole story

`AC(1)` is necessary but not sufficient under the classic MVS rule: it takes effect
only when the module is loaded from an APF-authorized library, as the job step
program. If UFSD's library genuinely is not in `IEAAPF00`, then the `AC(1)` from
`bf859e0` is inert and the commit's stated reasoning is wrong — harmless, but
misleading to anyone reading it later. If instead the library *is* authorized on
some target system, then position B's claim is too broad and the ecosystem has two
different authorization paths depending on where it is installed, which nothing
documents.

## What would settle it

1. Inspect `SYS1.PARMLIB(IEAAPF00)` directly on each target system and record
   whether the relevant libraries appear. Position B's claim rests on an assertion
   in the probe notes that this was checked; the check itself is not recorded.
2. Remove `AC(1)` from the UFSD build, start the STC, and test whether it still runs
   authorized. If it does, `AC(1)` is vestigial and should be removed with a comment
   pointing here.

Both are cheap. Prefer resolving by experiment (CLAUDE.md §9).

## Status

Open. Blocks benchmark question Q-03, whose premise is position B.
