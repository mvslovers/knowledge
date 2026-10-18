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
  - "mvslovers/mbt#278 (2026-10-17) — the maintainer's position: rc 4 is a warning, as on MVS, and he is against failing the build on it"
  - "the ecosystem-wide as370 return-code census of 2026-10-18: 818 assemblies in clean clones of 13 projects' HEADs, built with a logging shim as MBT_AS and first on PATH, with a column-72 positive control (mvslovers/mbt#286)"
verified_on: 2026-10-18
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
for a session.

**It is decided, and this document said otherwise for a day.** The maintainer's
position is recorded in **mvslovers/mbt#278** (2026-10-17): rc 4 is a warning,
as on MVS, and he is **against failing the build on it**. That issue was opened
the same day as this entry and neither knew about the other, so this document
was written saying the question was "open" and "waiting on the maintainer" when
his word already existed. Corrected 2026-10-18. `[source: mvslovers/mbt#278]`

The measurement in the next section was taken afterwards and is **new evidence
against a decided question, not grounds to treat it as unmade**. Anyone citing
it has to cite #278 with it.

## What an rc-4 deck actually loses, and what the gate would cost

Measured 2026-10-18, as370 1.6.3 (802dde1). Two files of the same four
statements, differing only in a trailing comment that reaches column 72 on the
`BALR` line:

```
clean.asm -> rc 0 -> clean.o: OS/360 object deck -- 1 section(s), 4B text
warn.asm  -> rc 4 -> warn.o:  OS/360 object deck -- 1 section(s), 2B text
```

`[tested]` **Four bytes of text against two**: the `BR 14` is gone from the
deck, the deck is otherwise well-formed, and nothing downstream can tell. That
is the httprexx `BALR` in miniature, and it makes the *shape* of the hazard
reproducible without waiting for it to happen again.

as370's own diagnostic is explicit — *"This card was consumed as a
continuation and the statement on it discarded (IFOX00 IFO026, severity 4)"* —
and mbt prints it: `b.logs` is the same writer `b.say` uses, so the text
reaches the build output on every build. It simply does not stop anything.
**So the problem is not visibility, it is that nothing acts on it.**

**Nothing in the ecosystem assembles at rc 4 today.** A census over clean
clones of each project's HEAD, built with a logging shim as `MBT_AS` and first
on `PATH`:

| Project | as370 invocations | rc != 0 |
|---|---|---|
| libc370 | 766 | 0 |
| brexx370 | 20 | 0 |
| rexx370 (`make` / `make test`) | 13 / 8 | 0 |
| nsf370 | 9 | 0 |
| oftp370, httprexx | 1 each | 0 |
| ufsd, ftpd, httpd, httplua, zlib370, lstring370 | 0 | 0 |
| **total** | **818** | **0** |

`[tested]` The zero is a measurement and not an exit-0-and-plausible number:
the positive control above went through the same shim and logged rc 4. And the
shim did intercept everything — libc370's build prints `[libc] 737 .s + 29
.asm` and the shim logged exactly 766 calls.

Two scope lines that are easy to get wrong:

- **mbt hands `.s` to cc370 and only `.asm` to as370**, so the rc-4 question is
  about `.asm` alone. libc370 builds with its own make and routes both through
  as370, which is where 766 comes from rather than 29.
- cc370's own 57 `.asm` files are the toolchain's test corpus and deliberately
  contain malformed input. They are not ecosystem code and were not counted.

The static check agrees with the census: across those projects there are 115
lines with a non-blank in column 72 and **every one is a deliberate
continuation marker** (`X`, `x`, `*`, `C`, `@`) on a code line.

A first count of 474 was wrong and the way it was wrong is worth keeping. 320
of those were a **`\r` from CRLF files** sitting at byte 72 of a 71-character
line (libc370 is largely CRLF), and most of the rest were brexx370's card
sequence numbers in columns 73-80 behind a real marker at 72. Byte position is
not column position until the line endings have been looked at, and
`awk 'length($0) >= 72'` says nothing about which of the three a hit is.

**So the gate change would be free today** — that is the measurement, and it is
all it is. It reopens nothing: the maintainer decided against the abort in
**mbt#278**, and this census is filed as **mbt#286** as evidence he may weigh
against that decision, not as grounds to treat it as unmade. No session flips
the gate, and no session should read "free" as "therefore do it".

What #278 does leave room for, and what this makes cheaper to argue, is making
the warning harder to miss *without* aborting — a count of assembler warnings
in `mbt build`'s closing line, or a WARNING marker on the step. At 818
assemblies and zero non-zero return codes, such a line would read `0` today, so
any non-zero would mean something the moment it appeared.

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
