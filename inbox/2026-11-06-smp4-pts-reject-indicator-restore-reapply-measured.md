# SMP4: the REJECT indicator of the PTS SYSTEM entry decides whether RESTORE deletes a usermod for good; `DEL SYS REJECT` switches it off

Source: removal of usermod ZMG0003 (mvslovers/usermods, `zmg0003/`), a usermod with a full
`++MOD(IKJCT441)` on top of ZP60038, discussed with the TK5 maintainer, who pointed at "the SMPPTS
system entry". Measured 2026-11-05 and 2026-11-06.

Platform: SMP4 `HMASMP LVL 04.48`, own throwaway containers, each started fresh. Container results,
not stand results.

- TK5 image `ghcr.io/mvslovers/tk5@sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf59...`
  (the same digest prefix as the TK5 Update 5 image in other inbox notes)
- MVS/CE, the default image of `mvsce-target`; digest not recorded in these runs

Job numbers are container-local.

Touches `MVS-SMP-0013`, which says the syntax to change these indicators is "not established" after
seven failed `REP` variants, and `MVS-SMP-0005`, which notes that RESTORE takes the MCS away.

## Ingested 2026-11-09 (see MVS-SMP-0017)

The `DEL SYS REJECT` / `ADD SYS REJECT` syntax and the `REJECT=YES`/`NO` RESTORE-and-re-APPLY
outcome were reproduced on TK5 with ZP60014 and ZP60038 and moved to `MVS-SMP-0017`. What follows
is the part not reproduced (ZMG0003 specifics, MVS/CE, SUP form, the instrument errors); the
manual quotation (GC28-0673-6) could not be checked, the manual was not at hand.

## The REJECT indicator does not help with unaccepted requisites

The same RESTORE on fresh MVS/CE ended RC 12 and restored nothing, before anything could be deleted:

```
HMA3022 ** RESTORE PROCESSING TERMINATED FOR SYSMOD ZP60014 - REASON = MISSING/NOGO REQUISITES:
HMA3590     --- UY16532 PRE
HMA3590     --- UY17021 PRE
HMA3022 ** RESTORE PROCESSING TERMINATED FOR SYSMOD ZP60038 - REASON = MISSING/NOGO REQUISITES:
HMA3590     --- UY01301 PRE
HMA3590     --- ZP60014 PRE
HMA3022 ** RESTORE PROCESSING TERMINATED FOR SYSMOD ZMG0003 - REASON = MISSING/NOGO REQUISITES:
HMA3590     --- ZP60038 PRE
```

My reading, not established: RESTORE wants every requisite that is not accepted in the same select list.
On TK5 those PTFs did not stop it. Measured on MVS/CE so far: accepting the chain makes `RESTORE` of ZMG0003 alone RC 0. Restoring
the whole chain under `REJECT=NO` on MVS/CE was not measured.

## SUP does not lift this

The maintainer's form: `++VER(Z038) FMID(EBB1102) PRE(UY01301,ZP60014) SUP(ZP60038)`, in our build with
ZP60038's `++JCLIN` and `++MACUPD(SGIKJ441)` added. Measured 2026-11-05.

`RESTORE SELECT(ZMG0003)`, with step IEBCOPY left out:

| | TK5 | MVS/CE |
|---|---|---|
| nothing accepted | RC 12, `ZP60038 SUPED`, `ZP60014 PRE` | RC 12, `ZP60038 SUPED`, `UY01301 PRE`, `ZP60014 PRE` |
| requisites accepted, ZP60038 not | RC 12, `ZP60038 SUPED` | RC 12, `ZP60038 SUPED` |
| ZP60038 accepted too | RC 0 | RC 0 |
| ZP60038 restored before the install | RC 0 | RC 0 |

The message reason is `RESTORE LIST INCOMPLETE`. My reading: a superseded SYSMOD counts like a requisite
for RESTORE, so applied only, it must be in the list. The three-SYSMOD RESTORE below fits this.

The two forms produce the same module: text 50408 bytes on TK5, 50136 on MVS/CE, 14 CSECTs and 224
relocations on both, the comparison `EQUAL` with both of its controls firing.

With the JCLIN inside, the SUP form installed RC 0 on a system without ZP60038 (`gone` mode, TK5 and
MVS/CE). The module in that mode was not read here. The PRE form fails there with `ZP60038 PRE`.

On TK5 under `REJECT=NO`, `RESTORE SELECT(ZMG0003,ZP60014,ZP60038)` of the SUP form behaves as in the table
further up, and the installed IKJPTGT is line-identical to the PRE form (1576 lines, no difference).

## Instruments that answered wrongly on the way

- **`USERMODS` is a syntax error on APPLY**: `APPLY SELECT(...) USERMODS .` gives `HMA2033 ** SYNTAX ERROR IN
  CONTROL STATEMENT AT COL 32`, RC 12, while ACCEPT requires the operand (without it HMA3652). It came from
  our own first run; its APPLY results say nothing about SMP's behaviour.
- **The stored decks in `mvs38src/ptf/mvsce/ZP600*.mcs` cannot be received**: pulled over mvsMF in text
  mode, each object card is 4 bytes (`X'02'` and the tag). 440 cards in ZP60014, 28 in ZP60038. `mvsce-bin`
  holds no ZP6 members. A binary pull from SMPPTS is needed, and it must happen before a RESTORE under
  `REJECT=YES`.
- **A comparison script that discards the job's return code**: my first comparison had `EXEC` in its member
  list but only `SYS1.LPALIB` on SYSLIB, where `EXEC` does not live. AMBLIST answered `AMB108I EXEC NOT FOUND`
  and RC 8, and my script threw that away and printed "same as before install: True" from the IKJPTGT lines
  alone. Noticed through `LMOD=EXEC - LIBRARY=CMDLIB` in the SMP output; the RC 8 itself only when writing this
  note. IKJPTGT in those runs is listed and valid, `EXEC` was not compared there.

## Limits

- One run per form and case.
- `REJECT=NO` measured on TK5 only.
- The combined form, `DEL SYS REJECT` and RESTORE in one job, was not measured; the runs used separate jobs.
- `EXEC` compared only in the run without ZMG0003, which covers neither form of the usermod.
- Raw output is in the session scratchpads and will not last.
