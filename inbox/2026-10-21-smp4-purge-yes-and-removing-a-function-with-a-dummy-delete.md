# 2026-10-21 — SMP4: PURGE=YES is why REJECT fails after ACCEPT; a dummy FUNCTION with ++VER(Z038) DELETE removes an accepted product's modules

Source: Paperclip issue MVS-225 (community feedback on the UFSD handbook chapter
"Removing UFSD"), measured 2026-10-21 in two throwaway containers (MVS/CE and TK5),
SMP4 `HMASMP LVL 04.48` in both. UFSD 1.5.0 (FMID TUFS150, `DELETE(TUFS140)`) was
installed through SMP from the release artifacts (RECEIVE, APPLY CHECK, APPLY, ACCEPT
in one job). The containers were removed afterwards; nothing was run on a real system.
Job numbers are not carried over. Board approval to write this note: Paperclip comment
on MVS-225 (2026-10-21).

This note refines `2026-10-21-smp4-restore-reject-after-accept.md`: that note reads the
REJECT failure as "ACCEPT removes the MCS from SMPPTS" (inferred). The measurement
below names the setting responsible.

## 1. PURGE=YES in the SMPPTS SYSTEM entry causes the REJECT failure

`LIST PTS .` shows the SYSTEM entry of the PTS (`LIST SYSTEM .` and `LIST PTS SYSTEM .`
are rejected with HMA2033). On both distributions:

```
SYSTEM    OPTIONS         = PAGELEN=0061  PEMAX=9999  PURGE=YES  REJECT=YES
```

After ACCEPT of TUFS150, on both distributions:

```
REJECT SYSMOD(TUFS150):
HMA2462 ** SYSMOD TUFS150 NOT FOUND ON SMPPTS LIBRARY
HMA2260    REJECT PROCESSING TERMINATED FOR SYSMOD TUFS150
HMA2050    REJECT PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12

RESTORE SYSMOD(TUFS150):
HMA2452 ** SYSMOD TUFS150 SELECTED FOR RESTORE HAS BEEN ACCEPTED
HMA3703 ** RESTORE PROCESSING TERMINATED BECAUSE FUNCTION SYSMOD TUFS150 FAILED
HMA2050    RESTORE PROCESSING COMPLETED - HIGHEST RETURN CODE IS 12
```

Reading: `PURGE=YES` makes ACCEPT remove the accepted SYSMOD from the PTS, so REJECT
cannot find it. RESTORE is refused on its own because the SYSMOD is accepted. The
connection between PURGE=YES and HMA2462 is the documented meaning of the option plus
this output; it was **not** shown that PURGE=NO lets REJECT succeed after ACCEPT.

Not established: how to change the option. Attempts to alter the SYSTEM entry with `UCLIN PTS .`
followed by `REP SYSTEM` / `REP SYS` / `REP OPTIONS` plus `OPTIONS(PURGE=NO)` or
`PURGE(NO)` all ended `HMA2032 ** SYNTAX ERROR IN UCL STATEMENT` (RC 08) on the
REP statement, in seven variants.
The right syntax is unknown, so the PURGE=NO case is unmeasured. Therefore "UCLIN is the
only way" is too strong as a statement about SMP in general, but no other documented
route was demonstrated either.

## 2. A dummy FUNCTION that deletes the product FMID

Input (received from an inline `SMPPTFIN`; the element-less function is allowed):

```
++FUNCTION(TZZ0001) .
++VER(Z038) DELETE(TUFS150) .
```

RECEIVE, APPLY CHECK, APPLY, ACCEPT with `//HMASMP.LINKLIB DD DISP=SHR,DSN=UFSD.LINKLIB`
and `//HMASMP.AUFSDLOD DD DISP=SHR,DSN=UFSD.AUFSDLOD` (the libraries of the deleted
product must be allocated, or SMP cannot delete from them).

Return codes (identical on MVS/CE and TK5): RECEIVE 04, APPLY CHECK 00, APPLY 04,
ACCEPT 00.

