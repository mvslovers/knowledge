# VSAM on MVS 3.8j: SHOWCB FIELDS=FDBK returns only the reason code; the RPL feedback word has all three

Source: libc370 session, 2026-10-19/20. Issue mvslovers/libc370#680 (open,
the consequence for `vs->rc`), PR mvslovers/libc370#678 (merged, closes #625:
new `__vsfdbk()`; the PR body has the full job output). Platform: MVS 3.8j,
MVS/CE in an own throwaway container (`mvsce-target`). KB check before
writing: no document mentions SHOWCB, FDBK or the RPL feedback word.

## Finding

- `SHOWCB RPL=...,FIELDS=FDBK` on MVS 3.8j delivers only the feedback
  (reason) code, in the low-order byte. The return-code and component bytes
  are 0. libc370's `@@vsxerr.c` took the return code from byte 1 of that
  word, so `VSFILE.rc` was 0 after every request, including a missing key,
  a duplicate write and end of data. A first version of `__vsfdbk()` that
  also used SHOWCB FDBK got 0 there too.
- The RPL feedback word itself (RPL+X'0C', `RPLFDBWD`) holds all three:
  return code (RPLRTNCD, the value VSAM returns in R15), component code
  (RPLCMPON) and reason code (RPLERRCD). VSAM sets it on every request, so
  it always belongs to the last request.

## Measurement

Probe `test/mvs/tstvsfb.c` (libc370), JCL `jcl/recvvsfb.jcl` /
`jcl/tstvsfb.jcl`. IDCAMS defines a KSDS (KEYS(8 0), RECORDSIZE(80 80)) and
REPROs KEY00001..KEY00003. One handle, DYNAM/UPD, requests in this order:
(b) missing key, (a) good read, (c) duplicate write, (d) end of data.
RECEIVE JOB00018, run JOB00019 (container-local job numbers):

```
TSTVSFB GREEN 13/13   (__vsfdbk, reads RPL+X'0C')        CC 0000
TSTVSFB RED 7/13      (old interface, vs->rc etc.)        CC 0001

(b) r15 8 fdbk X'10'                   RPL feedback word X'14080010'
(a) r15 0 fdbk X'00' reclen 80 rba 80  RPL feedback word X'00000000'
(c) r15 8 fdbk X'08'                   RPL feedback word X'0A080008'
(d) r15 8 fdbk X'04' rba 160           RPL feedback word X'00080004'
```

In the RED step `vs->rc` (from SHOWCB FDBK) was `r15 0` for (b), (c) and
(d). The top byte of the RPL feedback word varies (X'14', X'0A', X'00',
X'07' on a repeated end of data) and is not part of the three codes used.

## Side observation from the same probe

The library's LERAD/SYNAD/EODAD stubs return to the request with their own
R15 (8/12/4), so an R15 captured after the request is synthetic: at end of
data it is 4 while VSAM's own return code (RPLRTNCD) is 8. Read RPLRTNCD,
not the R15 a wrapper sees.

## What it means for callers

- Do not use `SHOWCB FIELDS=FDBK` to get a VSAM return code on 3.8j; read
  the RPL feedback word (RPL+X'0C') directly.
- libc370: `VSFILE.rc` is always 0 on MVS 3.8j (documented in the Library
  Reference VSFILE table, fix undecided in #680). Use `__vsfdbk()`
  (`<mvs/vsam.h>`, merged, unreleased on 2026-10-20; next release after 2.23.0) for return, component and reason code,
  RECLEN and RBA of the last request.
- A request VSAM does not accept at all (R15 4, RPL already active) leaves
  the feedback word to the active request; the locked `vs*` forms avoid that.

## Update 2026-10-20 (later the same day)

- Caveat: in all measured RPL feedback words the component byte is 0 as
  well (X'14080010', X'0A080008', X'00080004'), so the measurement shows
  that SHOWCB FDBK drops the return code; whether it also drops a nonzero
  component code is not shown.
- libc370 #680 was fixed in 2.24.0 (PR #688): `VSFILE.rc`/`component` now
  come from the RPL feedback word. `__vsfdbk()` was released in 2.24.0.
