---
id: ECO-0014
title: Testing a stdio read-error guard on MVS — write a temporary data set, then read it through a second DD with a different DCB
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/ufsd PR #111 (merged 2026-10-20, closes #69): the technique and the proof table, MVS/CE container, libc370 2.24.0, mbt test --mvs, batch and TSO"
  - "ufsd test/mvs/tstufsio.c (main branch, 2026-10-22): make_ds(), read_dd(), alloc_dd(), the file header comment"
verified_on: 2026-10-20
applies_to: [ufsd, libc370, mbt]
tags: [test, ferror, fgets, read-error, dcb-override, jfcb, rdjfcb, dynalloc, temporary-data-set, bsam, wrong-length-block, tstufsio]
related: []
---

## The problem

Since libc370 1.0.4 an uncorrectable read error comes back from `fgets()` as NULL,
exactly like end of file. A loop that reads to NULL and does not test `ferror()` reports
success on a damaged input. To prove the guard works, a test needs a read that
**fails** on MVS, not a mock. `[source: tstufsio.c header]`

## The technique `[tested]`

1. **Write the data set in the test, block by block, with BSAM.** Allocate a temporary
   data set with `dynalloc()` (`DISP=NEW`, no data set name, RECFM=U, block size 3120)
   and write two blocks: the first 80 bytes, the second 3120 (broken) or 80 (good).
   No fixture and no hand-written JCL are needed.
2. **Read its name and volume from the writer DD's JFCB.** `rdjfcb()` after the writes
   gives `jfcbdsnm` and `jfcbvols`; the system made them up for the temporary data set.
3. **Close the writer DCB but keep its DD allocated.** The temporary data set lives
   until the step ends, and the writer DD is its only owner.
4. **Allocate a second DD, `DISP=SHR`, on that name and volume, with the DCB you want:**
   RECFM=F, LRECL=80, BLKSIZE=80. Open it with `fopen("DD:...")` or `freopen(...,
   stdin)`. The first READ gets the 80-byte block and the second READ meets the
   3120-byte block, which does not fit the DCB, and fails.
5. **Check the first block was delivered.** The vector must fail on the second block:
   a vector that fails on the first would also make an unguarded loop return an error
   (from the missing first statement), which proves nothing. Here the unguarded loop ends
   "as at end of file" with the first statement parsed, and reports success.
6. Run each case twice, once with a good data set (the guard must stay quiet, all input
   parsed) and once with the broken one.

`freopen()` on a stream that is still open closes the old file itself; the test uses that
to switch `stdin` from the good to the broken DD (`[source: tstufsio.c comment]`).

## The proof the guards work `[tested]`

UFSD's two guards (`ufsd_cfg_read()` on `DD:UFSDPRM` returns 8 with UFSD106E;
`parse_sysin()` on `SYSIN` returns 8 with UFSFMT17E), libc370 2.24.0, MVS/CE container,
`mbt test --mvs --only TSTUFSIO`:

| Run | Batch | TSO | Assertions |
|---|---|---|---|
| guards in place | CC 0 | CC 0 | 48 PASS, 0 FAIL |
| `ferror(fp)` and `ferror(stdin)` replaced by constant 0 | CC 1 | CC 1 | 44 PASS, 4 FAIL |

In the failing run exactly the two return-value checks fail per environment
(`ufsd_cfg_read returns 8 (got 0)` and `parse_sysin returns 8 (got 0)`); the checks
that the first statement was read before the error still pass.

## Not examined

The source of the data set name and volume for a **second** SVC 99 allocation: the test
uses the JFCB route above. Other routes to a temporary data set (for example by `&&name`)
and the behaviour of `fclose(stdin)` followed by `freopen()` on it were reported in the
inbox note but not verified at ingest, and are not claimed here.
