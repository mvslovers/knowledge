# Hercules X'75' SEND: a restarted copy above 256 bytes corrupts the data on an unfixed emulator

Source: libc370 session, 2026-10-19/20. Issue mvslovers/libc370#160 (closed),
PR mvslovers/libc370#683 (merged; full job output in the PR body). Upstream
host-side fix: SDL-Hercules-390/hyperion issue #884 / PR #885 (merged
2026-09-06). Platform: MVS 3.8j, MVS/CE in an own throwaway container.
KB check before writing: not covered. The 2026-10-19 inbox note
`2026-10-19-hercules-x75-socket-emulation-defects-measured.md` has six other
X'75' defects (select, DNS, GETERROR, partial RECV, slots, SELECT bound) but
not the restart defect; this note is an addition, not a duplicate.

## Finding

X'75' copies data in 256-byte segments and the instruction is restartable.
On SEND the guest buffer is the source. When a page translation exception
on the guest buffer hits after at least one segment has been copied, the
instruction is re-executed: the guest side resumes where it stopped, but an
unfixed emulator recomputes the host pointer from `map32[R2]` and writes the
remaining bytes to the START of the host buffer. The peer receives the
right length with the wrong content: the tail shifted down over the head,
leftover host memory where the tail belonged. No error is reported.

A copy of 256 bytes or less is immune: a single segment either faults
having copied nothing (restart from the start is correct) or completes.
This is the SEND mirror of the RECV-side defect behind libc370#154.

## Measurement

Probe `test/mvs/tst75sst.c` (libc370), JCL `jcl/recv75sst.jcl` /
`jcl/tst75sst.jcl`. Each round fills a send buffer with an `i % 251`
pattern, releases one page `bound` bytes into it with PGRLSE (SVC 112,
verified to work first), sends the whole buffer with `send()` over a
loopback pair the probe owns both ends of, and the receiving end compares.
6 cases (len/bound 1024/0 control, 300/256, 1000/512, 1000/600, 4096/2048,
32000/16384), 5 rounds each. One job (JOB00019, container-local), GREEN
step = capped `send()`, RED step = library before the cap.

Container Hercules built from `mvslovers/hyperion` branch
`diag/x75-restart-trace` f1f1f9d1 (no host-side fix, plus a restart trace):

```
RED:   +TST75SST len=1024 b=0 intact first=1024 calls=1   (control)
       +TST75SST len=300 b=256 r=0 first_bad=1 replay_from=256:Y
       +TST75SST len=1000 b=600 r=0 first_bad=0 replay_from=512:Y
       +TST75SST len=32000 b=16384 r=0 first_bad=1 replay_from=16384:Y
       +TST75SST FAILED (25 of 30 rounds)                  RC 0008
GREEN: +TST75SST len=300 b=256 intact first=256 calls=2
       +TST75SST len=32000 b=16384 intact first=256 calls=125
       +TST75SST PASSED (30 rounds)                        RC 0000
```

`replay_from=N:Y` = the peer's bytes from offset 0 are the send buffer from
offset N on (the restart signature). Bound 600 replays from 512: the
straddling segment faults before it copies a byte.

Hercules restart trace of the same job: RED had 25 SEND restarts after a
completed segment (`dir=0 done=256/512/2048/16384`), one per failed round.
A trace line reads `X75 restart 7 (3 after a completed segment): dir=0
left=488 done=512 ...` (format as in the probe header). GREEN had about 29 SEND restarts, all `done=0`: the fault still
happens, the cap moves it to a segment start where restarting is correct.

Control: stock `ghcr.io/mvslovers/mvsce:latest` (Hercules a742398, contains
the upstream fix): RED and GREEN both 30/30.

## What it means for callers

- A guest cannot detect whether the emulator has the fix (no return value,
  status or function code distinguishes it). Code that must be correct on
  any Hercules caps every X'75' SEND and RECV at 256 bytes.
- A passing guest-side test does not prove a fixed emulator: it passes also
  when no fault fell after a completed segment. Only the emulator-side trace
  separates the two.
- libc370: `recv()` caps at 256 since #154 (PR #166); `send()` passes at
  most 256 bytes per call and returns the short count, never 0 for a
  non-empty request, since PR #683 (merged, unreleased on 2026-10-20; next release after 2.23.0). Callers must loop
  on a short positive `send()` return.
