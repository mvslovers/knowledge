---
id: ECO-0009
title: as370 exits with its severity and mbt gates on it — the gap is rc 4, where the column-72 continuation lives
status: tested
platform: [mvs38j]
sources:
  - "as370 1.6.3 (802dde1), host runs: two severity-12 errors -> exit 12; duplicate symbol alone (IFO196, severity 8) -> 8; undefined opcode -> 8; warnings -> 4; clean -> 0 and no output at all (2026-10-17)"
  - "mbt internal/build/build.go — the as step fails at rc >= 8 and deletes the object deck; a cc370 step fails at any rc != 0 (re-measured by the MBT session the same day)"
  - "httprexx asm/htrxterm.asm — the IFO026 case that cost a BALR and ended S0C1"
  - "an IFOX00 listing showing IFO213 zeroing an instruction: `000202 0000 0000` where `58F0 F098` belongs"
verified_on: 2026-10-17
applies_to: [oftpd, httprexx, rexx370, brexx370, libc370, mbt]
tags: [as370, assembler, exit-code, severity, ifo026, ifo196, ifo213, column-72, continuation, mbt, build-gating]
related: []
---

## What the exit code means

`as370` exits with the **highest severity it issued**, and mbt gates on that.
Measured with as370 1.6.3:

| Input | Exit |
|---|---|
| two severity-12 errors | 12 |
| duplicate symbol alone (`IFO196`, severity 8) | 8 |
| undefined opcode | 8 |
| warnings only | 4 |
| clean | 0, and **no output at all** |

`[tested]`

mbt's `as` step fails at **rc >= 8** and deletes the object deck, so a later
build cannot mistake a stale deck for a current one; a `cc370` step fails at
any rc != 0 and reports an assembler problem as rc 1.
`[source: mbt internal/build/build.go]`

So hard errors are caught, and caught properly. The hazard is the band below
the gate.

## rc 4 is the gap, and `IFO026` lives there

Warnings pass by design — the gate behaves like `COND=(8,LT)`, and as370 has
no warnings-as-errors switch. `[tested]` Among the warnings is **`IFO026`, the
column-72 continuation**, whose damage is that the *next* source line is
swallowed as the continuation of this one. A long inline comment running into
column 72 is enough.

The worked example: httprexx's `asm/htrxterm.asm` lost a `BALR` that way and
abended **S0C1** at run time. Nothing in the build said anything louder than a
warning.

**The defence is mechanical, not the exit code:**

```
awk 'length($0) >= 72' file.asm      # must print nothing
```

Run it over hand-written assembler before believing a clean build. Whether
rc 4 should fail a build at all is a maintainer decision, not a judgement call
for a session. It is **open**: no session may flip it, and no session should
record it as decided without the maintainer's own word.

## `IFO213` zeroes the instruction

Noted because the artifact is unusual: an `IFO213` leaves `000202 0000 0000`
in the listing where `58F0 F098` belongs. A deck can be structurally fine with
an instruction missing from it. `[tested]` Today this is harmless — `IFO213`
carries a severity above the gate, so the build fails anyway — but it is worth
knowing that the object is not merely "missing a symbol", it contains zeroes.

## Measure the exit code without a pipe

The first version of this measurement claimed "as370 exits 0 on severity 12".
It came from

```
as370 … 2>&1 | head -40; echo $?
```

which reports `head`'s status, not the assembler's. `[tested]` Redirect
instead:

```
as370 … > out 2>&1; echo $?
```

This is the general shell trap in the root `CLAUDE.md` ("Agent Discipline") in
its exact local form: the instrument answered, plausibly, and was wrong.
