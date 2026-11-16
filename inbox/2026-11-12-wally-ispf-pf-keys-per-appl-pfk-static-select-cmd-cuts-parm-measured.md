# Wally ISPF 2.2: PF keys per application, PFK() static, SELECT CMD(%x parm) cuts the last character

Date: 2026-11-12. Source: sdsf session (mvslovers/sdsf, help driver `src/isfhelp.c`),
measured in fresh throwaway MVS/CE containers (mvsce-target, mvsdev) over TN3270
with mbt's TSO test driver, user IBMUSER. Probe CLISTs in `SYS2.CMDPROC`, probe
panel in `SYSGEN.ISPF.PLIB`.

## Measured

- **`ZPFnn` can be read.** `ISPEXEC VGET (ZPF01 ZPF07 ZPF13) PROFILE` gives RC 0
  and `HELP`, `UP`, `HELP`, the ISPF defaults. The values are 255 bytes long and
  padded with blanks, so a CLIST `WRITE` of several of them in one line pushes
  the later ones off the screen.
- **The keys belong to the application.** `ZPF07 = HELP` stored by
  `VPUT (ZPF07) PROFILE` under applid ISP did **not** change PF7 in a dialog
  started with `NEWAPPL(ISF)`. Stored under applid ISF, through
  `SELECT CMD(...) NEWAPPL(ISF)`, it did: in SDSF, PF7 on the Status panel then
  showed SDSF's help. SDSF tells the Help key by VCOPY of `ZPFnn`, so this also
  shows that VCOPY gets the user's value, not only the default.
- **`PFK()` in a panel's `)INIT` returns the default keys only.**
  `PFK(HELP)`, `PFK(UP)`, `PFK(END)` and `PFK(LEFT)` gave `PF01`, `PF07`, `PF03`
  and `PF10`. After `ZPF07 = HELP` had been stored in the ISF profile,
  `PFK(UP)` still gave `PF07`, and so did a dialog started fresh with
  `NEWAPPL(ISF)` afterwards. So a panel cannot use `PFK()` to name the keys a
  user has set, as IBM's SDSF tutorial does.
- **`KEYS` typed into a command field not named ZCMD reaches the dialog.**
  SDSF's command field is ISFCMD; there `KEYS` was SDSF's `INVALID COMMAND`, and
  ISPF did not show its KEYS panel. A dialog with its own command field
  therefore offers no way to change its keys, unless it handles KEYS itself.
- **`ISPEXEC SELECT CMD(%name parm)` drops the last character of the parameters.**
  A CLIST `ZZECHO` (`PROC 1 P`, `WRITE <&P>`) showed:

  | Call | P received |
  |---|---|
  | `SELECT CMD(%ZZECHO ABCDEF)` | `ABCDE` |
  | `SELECT CMD(%ZZECHO ABCDEF )` | `ABCDEF` |
  | `SELECT CMD(ZZECHO ABCDEF)` | `ABCDEF` |
  | `SELECT CMD(%ZZECHO 'ABCDEF')` | `'ABCDEF` |

  The form without `%`, or a blank before the closing parenthesis, avoids it.
  The same cut made `ZPF07` become `HEL` and `U` in the first runs of the key
  measurement above.

## Consequence for SDSF

The help and tutorial texts keep naming the default keys (PF7, PF10, ...) and
say that these are ISPF's defaults (`ispplib/isfhhelp`); `PFK()` would not
show anything else. SDSF's Help-key detection through VCOPY of `ZPFnn` works
with keys a user has changed in the ISF profile.
