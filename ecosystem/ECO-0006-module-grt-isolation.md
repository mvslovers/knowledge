---
id: ECO-0006
title: A server module runs under its own GRT — httpd's core statics are invisible from it
status: source
platform: [mvs38j]
sources:
  - "httpd commit 4a97226 (2026-07-06) — Fix http_logout() no-op from a CGI: reach httpd's store, not the CGI's GRT. Fixes #113"
  - "libc370/asm/@@crt1.asm:77-78 (@@GRTSET at program entry) and :166 (CTHREAD entry, @@CRTSET only)"
  - "libc370/src/clib/@@grtset.c — unconditional crt->crtgrt = grt"
  - "libc370/src/clib/@@crtset.c — GRT inherited from TCBOTC at tcb[0x84/4]"
  - "httpd/project.toml:44-68 — every server module is startup = crt1"
  - "httpd/src/cgistart.c:52, 81, 86, 98 — __grtget() and the grtapp1/grtapp2 re-seed"
  - "httpd/src/httplink.c:38 — __linkds from the worker thread, same TCB"
  - "httpd/CLAUDE.md:143-149 — modules are loaded via LINK SVC; HTTPD/HTTPC pointers travel through the GRT"
verified_on: 2026-08-01
applies_to: [httpd, httprexx, httplua, mvsmf, libc370]
tags: [grt, wsa, writable-static, module, link-svc, crt1, crtm, grtapp1, grtapp2, vector-table, httpx, model-priors]
related: [ECO-0003]
---

## The rule

A server module loaded by httpd **does not share httpd's writable static area**, even
though it runs in httpd's address space *and on the same TCB*. An httpd-core function
reached from the module through the HTTPX vector table reads the **module's** GRT, where
the slot is empty — so the call silently does nothing.

Sharing an address space is not the relevant unit. Sharing a **runtime anchor** is, and
they do not share one.

## Why — the mechanism, step by step

**1. Modules are built with a full startfile.** Every one of httpd's server modules is
declared `startup = "crt1"` with `src/cgistart.c` as its root — `HTTPJES2`, `HTTPDM`,
`HTTPDMTT`, `HTTPDSL`, `HTTPDSRV`. `[source: httpd/project.toml:44-68]`

**2. `crt1` establishes a fresh CLIBGRT.** `@@crt1.asm:77-78`:

```
         L     R15,=V(@@GRTSET)
         BALR  R14,R15           Anchor a CLIBGRT area as CRTGRT
```

`__grtset()` `calloc`s a new CLIBGRT and assigns `crt->crtgrt = grt; ppa->ppagrt = grt;`
**unconditionally**, with no check for an existing one. `[source: @@grtset.c]`

**3. The module runs on the worker's own TCB.** `httplink()` issues
`__linkds(pgm, dcb, plist, &prc)` from inside `serve_client()` on the worker thread —
a plain LINK, no ATTACH, no new TCB. `[source: httpd/src/httplink.c:38]`

**4. So `__grtget()` on that TCB now returns the module's GRT.** `__grtget` is literally
`crt->crtgrt`, and `__crtget` finds the CRT by `crttcb == current TCB`. Any httpd-core
function invoked through the vector table from the module therefore reads the module's
GRT — and everything httpd put in its own is invisible.

**Contrast: ATTACHed worker threads do share.** `@@crt1.asm:166`, the CTHREAD entry,
calls only `@@CRTSET` — never `@@GRTSET` — and `__CRTSET` inherits the GRT of the
**originating** TCB via `TCBOTC` at `tcb[0x84/4]`. That is why a worker thread sees
httpd's GRT and why `libc370/doc/startup.md` can describe CLIBGRT as
"per process / address space" without being wrong. The LINK case is what that
description does not cover. See **ECO-0003** for the full runtime model.

## `cgistart.c` compensates — but only for two pointers

The fresh GRT is not an accident, and it is not unhandled. `cgistart.c` re-seeds the two
pointers a module actually needs, out of the parameter list it was LINKed with:

```c
CLIBGRT *grt = __grtget();
...
grt->grtapp1 = httpd;
grt->grtapp2 = httpc;
```

`[source: httpd/src/cgistart.c:52, 81, 86, 98]` Modules check the `HTTPD_EYE` /
`HTTPC_EYE` eyecatchers before trusting those slots.

**The compensation is incomplete by construction.** Two pointers are restored; anything
else httpd holds in its own GRT's writable static area stays invisible. That is not a
bug in `cgistart.c` — it is the boundary of what it can do.

## The bug class this produces

Three fixed instances, all the same shape: an httpd-core function reads state out of the
current GRT's WSA, is called from a module, finds an empty slot, and fails silently.

- **#109** — userid
- **#111** — password
- **#113** — the credential array. `http_logout()` invalidated nothing when called from a
  module: it reached the store via `credtok_logout()` → `cred_array()`, the token scan
  found nothing, the CRED stayed in httpd's real store, and the token kept resolving
  after a "successful" logout.

`[source: commit 4a97226, which names all three as the "same GRT/WSA class"]`

## The fix pattern

**Resolve the pointer while running in httpd's own GRT, cache it somewhere both sides
can reach, and pass it explicitly into the call made from the module.**

For #113: `httpd->credarr = cred_array()` at `cred_init()` time — in httpd's own GRT,
where it is valid — plus an array-explicit `credtok_logout_arr(array, token)`. The
wrapper keeps using `cred_array()` for httpd-core callers; `http_logout()` passes
`httpc->httpd->credarr` so it operates on httpd's real store from any GRT. The precedent
is `http_get_password()`, which already did this for the blowfish key.

The commit also records why the cross-GRT free is safe: the sysroot libc is built without
`USE_MEMMGR`, so there is no per-runtime free list — `@@getm`/`@@freem` keep the length in
a prefix on the block itself, making `free()` a pure function of (block, subpool). And the
array lock is an address-keyed ENQ, address-space-wide, so locking httpd's real array
address from the module coordinates correctly with the core.

## What does **not** fix it

- **Changing the module's link line.** Dropping httpd's objects from it, or re-linking the
  module against httpd, does not merge the two static areas. The separate GRT follows from
  the module being a separately linked load module with its own startfile, not from a
  build mistake.
- **Dropping the `static` qualifier / making the symbol `extern`.** Same reason.
- **Moving the state into a GETMAIN'd address-space-wide singleton.** Works by accident,
  discards the runtime's structure, and leaves the next instance of the class waiting.
- **Looking for the bug in the vector table.** The dispatch is correct; the code that runs
  is the right code. It is the data it reads that belongs to the wrong runtime.

## Open

**G-3a** — nothing in the ecosystem is built with `crtm`, the startfile that would *not*
establish a second GRT. httpd's `crt1` choice is deliberate and recorded ("for the
threading runtime (`@@CRT1`)"), because `crtm` carries no CTHREAD entry. Whether that
trade should be revisited is not written down. See `benchmark/questions.md`.

A derived-but-unverified consequence about CRT ordering — that the module's `@@GRTSET`
writes onto the *worker's* CRT rather than the one it just created, because both carry the
same `crttcb` and `__crtget` returns the first match — is recorded with a five-minute test
recipe in `benchmark/results/2026-07-31-baseline/2026-08-01-grt-crt1-crtm.md`. `[assumed]`
