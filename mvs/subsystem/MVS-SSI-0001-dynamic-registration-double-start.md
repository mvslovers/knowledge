---
id: MVS-SSI-0001
title: Dynamic SSI registration — and why a second START says IEF612I PROCEDURE NOT FOUND
status: tested
platform: [mvs38j]
sources:
  - "ufsd/docs/cross-as-reference.md:135-142 — Known Behavior: double start"
  - "nsf370/m5-stage0a-ssi-probe.md:104-107 — the symptom is IEF612I, not the application's own guard"
  - "nsf370/m5-stage0a-ssi-probe.md:63-71 — live MVSCE gate 2026-07-21, including the negative control"
  - "ufsd/src/ufsd#sct.c — ssct_new / ssct_install / ufsd_ssct_free, SSCT chained into JESCT, anchor in ssctsuse"
verified_on: 2026-07-21
applies_to: [ufsd, nsf370, mvsmf]
tags: [ssi, ssct, ssvt, jesct, iefssreq, ief612i, stc, start, estae, registration, ipl]
related: [ECO-0004]
---

## The symptom

While a dynamically-registered subsystem is live, issuing `S <proc>` a second time
produces:

```
IEF612I PROCEDURE NOT FOUND
```

`[tested: ufsd on Hercules/TK4-; nsf370 on MVSCE 2026-07-21]`

This is counter-intuitive on its face — the procedure obviously *is* found, it was found
the first time — which is exactly why a reasoning-from-the-message-text approach rejects
the right answer. It has nothing to do with the procedure library.

**The application's own "already registered" check does not fire.** It is a second layer
and is never reached. nsf370 states this explicitly after its live run:

> while the SSCT is live the "already registered" symptom is **`IEF612I`** (MVS routes
> the START through the SSI before `main` runs — ufsd's documented double-start), not
> NSFP092E (that guard is the second layer).

`[source: nsf370/m5-stage0a-ssi-probe.md:104-107]`

## The mechanism

MVS routes system-internal SSI calls — the job-step / START notifications — through the
**registered router**, and it does so *before* the second instance's own code gets
control. The router rejects the call, and the rejection surfaces to the console as
IEF612I.

`[source: ufsd/docs/cross-as-reference.md:135-138]` — both ufsd and nsf370 state this
independently. `[inferred]` on the last step: nobody has traced the specific SSI function
code MVS uses for the notification, only observed the symptom and its dependency on
registration state.

**The negative control is what makes it credible.** On MVSCE, after a clean `P NSFP`
(which deregisters the SSCT), a second `S NSFP` **re-registered cleanly — no `IEF612I`
and no `NSFP092E`**. `[tested: nsf370, 2026-07-21]` So the message is tied to the SSCT
still being live, not to the restart itself.

## Stopping the first instance fixes it

`/P <proc>` deregisters the SSCT — `ufsd_ssct_free()` removes it from the JESCT chain and
frees SSCT and SSVT — after which `S` works again. `[source: ufsd#sct.c:138-144]`

## What registration actually does

`ufsd_ssct_init()`, in supervisor state:

1. allocate the SSVT and SSCT in CSA,
2. `ssct_new("UFSD", ssvt, anchor)` — the four-character subsystem name, the SSVT, and the
   anchor address, which is parked in **`ssctsuse`** so the SSI router can recover the
   anchor from a given SSCT,
3. `ssct_install(ssct, NULL)` — chain the SSCT into **JESCT**.

Failure paths are announced, not silent: `UFSD091E` (cannot enter supervisor state),
`UFSD094E` (cannot allocate SSCT), `UFSD025E CANNOT INSTALL SSCT, RC=…`.
`[source: ufsd/src/ufsd#sct.c:23-59]`

nsf370's startup sequence on a clean start reads:

```
NSFP000I → NSFP034I SSCT REGISTERED → NSFP035I SSI ROUTER LOADED AT 00A8B488
         → NSFP001I READY ANCHOR=00A6C970
```

and shutdown:

```
NSFP095I SSCT DEREGISTERED → NSFP036I ROUTER UNLOADED → NSFP011I → IEF404I ENDED
```

`[tested: nsf370 live gate, 2026-07-21, no dump]`

## The operational hazard: the deregistering ESTAE is mandatory

**If the STC abends without its ESTAE cleaning up, the SSCT stays registered until IPL.**
There is no system service that reclaims it — see **ECO-0005**: MVS 3.8j has no `RESMGR`,
so there is nothing to fall back on. The ESTAE exit is the only cleanup path, which is
why ufsd documents it as mandatory rather than as good practice.

`[source: ufsd/docs/cross-as-reference.md:141-142]`

nsf370 flags the same dependency from both ends: an STC abend escaping ESTAE leaves the
SSCT registered, **and** a router abend in the client's address space leads to the same
place. A stuck SSCT means every subsequent `S` gives IEF612I with no way back short of an
IPL.

## Diagnosing it

| Observation | Reading |
|---|---|
| `S <proc>` → `IEF612I`, first instance still up | Normal, documented. Stop the first instance. |
| `S <proc>` → `IEF612I`, no instance running | The SSCT is stuck from an abend that escaped ESTAE. IPL, or clear the JESCT chain. |
| The application's own duplicate-registration message on the console | Something other than a live SSCT — the guard was reached, so registration was not blocked by the router. |
| `S` works after `/P` | The expected path. Deregistration happened. |

Do **not** read IEF612I here as a duplicate-jobname condition, an ENQ conflict on the
procedure name, or a PROCLIB problem. It is none of those, and the message text actively
misleads.
