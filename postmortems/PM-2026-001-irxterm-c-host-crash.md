---
id: PM-2026-001
title: IRXTERM crashes only when called from a C host — as370 assembles RS-format D(,B) with base 0
status: tested
platform: [mvs38j]
sources:
  - "rexx370/docs/irxterm-c-host-crash.md — the investigation, evidence log, job numbers"
  - "rexx370 commit a04a945 — fix: IRXTERM C-host crash root-caused (as370 RS-format D(,B) shim bug) + istso EXTRACT S328 (#206)"
  - "cc370 commit 15927eb — fix(as370): reject RS/SI/S storage operand with an index/length subscript (#12) (#16)"
  - "cc370/as370/src/as370.c:1256-1257, 1511, 2200-2205 — note_badfmt in the F_RS / F_SI / F_S encoders"
verified_on: 2026-07-02
applies_to: [rexx370, httprexx, cc370, libc370]
tags: [as370, hlasm, rs-format, lm, stm, psa, low-core, s0c1, s0c4, wild-branch, save-area, postmortem, toolchain]
related: [ECO-0003, PM-2026-002, MVS-BLDL-0001]
---

## Symptom

A crash that appeared **only** when rexx370's IRXTERM was invoked from a C program.
The pure-assembler test cases (`TTERMVL`, `TLNKTERM`) never reproduced it against the
same LINKLIB.

- Abend code rotated between **S0C1, S0C2, S0C4 and S0C6**, varying with timing.
- In every dump **R13 and R14 looked completely sane**.
- **R0 through R12** were full of what looked like system control blocks.

## Environment

MVS 3.8j, MVS-CE (`mvsdev.lan`) under Hercules. rexx370, httprexx as the consumer that
hit it, `as370` from cc370 as the assembler. Investigation and fix both 2026-07-02.
Job numbers throughout the evidence log below.

## Root cause

**Not IRXTERM, not the C runtime, not the LINK/BALR machinery.** A single
assembler-syntax pitfall in the caller-side shim (`test/trxcall.asm`, httprexx
`asm/htrxterm.asm`):

```asm
         LM    R0,R12,20(,R13)    restore R0-R12        <-- BROKEN
         LM    R0,R12,20(R13)     restore R0-R12        <-- correct
```

`LM` and `STM` are **RS-format**: the operand syntax is `D2(B2)`. The RX-style
`D2(,B2)` form with an empty index field is **silently assembled by as370 with
base register 0**:

```
LM 0,12,20(,13)   ->  98 0C 0014      base 0 — LM from ABSOLUTE 0x14
LM 0,12,20(13)    ->  98 0C D014      base R13 — intended
```

So the shim's epilog restored **R0–R12 from PSA low core 0x14–0x48** — the CVT
pointer, old PSWs, CSWs — instead of from the caller's save area.

The adjacent `L R14,12(,R13)` is **RX-format**, which legitimately has an index
field, so it assembled correctly. **That is precisely why R13 and R14 were always
intact while R0–R12 were garbage.** The "garbage" was literally our own task's old
PSWs (`078D0000 xxxxxxxx` pairs) and nucleus addresses. Its contents varied with
interrupt timing, which produced the wandering wild-branch targets and the rotating
abend codes.

**Why only from C:** an artifact of coverage, not of C. Only the C-host path goes
through the buggy shim (`trx_call` / `HRXCALL`). The pure-asm tests and the VLIST
wrappers use the correct `D(B)` spelling (`LM R1,R12,24(R13)`), so they never
exercised the bug.

## Wrong turns

Do not skip this section — every one of these is an attractive, well-formed
hypothesis, and a model without this document reproduces them.

**"The C caller's DSA / save area is being corrupted during the IRXTERM call."**
The single most attractive theory, because corrupted registers on return normally
*do* mean a clobbered save area. Refuted by instrumentation: word-by-word diffs of
the caller frame (192 bytes), the shim workarea, a 28 KB module window, and a
2-million-iteration SVC-free spin probe all showed **zero unexpected writes**
(JOB 862–876, JOB 892 "TRXHIT NONE"). **Storage was never corrupted; the broken `LM`
simply never read it.**