```
HMA3971    SYSMOD TZZ0001 HAS NO ELEMENTS               (RECEIVE, RC 04)
HMA2240    SUCCESSFULLY DELETED LMOD UFSD ON LINKLIB LIBRARY      (also UFSDCLNP, UFSDSSIR, UFSFMT)
HMA2461    SYSMOD TUFS150 NOT FOUND ON SMPSCDS LIBRARY  (APPLY, RC 04)
HMA2240    SUCCESSFULLY DELETED MODULE UFSD ON AUFSDLOD LIBRARY   (ACCEPT; also the other three)
```

Because RECEIVE ends RC 04, a following step with `COND=(0,NE,...)` is bypassed; use
`COND=(4,LT,...)`.

Member lists (TSO `LISTDS ... MEMBERS`), before and after the dummy:

```
before: UFSD.LINKLIB    UFSD UFSDCLNP UFSDSSIR UFSFMT      UFSD.AUFSDLOD  UFSD UFSDCLNP UFSDSSIR UFSFMT
after:  UFSD.LINKLIB    (no members)                        UFSD.AUFSDLOD  (no members)
```

Inventory after the dummy, in both CDS and ACDS: `MODULE UFSD` and `LMOD UFSD` no
longer found; the new function is a normal entry and the deleted one is a tombstone:

```
TZZ0001   TYPE = FUNCTION  STATUS = REC APP ACC  FMID = TZZ0001  DELETE VER(001) = TUFS150
TUFS150   TYPE = FUNCTION  DELBY = TZZ0001
TUFS140   TYPE = FUNCTION  DELBY = TUFS150        (left by the earlier upgrade)
```

So the dummy path does the part SMP does well (library members, MOD and LMOD entries),
but it does **not** free the FMID: the product id and the dummy id stay in the inventory
as FUNCTION entries and a `LIST` answers RC 00 for them. They need a final `UCLIN`
`DEL SYSMOD(...)` in both zones (RC 00 in the measurement), after which every LIST
answers not found (RC 04) and the libraries can be scratched. A product reinstalled
afterwards (the shipped install job) ended RC 00 in every step on both distributions.

A universal variant, one dummy deleting every id the product has ever used
(`++VER(Z038) DELETE(TUFS110,TUFS120,TUFS130,TUFS140,TUFS150)`), also works (TK5: RECEIVE
04, APPLY CHECK 00, APPLY 04, ACCEPT 00). SMP tombstones every listed id, including ones
that never existed on the system, which makes the later `DEL SYSMOD` lines succeed.

## 3. UCLIN DEL SYSMOD of an id that does not exist is an error, not a no-op

The documented UCLIN removal job of UFSD (a list of every id ever spent, in one block per
zone) was run on the MVS/CE container, where only TUFS140 and TUFS150 had ever existed:

```
HMA2532 ** SYSMOD ENTRY TUFS130 TO BE DELETED DOES NOT EXIST     (also TUFS120, TUFS110)
HMA2560    UPDATE PROCESSING TERMINATED - UPDATE NOT COMPLETE
HMA2293 ** CONTROL STATEMENT IGNORED DUE TO PREVIOUS ERROR       (next UCLIN block)
UCLIN step RC 12
```

The first (CDS) block is rejected as a whole at RC 08, the following block is skipped
(RC 12), and the ACDS was left unchanged (TUFS150 still `STATUS = REC APP ACC`), while the
final `LIST` step answered RC 04 and so looked like a normal result. A `RESETRC .` between
the blocks stops the cascade, but the block that names a missing id is still rejected.
Naming only ids that exist ends RC 00. Consequence for every product: a removal UCLIN
must only name ids that exist (or follow a DELETE function that tombstoned them), and
the stanzas of the final LIST must be read, not the return code.

## Limits

- Throwaway containers, not production systems: no history of old FMIDs or tombstones
  beyond what is stated; both have the SMP4 default SYSTEM entry shown above.
- One product (UFSD, four load modules, LMOD names equal to module names). The `++MAC`
  variant of the dummy (the dummy macro in the RAKF example) was not run.
- PURGE=NO was not set; REJECT after ACCEPT with PURGE=NO is unmeasured.
- Order of the steps and the UCLIN syntax are exactly as shown above; the dummy id used
  was a throwaway id and must not be a released FMID.
