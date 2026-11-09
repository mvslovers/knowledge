---
id: MVS-SUP-0003
title: Reading a freed 36,864-byte subpool 1 area abends S0C4 reason 11 — a block cannot carry its own "who owns me" word
status: tested
platform: [mvs38j]
sources:
  - "Measured 2026-11-05 on a throwaway TK5 and a throwaway MVS/CE container: mvslovers/usermods, branch zmg0003/ispf-test, zmg0003/test/ZMGDRV.ASM (operand F, label TESTF), test/mktest.py (step TMPF), test/results-tk5.txt and test/results-mvsce.txt. The results files hold the F1 and F2 lines (chunk address) and no F3 line; the abend code S0C4-11 is recorded in zmg0003/README.md (step TMPF)"
  - "zmg0003/README.md: the owner TCB of the chunks sits at ENVBLOCK+X'138'"
verified_on: 2026-11-05
verified_platforms: ["TK5 throwaway container", "MVS/CE throwaway container"]
applies_to: [brexx370, rexx370]
tags: [getmain, freemain, subpool-1, s0c4, page-translation, freed-storage, ikjct441, envblock, owner, tcb]
related: [MVS-TSO-0006, MVS-SUP-0002]
---

## The claim

A TSO command processor does `GETMAIN` of **36,864 bytes from subpool 1**, `FREEMAIN`s
the same area, then reads its first byte. The read **abends S0C4 with reason 11**
(page translation). The line the program writes after the read (`F3 READ WORKED, NO
ABEND`) does not appear. `[tested]`

The chunk addresses were X'AD000' on TK5 and X'9D000' on MVS/CE: the area starts on a
page boundary and covers whole pages (36,864 = 9 × 4,096).

Program (`TESTF`), the decisive lines:

```
         GETMAIN R,LV=36864,SP=1
         ...
         MVC   0(4,R2),=F'1'       TOUCH THE PAGE
         FREEMAIN R,LV=36864,A=(R2),SP=1
         L     R2,DWORK
         L     R3,0(,R2)           AN ABEND HERE IS THE ANSWER
         MVC   LTXT(30),=CL30'F3 READ WORKED, NO ABEND'
```

## What follows

A structure that must be inspected after its owner may have ended cannot hold the
owner's identity inside itself: a task's subpool 1 storage goes away with the task,
and looking there abends instead of returning old data. `[inferred]`

This matches how `IKJCT441` (usermod `ZMG0003`) is built: the owner TCB of its chunks
is kept in `ENVBLOCK`+X'138', outside the chunks, and the chunks are freed only "if
this task owns them". `[source: zmg0003/README.md]` The README does not state that the
owner word once sat in the chunk header, nor that a two-screen ISPF session abended
because of it; that design history comes from the inbox note only and was neither
reproduced nor found in a public source, so it is not recorded as fact here. See
`MVS-TSO-0006` for the two-screen setup.

## Not measured

- Smaller sizes, or areas that share a page with storage that is still allocated. A
  smaller freed area may well read without an abend, so the abend must not be relied on
  as a detector of freed storage.
- A task that ended, as opposed to an explicit `FREEMAIN`. The test frees explicitly in
  one task.
- Whether a page released here is stolen or merely invalidated. Only the abend code was
  recorded.
