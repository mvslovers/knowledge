---
id: MVS-JCL-0002
title: A DD statement from the JCL stays allocated after an SVC 99 unallocation request for it — measured with libc370's JES checkpoint and spool handles
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/libc370 PR #679 (merged 2026-10-19; released in v2.24.0, 2026-10-20), 'Also measured on the way'; issue #142"
  - "libc370 test/mvs/tstjsop.c, jcl/tstjsop.jcl and jcl/recvjsop.jcl, run as step GDD (the JCL has HASPCKPT and HASPACE1 DD statements) and step GNODD (none); one job in a throwaway MVS/CE container, container-local job number, COND CODE 0000"
  - "libc370 v2.24.0 src/mvs/jes2ckpt/@@cpclos.c (deallocate_checkpoint) and src/mvs/jes2spool/@@jsclos.c: S99VRBUN, S99NOCNV, text unit DDNAME only"
verified_on: 2026-10-19
applies_to: [libc370]
tags: [jcl, dd, svc99, dynalloc, unallocate, s99vrbun, s99nocnv, dsab, get_dsab, jesopen, jesclose, cpclos, jsclos]
related: []
---

## The claim

When `__cpclos()` (`@@cpclos.c`) and `__jsclos()` (`@@jsclos.c`) end, they close the DCB
and then always issue an SVC 99 unallocation request for the handle's DD name, however
the DD was allocated. The request is `S99VRBUN` with `S99NOCNV` and one text unit, the
DDNAME. **If the DD came from a DD statement in the step's JCL, it is still allocated
afterwards: its DSAB is still found, and a second open through the same DD works.**
`[tested]`

**What was not established is why.** The SVC 99 return code and error reason of the
unallocation request for the JCL DD were not looked at: both closers drop the code
(`__cpclos()` calls `deallocate_checkpoint(cp)` and ignores its result). So the DD
survives; whether SVC 99 refused, or did something else, is not known. **Do not read
this as "SVC 99 never unallocates a JCL DD".** `[source: libc370 v2.24.0]` An earlier
draft of libc370's Library Reference said "MVS refuses to unallocate it"; it was cut to
"stays allocated" for this reason.

## The measurement

Probe `test/mvs/tstjsop.c`. "Allocated" means `get_dsab(NULL, "<ddname>")` returns
non-NULL after `jesclose()`, which calls `__cpclos()` and `__jsclos()`.

Step GDD (JCL with `HASPCKPT` and `HASPACE1` DD statements):

```
+TSTJSOP   checkpoint DD HASPCKPT, spool DD HASPACE1
+TSTJSOP PASS: the DDs of the JCL were used
+TSTJSOP   after jesclose(): HASPCKPT allocated, HASPACE1 allocated
+TSTJSOP PASS: a second jesopen() uses the HASPCKPT DD again
```

Step GNODD (no DD statements; the library allocated the pair itself): `jesclose()`
unallocated both DDs, and over ten open/close rounds the step had "DDs in the step: 2
before, 2 after". `[tested]`

## What it means for a caller

- A program may open its own JCL DD through `__cpopen("DD:...")` or `jesopen()`, close
  it with `__cpclos()` or `jesclose()`, and use the DD again later in the same step.
  Closing does not lose it. `[tested]`
- A DD that `jesopen()` allocated dynamically (no DD statement; since libc370 2.24.0,
  PR #679) is freed again by `jesclose()`. The step needed no `DYNAMNBR` for the two DDs,
  measured in a step with no other dynamic allocation. `[tested]`
- A caller that needs to know whether a DD is still allocated after `jesclose()` can ask
  `get_dsab()`, as the probe does; the unallocation result is not returned.