**"Rotating abend codes mean a race."** They mean a wild branch into storage whose
*contents* vary with interrupt timing. Different thing, and it points somewhere else
entirely.

**"It is the interpreter's termination path, or the LINK-versus-BALR asymmetry, or a
subpool-0 collision."** All exonerated in the evidence log. JOB 868 ran the pure-asm
path green against the identical LINKLIB — which should have pointed at the shim
much earlier than it did.

**"`20(,R13)` and `20(R13)` are the same thing."** In RX context the empty index is a
normal, harmless idiom, which is exactly what makes it invisible here. A model is
very unlikely to volunteer that the two spellings assemble differently.

**Language Environment.** Not a wrong turn taken by this investigation, but the one
the 2026-07-31 benchmark showed a model takes: CAA in R12, DSA, XPLINK,
`#pragma linkage`, CEEDUMP. MVS 3.8j has no Language Environment — see **ECO-0003**.
That explanation fits the same symptom (corrupt R0–R12, intact R13/R14, rotating
abends) and is internally consistent, which is why it survives scrutiny that is not
platform-aware.

## Fix

- `test/trxcall.asm` — epilog `LM R0,R12,20(R13)`, plus a warning comment.
- `test/trxldc.asm` — same fix in `TRXCALLV`.
- httprexx `asm/htrxterm.asm` — same fix; IRXTERM re-enabled, LPE leak gone.
- Repo-wide scan for further RS-format `D(,B)` operands (LM/STM/CS/CDS/shifts/ICM/…)
  across rexx370, httprexx and libc370 found **no other instance**.
- **The toolchain was hardened so this cannot recur silently:** `as370` now rejects a
  storage operand carrying an index/length subscript on RS/SI/S format, at severity 12,
  matching IFOX00's ERR216 ILLEGAL OPERAND FORMAT. `[source: cc370 15927eb;
  as370.c:1256-1257, 1511, 2200-2205 — note_badfmt on ns >= 2 in the F_RS / F_SI / F_S
  encoders, text "Illegal operand format (index/length not allowed on RS/SI/S operand)"]`
  The commit records that `resolve()` produced two subscripts (`sub[0]=0`, `sub[1]=base`)
  and the encoder took the first as the base.

`[tested]` **Negative proof:** re-introducing the `D(,B)` spelling reproduces the
original crash signature immediately (JOB 890); the fixed spelling with the identical
LINKLIB is green (JOB 899). Full matrix: 55 tests × batch+TSO, 0 failures
(JOBs 903/905/909/911/913), host suite 2474 assertions pass.

## Second bug found on the way — `istso.asm` S328

While verifying, TREXXVL's batch leg failed deterministically in its 5th IRXINIT with
**S328 inside SVC 40 (EXTRACT)**. `istso.asm` issued `EXTRACT …,MF=(E,WEXTLST)` with
the parameter list in a **freshly GETMAINed, non-zeroed** workarea. The E-form stores
the answer-area address and the FIELDS bytes but leaves the TCB slot (list+4)
untouched; residual garbage there is read as a TCB address → S328. It worked by luck
whenever the GETMAINed storage happened to be zero. Fixed by `XC`-clearing the
parameter list and answer area before the EXTRACT.

Also corrected: a comment claiming EXTRACT issues SVC 9. **EXTRACT is SVC 40.**

## The transferable lesson

Two, and both are about the toolchain rather than about MVS:

1. **Suspect our own toolchain before suspecting MVS.** The assembler emitted valid,
   wrong code with no diagnostic. Shared with **PM-2026-002**, where the linker did
   the same thing.
2. **When a symptom says "storage was corrupted", check whether the storage was ever
   read.** Here it was byte-stable throughout; the instruction that was supposed to
   read it addressed somewhere else entirely.
