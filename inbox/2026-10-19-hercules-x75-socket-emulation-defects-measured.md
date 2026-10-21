# Hercules X'75' socket emulation: six measurements (select, DNS, GETERROR, RECV, slots, SELECT bound)

Source: libc370 session, 2026-10-19. Issues mvslovers/libc370#144, #161, #162,
#163, #164, #165 (all closed by the probe PRs #655, #656, #657; each PR body has
the full job output). Platform: MVS 3.8j, MVS/CE in throwaway local containers
(`mvsce-target`, Apple `container`), NUMCPU 1. Emulator: SDL Hyperion main,
image label `io.mvslovers.hercules.ref` = a742398 (2026-10-13); `tcpip.c`/`tcpip.h`
identical to hyperion 16e62c4. Probes: libc370 `test/mvs/tst75sel.c`,
`tst75dns.c`, `tst75err.c`, `tst75prt.c`, `tst75slt.c`, `tst75bnd.c` (build and
reading instructions in each header). All defects are in the emulator, not in
libc370.

## 1. select() misses a readable socket (#144) - defect, guest-reachable

X'75' sockets have a guest slot number and a host descriptor. Both are allocated
lowest-free, so as long as only the guest opens sockets the two orders stay in
step (control: 4 pairs, 8 rounds of close/reopen, select() always right).
When the Hercules process itself holds a descriptor without a guest slot
(TN3270, HTTP console 8888, sockdev), a later socket gets a low slot but a high
descriptor. select() over {C, H} then misses C although FIONREAD = 1:
4 of 4 runs (`B#0 P=4 C=4 H=6 port=8888 layout=C<H`, `{C,H} rc=1 C:1/0`).
{C} alone is reported correctly. The probe triggers the state from the guest by
connecting to Hercules' own HTTP port.

## 2. gethostbyname()/gethostbyaddr() stop the emulated CPU (#163) - defect

An observer subtask (STCK + STIMER 0.01 s loop) recorded its largest gap while
the main task looked up fresh names that fail slowly (`h<n>.<a>.<b>.6.in-addr.arpa`,
unique per run so no cache answers). Gap = lookup time within 4 ms
(5026/5030 ms, 4158/4160 ms); fast lookup 2 ms gap 10 ms. With one CPU the whole
guest stands still for the duration of the host resolver call. The step's
IEFACTRT line showed 00:00:16.34/00:00:26.85 (read as CPU/elapsed, which would
mean the stalled time is charged as CPU; the field order was not checked). The length depends on the host's resolver;
with NUMCPU > 1 the stall can hide on the other CPU.

## 3. Socket errors: per-slot word never cleared, global word shared (#161)

- GETERRORS (code 2) reads `Cerr[slot]`. CLOSE resets the slot but not
  `Cerr[]`: a new socket on the same number reads the previous holder's last
  error (98 of 98). No crossing between two live sockets (0 of 50).
- GETERROR (code 3) reads `CerrGen`, one word for the whole emulator, written
  only by failing SOCKET, GETHOSTBYNAME, GETHOSTBYADDR. Two jobs in parallel
  (two initiators, 0.16 s between own error and read): each read the other's
  code in 297 and 296 of 300 rounds. So `errno` after a failing `socket()` in
  libc370 (`@@75sock.c`) can be another address space's error.

## 4. Partial RECV (#165) - no defect

A RECV asking 636 bytes when 256 are there returns 256 and consumes them;
the next call returns the remaining 380. Forced splits 1..635 (24 rounds) and
20 no-wait rounds: no replay, no corruption, FIONREAD 0 afterwards. Limit: both
ends in the same guest over host loopback.

## 5. Leaked conversations abort Hercules (#162) - defect

Issuing only the first of the two X'75' instructions of a RECV on an idle,
unconnected socket leaks the talk and two `map32` slots each time (call 1 slot 0,
call 467 slot 932). At about 467 leaks (~934 slots), before the 1024-entry table
is full and before `find_slot()` could alias at `Ccom-1`, the Hercules process
aborts: `Fatal glibc error: malloc.c:2601 (sysmalloc): assertion failed`.
Root cause of the heap corruption not investigated.

## 6. Unchecked aux2 in SELECT kills Hercules (#164) - defect

SELECT subcode 5 loops `i < aux2` over `Ccom_han[1024]` without a bound.
A hand-built parameter list: aux2 = 8, 1025, 1032 survive (rc 0, the overread
stays in mapped memory); aux2 = 2048 ends Hercules with SIGSEGV (exit 139).
libc370 passes a valid maxsock and is not exposed.

## Method note

Hercules block-buffers `/logs/hercules.log`; when the process crashes, the tail
(and mvsMF with it) is lost. The crash probes write a high-volume WTO trail to
force the log to disk, and the results were read from the container's console
log directly, not via mvsMF.
