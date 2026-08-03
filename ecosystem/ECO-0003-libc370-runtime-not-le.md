---
id: ECO-0003
title: The libc370 runtime model — and why it is not Language Environment
status: myth
platform: [mvs38j]
sources:
  - "libc370/doc/startup.md:1-177 — the three anchors, the three startfiles, the exit paths"
  - "libc370/asm/@@crt0.asm, @@crt1.asm, @@crtm.asm — the startup sequences"
  - "libc370/src/clib/@@crtset.c, @@crtget.c, @@crtres.c, @@grtset.c, @@grtget.c"
  - "libc370/maclib/pdpprlg.macro — the compiled prologue reads the NAB at 76(,13)"
  - "grep for CEESTART, CEEPIPI, CEEENTRY, CEEDUMP, SCEELKED, XPLINK, TERMTHDACT, CEECAA over libc370, cc370/as370, rexx370, httpd — zero matches, 2026-08-01"
  - "knowledge/benchmark/results/2026-07-31-baseline.md §6.1 — the measured failure"
verified_on: 2026-08-01
applies_to: [libc370, cc370, rexx370, httpd, httprexx, httplua, ufsd, nsf370]
tags: [libc370, runtime, startup, crt0, crt1, crtm, clibcrt, clibgrt, clibppa, linkage, save-area, language-environment, model-priors, myth]
related: [ECO-0002]
---

## Why this document exists

Asked to debug a C-on-MVS problem in this ecosystem, a model without this KB answers
in terms of IBM **Language Environment**. Across three benchmark runs and two
questions, **nine answers** did exactly that. It is the most reproduced failure the
benchmark has produced.

MVS 3.8j has no Language Environment. What it has is libc370's own runtime, described
below. Read that first; the LE correction is one short section at the end, kept short
on purpose.

## The three runtime anchors

Everything is located **without a global variable** — the runtime is reentrant.
`[source: libc370/doc/startup.md:40]`

| Block | Scope | Anchored in | Found by |
|---|---|---|---|
| **CLIBPPA** (`clibppa.copy`) | per program invocation | the TCB first-save-area "next" slot, `8(TCBFSAB)`, eyecatcher `'@PPA'` | `@@PPAGET` |
| **CLIBCRT** (`clibcrt.copy`) | per **TCB / thread** | the `ppa->ppacrt[]` array | `crt->crttcb == current TCB` |
| **CLIBGRT** (`clibgrt.copy`) | per process / address space | `crt->crtgrt` and `ppa->ppagrt` | `__grtget` |

- `@@PPAGET` reads `PSATOLD -> TCB -> TCBFSAB -> 8(fsa)` and checks the `'@PPA'`
  eyecatcher.
- `__crtget` scans `ppa->ppacrt[]` for the entry whose `crttcb` equals the current
  TCB, and returns the **first** match.
- `__grtget` is literally `crt->crtgrt`. `[source: @@grtget.c]`

`__CRTSET` inherits the GRT of the **originating** TCB, read from `TCBOTC` at
`tcb[0x84/4]`, which is what makes the GRT effectively per-address-space across
ATTACHed threads. `[source: @@crtset.c]` The important consequence for LINKed modules
is in **ECO-0002**'s neighbourhood and in `benchmark/results/2026-07-31-baseline/2026-08-01-grt-crt1-crtm.md`.

## The stack is a NAB scheme, not an MVS save-area stack

The `STACK` DSECT field `THEIRSTK` sits at **offset 76**. Every compiled C function's
prologue reads it:

```
pdpprlg.macro:   L 15,76(,13)     <- the NAB (Next Available Byte)
```

Each startup does `LA R0,MAINSTK; ST R0,THEIRSTK` to point the initial NAB at its
GETMAIN'd stack region; every C call bumps the NAB to carve its frame.
`[source: libc370/doc/startup.md:52-62]`

