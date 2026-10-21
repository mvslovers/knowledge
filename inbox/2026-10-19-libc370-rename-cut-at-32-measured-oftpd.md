# libc370 rename(): a new name over 32 characters fails before 2.18.1 (measured, oftpd)

Source: oftpd session, 2026-10-19; records in oftpd `internals/m38-changes.md`
and `internals/dev1-changes.md` (PR mvslovers/oftpd#40). Platform: MVS 3.8j
(MVS/CE dev1, MVS/CE m38l/m38x, TK5 m38b/m38r).

## What was measured

OFTPD receives a file into a temporary data set and renames it to its final name
with libc370 `rename()` when the file is complete.

- **dev1, OFTPD `2253a7a`, linked with libc370 2.17.0.** A file relayed
  M38X -> M38L -> DEV1, virtual name `M38X.SVC.TO.DEV1.F`, final name
  `IBMUSER.OFTPIN.M38X.SVC.TO.DEV1.F` (**33 characters**). Console on dev1
  (read by the maintainer):
  `OFTP221E M38L: IBMUSER.OFTPTMP.T0000157 NOT RENAMED TO IBMUSER.OFTPIN.M38X.SVC.TO.DEV1.F`,
  then `M38X.SVC.TO.DEV1.F not accepted, EFNA 12`; the same for T0000158 (`.T`).
  Nothing was left on dev1: no `IBMUSER.OFTPTMP.*`, no `IBMUSER.OFTPIN.M38X.*`.
  The sender saw NERP reason 12 (m38x T0000010/11, m38l T0000019/20).
- **All five stands on OFTPD `7a9d9a9`, linked with libc370 2.21.0.** The same
  name arrived (m38x JOB00652, dev1 `IBMUSER.OFTPIN.M38X.SVC.TO.DEV1.F` and `.T`),
  and so did a 41-character one (`IBMUSER.OFTPIN.M38R.SVC.TO.DEV1.LONG.NAME`,
  m38r JOB00921) and a 35-character one on TK5 m38b. Each received data set was
  identical to its source.

## The mechanism (not read here; from MBT and libc370#590)

Before libc370 2.18.1, `rename()` writes the IDCAMS `ALTER <old> NEWNAME(<new>)`
statement past column 72, so the new name is cut at 32 characters. A 33-character
name cut there ends in a dot (`IBMUSER.OFTPIN.M38X.SVC.TO.DEV1.`), which is
invalid, so the ALTER and `rename()` fail. A longer name cut at a qualifier
boundary instead gives a valid but **shorter** name, and the rename "succeeds"
under the wrong name (MBT reports a case on dev1 on 2026-10-18). Fixed in
libc370 2.18.1 (libc370#590).

## What follows

- Any consumer that renames data sets with `rename()` needs libc370 2.18.1 or
  later; oftpd raised its floor to 2.18.1 in `mbt.toml`.
- A rename that returns 0 is no proof that the name is right on an older libc370:
  read the catalog for the full new name.
- Test names over 32 characters deliberately, both one that is cut after a dot
  and one that is cut at a qualifier boundary.
