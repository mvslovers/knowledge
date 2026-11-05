# Reading a freed subpool 1 chunk abends S0C4-11: a block cannot hold its own "who owns me" word

Measured 2026-11-05 on throwaway TK5 and MVS/CE containers. Program and results:
mvslovers/usermods, branch `zmg0003/ispf-test`, `zmg0003/test/ZMGDRV.ASM` (operand `F`, label
`TESTF`), `test/mktest.py` (step `TMPF`), `test/results-tk5.txt`, `test/results-mvsce.txt`.

## Finding

A TSO command processor does `GETMAIN` of 36,864 bytes from subpool 1, `FREEMAIN` of the same
area, then reads the first byte. The read abends S0C4 with reason 11 (page translation). The
line the program writes after the read (`F3 READ WORKED, NO ABEND`) does not appear.

The chunk addresses were X'AD000' and X'9D000' on the two systems: the area starts on a page
boundary and covers whole pages.

## What follows

A structure that must be inspected after its owner may have ended cannot carry the owner's
identity inside itself: a task's subpool 1 storage goes away with the task, and looking there
abends rather than returning old data. This is what happened to the design of `IKJCT441`
(usermod `ZMG0003`): the owner TCB moved from the chunk header to ENVBLOCK+X'138', which outlives the
chunks. Before the change, one ISPF logical screen would have abended when it looked at a chunk
of the other screen's ended task.

## Not measured

- Smaller sizes, or areas that share a page with storage still allocated. A smaller freed area may
  well read without an abend, so the abend must not be relied on as a detector of freed storage.
- The case of a task that ended, as opposed to an explicit `FREEMAIN`. The test frees explicitly in
  one task.
- Whether a page released here is stolen or merely invalidated. Only the abend code was recorded.
