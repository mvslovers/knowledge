# ISPF V2R2M0: VGET after VPUT without a DISPLAY depends on the values; a failed VGET blanks the variable

Measured 2026-11-05 on a throwaway TK5, ISPF V2R2M0, same logon, `ISPEXEC SELECT CMD(%name)`.
BREXX/370 `feature/irxexcom` 9dbcf46, ZMG0001 and the REXX-capable `IKJCT441` (usermod `ZMG0003`,
then called ZMG0004) installed; the CLISTs go through its unchanged CLIST path. Source: mvslovers/usermods, branch
`zmg0003/ispf-test`, `zmg0003/test/ispf/results-after.txt` (case `NESTCTL`), execs in
`zmg0003/test/ispf/lib/`. Not repeated on MVS/CE. No run against the unchanged `ZP60038`
`IKJCT441` for exactly these four members.

## Finding 1: `VPUT V SHARED`, change V, `VGET V SHARED`, no DISPLAY between

| Member | Language | Value at VPUT | Value at VGET | V after VGET | VGET RC |
|---|---|---|---|---|---|
| `XU` | REXX | `INNER` | `CLOBBER` | `CLOBBER` (not fetched) | 0 |
| `XB` | CLIST | `INNER` | `CLOBBER` | `CLOBBER` (not fetched) | 0 |
| `XA` | REXX | `FROMXA` | `OLD` | `FROMXA` (fetched) | 0 |
| `XC` | CLIST | `FROMXC` | `OLD` | `FROMXC` (fetched) | 0 |

The members ran in the order XU, XC, XB, XA, so the two outcomes alternate: it is not a matter of
the order or of earlier members. It is not a matter of the language either. RC=0 in all cases, so
the return code does not show it.

**Not isolated:** in both failing cases the value at VGET is longer than the value at VPUT and in
both working ones shorter. That is a pattern in four lines, not a measured cause; the lengths were
not varied on their own.

## Finding 2: a VGET that fails blanks the variable

`SET &NOVAR = OUTER`, then `VGET (NOVAR) SHARED` for a variable not in the pool: RC=8 and NOVAR is
empty afterwards, in a CLIST (`XV`) and in REXX (`XR`).

## Related

`zmg0003/README.md`, "Open defect": a variable that first appears after the first `ISPEXEC` of a
dialog does not get its value back from `VGET`. That is a different condition: in all four
members above the variable exists before the first `ISPEXEC`.