**This is the single most dangerous near-collision with LE.** LE also keeps a value at
a fixed offset in R13's block — its NAB, at `X'4C'` = 76 decimal. Same number,
different runtime, different block layout. An answer that says "NAB at offset 76" is
therefore *not* evidence that it understands libc370; it is exactly what an
LE-primed answer says too. Check what else the answer claims before crediting it.

## The three startfiles

All three define the **same** entry point `@@CRT0` and are **mutually exclusive** —
built as separate objects outside `libc.a`, so the linker pulls exactly one into a
given program, like glibc's `crt1.o`. `[source: libc370/doc/startup.md:7-12]`

| Startfile | Use it for | Threads | Builds the runtime? | Stack |
|---|---|:-:|---|---|
| `crt0.o` | standalone program that creates threads (`cthread_create*`) | yes | yes (full) | 256 KB |
| `crt1.o` | standalone program that does **not** create threads — the common case | no | yes (full) | 256 KB |
| `crtm.o` | a C module entered **inside an already-running C runtime on the same TCB** (LINK/XCTL/LOAD+BALR from a C program) | no | no — **reuses** the caller's | 64 KB |

- **crt0 vs crt1** differ in exactly one functional line: the
  `IDENTIFY EPLOC=CTHREAD` at startup, which is what lets `ATTACH EP=CTHREAD` resolve.
  `@@crt1.asm` is otherwise a line-for-line copy. Not a size or optimisation
  difference. `[source: libc370/doc/startup.md:22-27, 105-112]`
- **crtm** omits the PPA GETMAIN, the TCBFSA anchoring, `@@CRTSET`, `@@GRTSET` and the
  `EXTRACT`. It calls `@@CRTGET` for an **existing** CLIBCRT, saves that CRT's
  `CRTSAVE` into `OLDSAVE`, and swaps in its own save area.
- **Never use `crtm` as the top-level startfile.** Its `@@CRTGET` is dereferenced with
  no NULL check; without a prior crt0/crt1 on the same TCB the store lands in
  protected low core and abends. `[source: libc370/doc/startup.md:28-30, 128-133]`

Two details that distinguish crtm and are easy to miss:

- **Non-standard linkage.** crt0/crt1 take the parm via `R1 -> A(parm)`. crtm keeps
  **R0** (`PGMR0`) and passes it as `__start`'s first argument — one indirection less.
  crtm is entered by purpose-built caller code, not attached as a job step.
- **Its own inline `@@EXITA`.** Because crtm provides `@@EXITA` as its own `ENTRY`,
  the linker does not pull `@@exita.o` from `libc.a`. That inline version restores
  `CRTSAVE` from `OLDSAVE`, FREEMAINs only its own stack, and calls **neither
  `@@GRTRES` nor `@@CRTRES`** — crtm created none of them, so it must not tear them
  down.

**Caveat on crtm:** `__start` re-opens `stdout`/`stderr`/`stdin` and overwrites
`grt->grtout/...`. Since crtm shares the parent's GRT, nesting it **clobbers the
parent's standard streams**. `[source: libc370/doc/startup.md:145-150]`

### Exit paths

| | Teardown module | GRT freed | CRT freed | PPA out of TCBFSA | FREEMAIN |
|---|---|:-:|:-:|:-:|:-:|
| crt0 / crt1 | `@@exita.o` from `libc.a` | yes (`@@GRTRES`) | yes (`@@CRTRES`) | yes | PPA + stack |
| crtm | inline `@@EXITA` | no | no | no | own stack only |

## Linkage on 3.8j

Standard OS linkage. **R13 points at a 72-byte save area**, not at a DSA:
`STM 14,12,12(13)` on entry, `L 13,4(13)` / `LM 14,12,12(13)` on exit; R14 return,
R15 entry/return code, R1 parameter list. There is no XPLINK, no downward-growing
stack, no `#pragma linkage(…, OS)` — because there is no other linkage to
distinguish it from.

## Practice note: `crtm` is documented but unused

