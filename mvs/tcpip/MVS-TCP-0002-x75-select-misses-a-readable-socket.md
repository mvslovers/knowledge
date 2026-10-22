---
id: MVS-TCP-0002
title: select() over several sockets can miss a readable one -- the emulator takes nfds from the host descriptor of the highest socket number
status: tested
platform: [mvs38j]
sources:
  - "libc370 issue #144 and PR #655 (merged 2026-10-19; full job output in the PR body); probe test/mvs/tst75sel.c, jcl/tst75sel.jcl (header: mechanism, build, how to read)"
  - "MVS 3.8j (MVS/CE) in a throwaway local container, NUMCPU 1; emulator SDL Hyperion develop a742398 (banner 4.10.0.11783-SDL-DEV-ga7423980, 2026-10-13); tcpip.c and tcpip.h identical to 16e62c4. Probe run on 2026-10-19."
  - "hyperion tcpip.c, case 17 SELECT subcode 4, at a742398 and at upstream develop cc555792 (2026-10-21); read 2026-10-22"
  - "libc370 src/net/dyn75/@@75selx.c at v2.25.1 (the aux2 the library passes); read 2026-10-22"
verified_on: 2026-10-19
applies_to: [libc370, httpd, ftpd]
tags: [hercules, x75, select, nfds, ccom-han, host-descriptor, slot-order, tst75sel, readiness]
related: [MVS-TCP-0001, MVS-TCP-0004, MVS-TCP-0008]
---

## The claim

On an emulator with the code of a742398 (still in upstream develop on
2026-10-21), `select()` over **more than one socket** can return without a
socket that has data waiting. A select over one socket is not affected.
The defect is in Hercules' `tcpip.c`, not in libc370. `[tested]`

## Mechanism

The emulator runs the host `select()` with

```c
i = select (Ccom_han [aux2 - 1] + 1, ro, wo, eo, &timeout);   /* SELECT subcode 4 */
```

`aux2` is the guest's `maxsock` (highest socket number + 1; libc370 passes
the caller's `maxsock` unchanged as aux2). So `nfds` is the **host descriptor
of the highest socket number** in the set, plus one -- not the highest
descriptor in the set. `[source: tcpip.c @ a742398, @@75selx.c @ v2.25.1]`

Socket numbers come from the emulator (lowest free, MVS-TCP-0001), host
descriptors from the host kernel (lowest free). While only the guest opens
and closes sockets the two orders stay in step. The probe's header says
a socket whose descriptor lies at or above `nfds` is not examined: the host
returns its bit cleared (a silent miss) or, in a later word of the set,
untouched (a false "ready"). `[inferred: from the probe header's reading of
host select() semantics; only the miss was observed]`

The orders come apart when the Hercules process itself holds a descriptor
that has no guest socket number: its TN3270 console, its HTTP console or a
sockdev accepts a connection. **A guest can cause that itself** by
connecting to Hercules' own HTTP or TN3270 port. `[tested]`

## Evidence

Probe sequence (phase B of `tst75sel.c`): socket P (slot p, descriptor x),
socket H (slot p+1, descriptor x+1), close P, connect H to a port Hercules
itself serves (Hercules accepts on descriptor x, no slot), socket C (slot p
-- low slot, descriptor x+2 -- high descriptor), C connected to the probe's
own listener and its peer sends one byte. H gets Hercules' reply. Both are
readable (FIONREAD, a different function code that does not go through
SELECT). `select()` over {C, H} gets `aux2` = slot of H + 1,
`nfds` = descriptor of H + 1, and C is not examined.

```
+TST75SEL A r=0 s=4,7,9,11 rc=4 miss=0 false=0      (r=0..7 all clean)
+TST75SEL B#0 P=4 C=4 H=6 port=<hercules http port> layout=C<H
+TST75SEL B#0 {C,H} rc=1 C:1/0 H:285/1 bad=1
+TST75SEL B#0 ctl {C} rc=1 bad=0 {H} rc=1 bad=0
+TST75SEL RESULT DEFECT: 4 anomalies, B layout 4/4 - RC 4
```

`C:1/0` = FIONREAD 1 before the select, bit 0 after it: a miss. `H:285/1`
is the HTTP reply, reported correctly. The line `{C} rc=1 ... {H} rc=1`
shows each socket alone is reported correctly. `[tested]`

- **Control (phase A):** 4 connected pairs, 8 rounds of close and reopen
  by the guest alone. Every round clean: slots and descriptors stay in step.
- **Phase B:** the condition (`layout=C<H`) was created in 4 of 4 attempts and
  the miss occurred in 4 of 4.

## Who is exposed

libc370#144 reports that over 40000 select runs on MVS 3.8j none had more
than one descriptor in its set: HTTPD selects on its listener alone, FTPD on
one control or data socket at a time, ufsd, mvsmf and the Lua/REXX HTTP
modules do not select. `[tested, per libc370#144; not repeated at ingest]`
A program that selects on **several sockets** is
exposed on any emulator that has this code, and waits for a socket that is
already readable. `[inferred: from the mechanism and the survey]`

A select over one socket per call is correct for the case measured.
`[inferred: from the {C} and {H} controls; the workaround itself was not
tried]`

## Not fixed

No emulator change is referenced from libc370#144 or PR #655, and the line
above is unchanged in upstream develop (2026-10-21). libc370 has no guard for
it. `[source: tcpip.c @ develop cc555792]`
