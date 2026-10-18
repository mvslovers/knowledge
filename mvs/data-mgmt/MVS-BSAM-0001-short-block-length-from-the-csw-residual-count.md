---
id: MVS-BSAM-0001
title: The length of a short block after a BSAM/BPAM READ is DCBBLKSI minus the CSW residual count
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE LAB, JOB01197 — rexx370 IRXBPAM reading an FB 80/3120 member of 49 records (39 + 10), 2026-09-25"
  - "mvs38-ibmsrc/ext/ifox-gorlinsky/ieziob.asm — IOBSTDRD field layout: IOBFLAG3 at +8, IOBCSW 0CL7 at +9, `DS XL2 - LAST TWO BYTES OF IOBCSW` at +14"
  - "libc370 src/stdio/@@aread.asm — `L R14,DECB+16 DECIOBPT` / `ICM R1,B'0011',IOBCSW+5` / `SR R9,R1`"
  - "rexx370 asm/irxbpam.asm — the same computation in the BPAM reader (GitHub rexx370#230, PR #232)"
verified_on: 2026-09-25
applies_to: [rexx370, libc370]
tags: [bsam, bpam, read, check, decb, iob, csw, residual-count, blocksize, short-block, fb]
related: [MVS-JCL-0001, MVS-BSAM-0002, MVS-OPEN-0001]
---

## The claim

`READ`/`CHECK` do not tell you how many bytes arrived. **The length of the
block that was just read is `DCBBLKSI` minus the residual count of the CSW**,
a halfword at `IOB+14`, and the IOB is found through the DECB.

For a fixed-blocked member every block is `DCBBLKSI` long except the last,
which is short. Nothing in the DCB or the DECB says so; only the residual
count does.

## Where the two numbers are

- **`DECB+16` is `DECIOBPT`**, the address of the IOB.
  `[source: libc370 @@aread.asm]`
- **The residual count is the last halfword of the CSW**, and in the IOB that
  is `IOBCSW+5` = `IOBSTDRD+14`. `IOBCSW` is `0CL7` — the *low-order seven*
  bytes of the CSW — and starts at +9, right after the one-byte `IOBFLAG3` at
  +8; its last two bytes are the count. `[source: ieziob.asm]`

```asm
         L     R14,DECB+16             DECIOBPT -> IOB
         SLR   R1,R1
         ICM   R1,B'0011',IOBCSW+5     residual count (halfword at IOB+14)
         LH    R2,DCBBLKSI
         SR    R2,R1                   bytes actually read
```

This is what libc370's `@@AREAD` does (`ICM R1,B'0011',IOBCSW+5` / `SR R9,R1`,
with R9 preloaded from the block size), and rexx370's `IRXBPAM` copies it.
`[source: @@aread.asm, irxbpam.asm]`

## Measured

An FB 80/3120 member of **49 records** read block by block: one full block of
39 records (3120 bytes, residual 0) and one short block of 10 records
(800 bytes, residual 2320). `[tested: JOB01197, MVS/CE LAB, 2026-09-25]`

## Why it bites

A reader that trusts `DCBBLKSI` for every block returns the last block padded
with whatever the buffer held before — usually the tail of the *previous*
block, because the buffer is reused. The result is plausible text with
duplicated lines at the end of the member, no abend and no return code, which
is the worst shape a bug can have.

## The neighbouring trap

`DCBBLKSI` comes from the **first** data set of a concatenation
(`MVS-JCL-0001`). Reading a later library whose blocks are larger does not
produce a short block — it fails the READ into SYNAD. The arithmetic above is
only correct while the DCB's block size is the one the block was written
with.