No module in the ecosystem is built with `crtm`. Across every `project.toml` under
`~/repos/mvs`: **120 × `startup = "crt1"`, 1 × `crt0`, 0 × `crtm`** — although
`crtm.o` is built and shipped (`libc370/build/sdk/crtm.o`) and `startup.md` documents
it as the correct choice for the nested case. httpd's server modules use `crt1`
deliberately, "for the threading runtime (`@@CRT1`)"
`[source: httprexx/project.toml:16-17, httplua/project.toml:20]`, because `crtm`
carries no CTHREAD entry. Whether the rule in `startup.md` should be restated, scoped
or retired is open — see gap **G-3a** in `benchmark/questions.md`.
`[source: grep over all project.toml, 2026-08-01]`

---

## The correction: there is no Language Environment here

**What LE is.** IBM's common runtime for C, COBOL, PL/I and Fortran, introduced with
MVS/ESA in the early 1990s and standard on OS/390 and z/OS. It supplies the CAA
(Common Anonymous Area) in R12, DSAs on a downward-growing stack, condition handling,
enclaves, and the `CEE*` symbol namespace.

**MVS 3.8j predates all of it by more than a decade.** libc370 is an independent
runtime; the table above is the whole model.

**The checkable negative.** None of the following appears anywhere in `libc370`,
`cc370/as370`, `rexx370`, or `httpd`:

```
CEESTART   CEEPIPI   CEEENTRY   CEEDUMP   CEECAA
SCEELKED   XPLINK    TERMTHDACT
```

`[source: grep, 2026-08-01 — zero matching files for each]`

If an answer about this ecosystem names any of them, it is describing a platform the
target system does not have. That is a mechanical test.

**The mapping, if you need to translate an LE-shaped thought:**

| LE concept | Here |
|---|---|
| CAA in R12 | no equivalent; R12 is an ordinary base register |
| DSA / downward stack | NAB scheme, `THEIRSTK` at 76(,13), upward |
| enclave | no equivalent |
| `CEESTART` / `CEEPIPI` | `@@CRT0` — one of `crt0.o` / `crt1.o` / `crtm.o` |
| CEEDUMP, `TERMTHDACT` | no equivalent; ordinary MVS ABEND dumps |
| `#pragma linkage(…, OS)` | not needed — OS linkage is the only linkage |
| `SCEELKED` | `libc.a` plus one startfile object |

## What the wrong answer looks like

From the without-KB baseline, verbatim, so the shape is recognisable:

> "R13 and R14 sane, R0–R12 full of control blocks, is exactly what you'd expect if
> the routine is running on **Language Environment's registers rather than its own**.
> … an LE caller hands you R1 = parameter list, **R12 = CAA**, R13 = DSA … The classic
> version of this bug is an assembler routine that uses **R12 as its base register**
> while LE uses R12 for the CAA."

> "In LE-based builds that anchor CSECT is the standard bootstrap (`CEESTART` and
> friends) … look at the **preinitialized environment** path (LE preinit, `CEEPIPI`)"

**The concrete damage.** That first quote is a diagnosis of the IRXTERM-from-C crash,
and it is wrong. The actual root cause was `as370` assembling the RX-style empty-index
form `D(,B)` on an RS-format `LM` with **base register 0** — `98 0C 0014` instead of
`98 0C D014` — so R0–R12 were restored from PSA low storage at `0x14`–`0x48` rather
than from the caller's save area. R13/R14 survived because the adjacent
`L R14,12(,R13)` is RX-format and assembled correctly.
`[source: rexx370/docs/irxterm-c-host-crash.md; commits rexx370 a04a945, cc370 15927eb]`

Both explanations fit the same symptom — corrupted R0–R12, intact R13/R14, rotating
abend codes. That is why the LE answer is durable and why it costs real time: it is
internally consistent, it is specific, and there is nothing in the symptom alone to
falsify it. Only knowing that the platform has no LE does that.
