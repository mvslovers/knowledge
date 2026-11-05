# ISPF logical screens share one ECT; ECTIOWA is swapped, ECTENVBK is not. Input stack elements sit at fixed addresses per depth

Measured 2026-11-04 on a throwaway TK5, ISPF V2R2M0, unchanged ZP60038. Setup jobs
JOB00045 and JOB00046. Program, job builder and raw lines: mvslovers/usermods,
`zmg0003/test/ispf/ZMGWHO.ASM`, `mkwho.py`, `results-screens.txt`. Not repeated on MVS/CE.

## Findings

1. **One ECT for all logical screens.** `LWAPECT` and `CPPLECT` were the same value at
   READY and in both screens (X'A7CF4').
2. **`ECTIOWA` (ECT+4) is per screen.** READY X'A9FC8', screen 1 X'A9F98', screen 2
   X'187FD0'. ISPF changes the pointer inside the one ECT when it switches screens, and
   each screen has its own input stack.
3. **`ECTENVBK` (ECT+X'30') is not per screen.** Control: `ZMGSET` stored a marker there in
   screen 1. Screen 2 read that marker. After `ZMGSET` in screen 2, screen 1 read the
   marker of screen 2. So one word serves all screens, and a REXX environment published
   there is visible from the other screen.
4. **Each screen has its own task tree.** A command in screen 1 had parent/grandparent
   X'994D88'/X'9A2780', in screen 2 X'98F6A8'/X'98FDD8'. The current TCB is the command's
   own and its address gets reused (one command in screen 2 ran at the TCB address a
   command of screen 1 had before), so it does not identify a screen.
5. **Input stack elements are an array: the address says the depth, not the instance.**
   At READY: terminal element X'A9FD8', CLIST at depth 1 X'A9FDC', nested CLIST X'A9FE0'.
   Every later CLIST at a depth got the same address, also after a command abend (S0C1
   in a CLIST, the stack was flushed to READY) and after an attention. First byte: X'80'
   terminal, X'4A' CLIST.
6. **Attention at a CLIST `READ` did not end the CLIST** (no attention exit): PA1 gave
   `READY`, the element stayed, and the next input line was taken by the `READ`. One case.

## What follows

- An IOSTELM value recorded earlier cannot tell whether the same procedure is still
  running: a later CLIST at the same depth has the same address. An "exec is running"
  word holding IOSTELM is only as good as its cleanup after an abend.
- The value does separate screens at a given moment, since the screens have different stacks.
- A single anchor in `ECTENVBK` does not fit exec runs in two screens, which do not nest.
  Not measured with a real REXX exec in two screens; this is derived from finding 3.

## Addendum: real BREXX/370 execs in two screens

Same day and system, BREXX/370 `feature/irxexcom` (b6862b0), ZMG0001, the IKJCT441 usermod (ZMG0003, then called ZMG0004,
branch `zmg0003/ispf-test`), no trace. Raw lines: `zmg0003/test/ispf/results-twoscreens.txt`. Setup
jobs JOB00053, JOB00054. Single-screen control: panel input reaches the exec.

| Case | ECTENVBK when screen 1 continues | Result |
|---|---|---|
| Both execs alive, back to screen 1, `NEW1` visibly typed into the field | environment of screen 2 | `DISPLAY` RC=0 but the variable stays `OLD1`: input lost silently. The next `VGET` abends S0C1 in ISPEXEC with R15=X'28' (40), caught by the BREXX ESTAE |
| Exec 1 ends while exec 2 is alive; then exec 2 ends | after both: X'24C0A0', the environment of exec 1, which has ended | A stale pointer stays in ECTENVBK. Whether reading it abends depends on the storage; not settled here |
| Exec 2 already ended on return | environment of screen 1 | Input arrives |
| A CLIST dialog waits on screen 2 | environment of screen 1 | Input arrives; the CLIST continues normally |

The S0C1 with R15=40 is probably ISPF's reaction to RC=40 from IKJCT441; ISPF was not
disassembled for this. Only two live REXX dialogs fail, and only exec 1's first return shows
no error at all.

## Addendum: attention during a running exec

BREXX/370 `feature/irxexcom` (b6862b0) has no STAX exit. PA1 during a loop in a published exec,
TK5, same day. Raw lines: `zmg0003/test/ispf/results-attention.txt`.

- **READY:** `READY` appears and the next command runs under a new task. The exec is gone, but
  ECTENVBK still holds its environment (X'1720A0'), also several commands later.
- **ISPF, option 6:** `COMMAND TERMINATED`. ECTENVBK still holds the environment (X'24C0A0').
  The next plain CLIST dialog ends with `PROCESS HAS ABENDED`. The same dialog worked in a
  session without the attention. Abend code not captured.

So BREXX's ESTAE path does not clean up here: any product that publishes in ECTENVBK needs its
own attention handling.
