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

## The syntax

From GC28-0673-6, OS/VS SMP System Programmer's Guide (Sep 1980), section "UCL - SMPPTS SYSTEM Entry",
quoted verbatim:

> When the PTS SYSTEM entry is created, the REJECT indicator is set. To reset the indicator requires a
> second UCL statement specified as "DEL SYS REJECT.".

Also, in the RESTORE section:

> When a SYSMOD is successfully restored and the REJECT indicator is on in the PTS SYSTEM entry, the
> SYSMOD is also rejected from the PTS

Measured on TK5 (JOB 47 to 48, and JOB 68 to 69), both UCLIN jobs RC 0:

```
UCLIN PTS .
DEL SYS REJECT .
ENDUCL .
```

`LIST PTS .` before, after `DEL SYS REJECT`, and after `ADD SYS REJECT`:

```
SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=YES
SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=NO
SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=YES
```

The manual gives `DEL SYS PURGE` and `ADD SYS PURGE` the same way. **`PURGE` was not measured**, so
`REJECT` after an ACCEPT under `PURGE=NO` (the open point of `MVS-SMP-0013`) is still open.

## The two cases on TK5

Fresh system, ZP60014 and ZP60038 `REC APP` and not accepted, ZMG0003 installed, then
`RESTORE SELECT(ZMG0003,ZP60014,ZP60038) .`, then `APPLY SELECT(ZP60014,ZP60038) DIS(WRITE) .`

| | `REJECT=YES` (as distributed) | `REJECT=NO` |
|---|---|---|
| RESTORE | RC 4, all three out (JOB 50) | RC 4, all three out (JOB 53) |
| `LIST PTS SYSMOD(...)` after it | not taken | all three there, `STATUS = REC` |
| re-APPLY | RC 12, HMA4012 (JOB 53) | RC 0 (JOB 56) |
| IKJPTGT, AMBLIST text lines | 1502, stays so | 1533, line-identical to before the install |
| Install ZMG0003 again | RC 12, HMA3022 `ZP60038 PRE` | RC 0, same module as the first install |

The two columns come from two containers; the only change between them is the UCLIN.

```
HMA4012 ** SYSMOD ZP60014 SELECTED FOR APPLY NOT FOUND ON SMPPTS LIBRARY
HMA4012 ** SYSMOD ZP60038 SELECTED FOR APPLY NOT FOUND ON SMPPTS LIBRARY
```

So on a system with `REJECT=YES`, RESTORE of an applied usermod removes it for good unless its job
stream is still at hand. **The indicator must be off before the RESTORE.** The way back after a
RESTORE under `REJECT=YES` (RECEIVE from the original job stream) was not measured.

Full cycle under `REJECT=NO`, with both forms of the usermod (below): install 1576 lines, RESTORE 1502,
re-APPLY 1533 and equal to the baseline, IPL with TSO logon, second install equal to the first, second
RESTORE and re-APPLY equal to the baseline again.

`EXEC` in `SYS1.CMDLIB` also carries a ZP60014 module. In a separate run without ZMG0003, RESTORE plus
re-APPLY of ZP60014 and ZP60038 left it line-identical (769 lines; 742 while restored; JOB 43 to 48).

RESTORE RC 4: the job shows `HMA2391 LINK SUCCESSFUL ... LMOD=IKJPTGT ... RETURN CODE=04`. That this is
the cause of the RC 4 is my reading, not established.

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
