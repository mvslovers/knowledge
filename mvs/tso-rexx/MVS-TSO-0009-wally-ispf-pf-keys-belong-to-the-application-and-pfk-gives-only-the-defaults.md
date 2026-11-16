---
id: MVS-TSO-0009
title: Wally ISPF 2.2.000 — ZPFnn is stored per application ID and PFK() in a panel returns only the default keys
status: tested
platform: [mvs38j]
sources:
  - "Reproduced 2026-11-16 in a throwaway MVS/CE 3.0.0 container over TN3270 with mbt's TSO test driver (`mbt test --tso`), user IBMUSER, Wally ISPF V2.2.000, primary option 6. CLISTs ran `ISPEXEC VGET (ZPF01 ZPF07 ZPF13) PROFILE`, `ISPEXEC VPUT (ZPF07) PROFILE` and `ISPEXEC SELECT CMD(name) NEWAPPL(ISF)` and wrote what they read to a file; panel ZZE2 (own command field ZZCMD, `)INIT &KUP = PFK(UP)` and the same for HELP, END, LEFT, `)PROC &ZZPFK = .PFKEY`) was displayed in a CLIST loop"
  - "Wally's SYSGEN.ISPF.DOC(ZVARS), read 2026-11-16: ZPF01 and ZPF13 default HELP, ZPF03 END, ZPF07 UP, ZPF10 LEFT, all 255 bytes, pool SYS"
  - "Reported measurement from the SDSF clone project (mvslovers/sdsf, issue #68 and #69), 2026-11-12; parts not reproduced are listed below"
verified_on: 2026-11-16
verified_platforms: ["MVS/CE 3.0.0 (throwaway container)"]
applies_to: [sdsf]
tags: [ispf, wally, pf-keys, zpf, pfk, vget, vput, profile, applid, newappl, keys, dialog]
related: [MVS-TSO-0008, MVS-TSO-0010]
---

## The claim

In Wally ISPF V2.2.000 the key settings `ZPF01`...`ZPF24` are part of the
**profile of an application ID**. A dialog started with `NEWAPPL(ISF)` has its
own set; what is stored under ISP does not reach it. The function `PFK()` in a
panel's `)INIT` does not follow the stored values: it returns the default keys.
`[tested]`

## ZPFnn can be read and is per application

`VGET (ZPF01 ZPF07 ZPF13) PROFILE` ends RC 0. The values come back padded
with blanks (the document lists a length of 255): in a 80-byte record written
by a CLIST the closing `>` of `ZPF01=<HELP` was cut off, while a `ZPF07` that the
CLIST itself had stored with `VPUT` came back without padding and kept its `>`.
`[tested]`

Storing a value under one application and reading under the other:

| Step | Applid | Result |
|---|---|---|
| `SET &ZPF07 = UP`, `VPUT (ZPF07) PROFILE` | ISP | RC 0 |
| `VGET (ZPF07) PROFILE` | ISP | `UP` |
| `VGET (ZPF07) PROFILE` in `SELECT CMD(...) NEWAPPL(ISF)` | ISF | `HELP`, stored there earlier |

The ISF value stayed `HELP` after ISP's `ZPF07` was set to `UP`, so the two
profiles are separate. `[tested]`

With `ZPF07 = HELP` in the ISF profile, PF7 in a dialog running under ISF ended
the `DISPLAY` with RC 0, `.PFKEY` PF07 and ZVERB blank, which is the Help-key
return described in [[MVS-TSO-0008]]. The same panel did not show a different
`.PFKEY` for PF7 in any phase. Whether PF7 returned something else while the
ISF profile still had `UP` was not measured in a clean state.

## PFK() returns the default keys

Panel ZZE2 showed, after `&KUP = PFK(UP)`, `&KHELP = PFK(HELP)`, `&KEND = PFK(END)`
and `&KLEFT = PFK(LEFT)`, in three successive dialogs under `NEWAPPL(ISF)`:

```
Panel ZZE2.  UP=PF07 HELP=PF01   END=PF03  LEFT=PF10
```

Every time, even though `VGET (ZPF07)` in the same application read `HELP`
(`PFK(UP)` would name PF7, but PF7 meant Help). `[tested]`

So a panel cannot use `PFK()` to name the keys a user has set. A dialog that must
know what a key stands for reads `ZPFnn` for the key `.PFKEY` names, with `VCOPY`
or `VGET`. The SDSF clone project reports that it recognises the Help key this
way and that the values a user stored under ISF are the ones it sees; the
detection code was not run here. `[assumed]`

## KEYS typed into a command field not named ZCMD reaches the dialog

ZZE2's command field is ZZCMD. Typing `KEYS` there and pressing Enter ended the
`DISPLAY` with RC 0, `.PFKEY` PF00, and the dialog read `ZZCMD=KEYS`; the next
screen was ZZE2 again, not an ISPF KEYS panel. A dialog with its own command
field therefore gets no key-definition panel from ISPF unless it handles `KEYS`
itself. `[tested]`

Open observation: `KEYS` typed into **ZCMD** of a panel without a help or keys
setup (ZZE1) produced the "ISPF SERVICE ERROR DISPLAY" screen: service
`DISPLAY`, return code 20, panel `ISPERROR`, applid ISP. The cause was not
found; it was not checked whether the KEYS panel exists in this installation.
Do not read it as "KEYS works in ZCMD" or as "KEYS is broken".

## Not reproduced

- The report says that in SDSF, PF7 on the Status panel then showed SDSF's help
  when `ZPF07 = HELP` was stored through `SELECT CMD(...) NEWAPPL(ISF)`, and
  that the same value stored under ISP left PF7 alone. SDSF was not run; the
  per-application separation was shown through `VGET` instead.
- The report gives the value length as 255 bytes. Here the padding was seen only
  through the cut record; a CLIST `&LENGTH` of `ZPF01` gave 4, so CLIST variables
  lose trailing blanks and say nothing about the stored length.
