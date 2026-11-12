# Wally ISPF 2.2: HELP shows one panel, no tutorial navigation; ISPTUTOR on TK5 is LBTUTOR

Date: 2026-11-11. Source: sdsf session (SDSF clone, mvslovers/sdsf, issue #11),
measured in a fresh throwaway TK5 container (mvsce-target --dist tk5) over
TN3270 with mbt's TSO test driver (`mbt test --tso`), user HERC01.

## Setup

Test panels in SYS2.ISP.PLIB, started with a CLIST `ISPEXEC DISPLAY PANEL(ZZHT1)`:

- ZZHT1, an application panel: `)INIT .HELP = ZZHH1`, `&ZHTOP = ZZHT0`, `&ZHINDEX = ZZHIX`.
- ZZHH1, a help panel: `)PROC &ZSEL = TRANS(&ZCMD 1,ZZHHA *,'?')`, `&ZCONT = ZZHH2`, `&ZUP = ZZHT0`.
- ZZHH2, ZZHHA, ZZHT0, ZZHIX: plain pages.

## Measured

- **PF1 (HELP) on ZZHT1** displays ZZHH1, the `.HELP` panel.
- **On that help panel, Enter, `1` + Enter and PF3** all go straight back to
  ZZHT1. Wally ISPF evaluates none of ZSEL, ZCONT, ZUP, ZHTOP or ZHINDEX: its
  HELP is a single panel without navigation.
- This matches Wally's own documentation, `ISP.V2R2M0.DOC`:
  - `COMMANDS` lists HELP as Supported.
  - `CONTVARS` lists `.HELP` as Supported.
  - `ZVARS` lists ZCONT, ZHTOP, ZHINDEX, ZIND, ZUP and ZSEL as function variables.
  - `FUTURE` says of help panels: "The author is struggling to get excited writing these".
- **TK5 adds a tutorial driver** in `SYS2.ISP.LLIB`: members `LBTUTOR` and
  `ISPTUTOR` (plus LBHELP), by Larry Belmontes. `ISPTUTOR` is LBTUTOR:
  started as `ISPEXEC SELECT PGM(ISPTUTOR) PARM(ZZHH1)`, its messages read
  `LBTUTOR 13 : RC=0012 ...`.
- TK5's primary menu has `T,'PGM(LBTUTOR) PARM(LBT00000)'`, with the IBM line
  `PGM(ISPTUTOR) PARM(ISP00000)` commented out.
- **LBTUTOR navigation, measured** with both names, same result:
  - **Works:** a topic number (ZSEL); Enter on a menu panel goes to the next
    topic (the first ZSEL entry, as in IBM's tutorial); PF10 goes back to
    the previous panel; PF7 goes to the ZUP panel; PF3 leaves with SELECT RC 0.
  - **`T` fails:** LBTUTOR wants `ISP00000` and ignores the ZHTOP set in the
    application panel (`RC=0012 Panel not found:ISP00000`).
  - **`I`** had no visible effect.
- Neither the DEV1 stand nor MVS/CE was found to have `SYS2.ISP.LLIB` or
  LBTUTOR. A product that wants IBM-style help (ZSEL, ZCONT, ZUP chains)
  under Wally ISPF everywhere has to drive the help panels itself.

## What a dialog sees of the Help key (second run, same day, new container)

Panel ZZE1 with no `.HELP`, `)PROC &ZZPFK = .PFKEY`, displayed from a CLIST.
The CLIST then wrote LASTCC, ZVERB (after `VGET (ZVERB)`), ZZPFK and ZCMD:

| Key | DISPLAY RC | .PFKEY | ZVERB | ZCMD |
|---|---|---|---|---|
| PF1 (HELP) | 0 | PF01 | blank | blank |
| PF13 (HELP) | 0 | PF13 | blank | blank |
| `HELP` typed into ZCMD | 0 | PF00 | blank | blank (ISPF took it) |
| PF3 (END) | 8 | PF03 | blank | END |
| Enter | 0 | PF00 | blank | blank |

- Without `.HELP`, the Help key **returns to the dialog** with RC 0, like
  Enter. Only `.PFKEY` in `)PROC` tells it apart; ZVERB stays blank, unlike
  RETRIEVE, where it carries the verb. To learn the key's command, the dialog
  reads the system variable `ZPFnn` for the key `.PFKEY` names.
- `HELP` typed into **ZCMD** is consumed by ISPF and leaves nothing. A
  command field of another name (SDSF's ISFCMD) gets `HELP` through as text.
- With `.HELP` set, PF1 shows that panel (see above). PF3 there redisplays
  the application panel, and the next Enter ends the DISPLAY with RC 0.

## Consequence for SDSF

SDSF drives its help and TUTOR panels itself in ISFISP: PF1/HELP and TUTOR
are caught by the program, which displays the panels in a loop and evaluates
ZSEL/ZCONT/ZUP/ZHTOP/ZHINDEX with a back stack. Not dependent on LBTUTOR.
