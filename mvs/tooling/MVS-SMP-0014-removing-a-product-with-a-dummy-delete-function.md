---
id: MVS-SMP-0014
title: An element-less FUNCTION with ++VER(Z038) DELETE(product) removes an accepted product's modules and inventory entries — but not its ids, which stay as tombstones until a UCLIN
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers, SMP 4 HMASMP LVL 04.48 in both, 2026-10-21 (as reported in the inbox note; job numbers not carried over) — UFSD 1.5.0 (FMID TUFS150, DELETE(TUFS140)) installed through SMP from the release artifacts in one job; dummy function TZZ0001 received from an inline SMPPTFIN; universal variant on the TK5 container"
  - "QA acceptance run of FTPD 1.3.0 (TFTP130), TK5 throwaway container, 2026-10-22 (Paperclip MVS-20, ftpd#283 to #287): dummy function TFTPDEL with DELETE(TFTP100,TFTP110,TFTP120,TFTP130), UCLIN, scratch (as reported in the inbox note; job numbers belong to that container)"
  - "ufsd docs/uninstall.md at commit 6804ee7 — the removal procedure built on a dummy function (TUFSDEL), the main route there"
verified_on: 2026-10-21
verified_platforms: ["MVS/CE (3.0.0)", "TK5 Update 5"]
applies_to: [ufsd, ftpd, httpd, mbt]
tags: [smp, smp4, delete, ver, dummy-function, uninstall, tombstone, hma3971, hma2240, hma2461, uclin, mbt]
related: [ECO-0007, MVS-SMP-0006, MVS-SMP-0008, MVS-SMP-0009, MVS-SMP-0010, MVS-SMP-0013, MVS-SMP-0015]
---

## The claims

1. **A function that carries no elements and only `++VER(Z038) DELETE(<product>)`
   removes the product's load modules from both libraries and its `MOD` and `LMOD`
   entries from both zones.** `[tested]`
2. **It does not free the ids.** The product id and the dummy id stay as
   `FUNCTION` entries, and `LIST` answers RC 00 for them (`MVS-SMP-0009`). A final
   `UCLIN` `DEL SYSMOD(...)` in both zones is still needed. `[tested]`
3. **The libraries of the deleted product have to be allocated in the job.** A
   missing DD fails silently for the APPLY (`MVS-SMP-0010`). `[tested]`

## The dummy function

Received from an inline `SMPPTFIN`:

```
++FUNCTION(TZZ0001) .
++VER(Z038) DELETE(TUFS150) .
```

RECEIVE, APPLY CHECK, APPLY and ACCEPT, with the product's libraries allocated
in the job:

```
//HMASMP.LINKLIB  DD DISP=SHR,DSN=UFSD.LINKLIB
//HMASMP.AUFSDLOD DD DISP=SHR,DSN=UFSD.AUFSDLOD
```

Return codes, identical on MVS/CE and TK5: RECEIVE 04, APPLY CHECK 00, APPLY 04,
ACCEPT 00.

```
HMA3971    SYSMOD TZZ0001 HAS NO ELEMENTS               (RECEIVE, RC 04)
HMA2240    SUCCESSFULLY DELETED LMOD UFSD ON LINKLIB LIBRARY      (also UFSDCLNP, UFSDSSIR, UFSFMT)
HMA2461    SYSMOD TUFS150 NOT FOUND ON SMPSCDS LIBRARY  (APPLY, RC 04)
HMA2240    SUCCESSFULLY DELETED MODULE UFSD ON AUFSDLOD LIBRARY   (ACCEPT; also the other three)
```

RECEIVE ends RC 04, so a following step gated on `COND=(0,NE,…)` is bypassed. Use
`COND=(4,LT,…)`, as the generated install jobs do for the ACCEPT
(`MVS-SMP-0008`).

## Evidence: member lists and inventory

TSO `LISTDS … MEMBERS` before and after the dummy:

```
before: UFSD.LINKLIB    UFSD UFSDCLNP UFSDSSIR UFSFMT      UFSD.AUFSDLOD  UFSD UFSDCLNP UFSDSSIR UFSFMT
after:  UFSD.LINKLIB    (no members)                        UFSD.AUFSDLOD  (no members)
```

After the dummy, in both CDS and ACDS, `MODULE UFSD` and `LMOD UFSD` are no longer
found. The new function is a normal entry and the deleted ones are tombstones:

```
TZZ0001   TYPE = FUNCTION  STATUS = REC APP ACC  FMID = TZZ0001  DELETE VER(001) = TUFS150
TUFS150   TYPE = FUNCTION  DELBY = TZZ0001
TUFS140   TYPE = FUNCTION  DELBY = TUFS150        (left by the earlier upgrade)
```

So the dummy path does the part SMP does well: library members, `MOD` and `LMOD`
entries. The ids need a final `UCLIN` with `DEL SYSMOD(...)` for every id in both
zones (RC 00 in the measurement). After it every `LIST` answers not found (RC 04)
and the libraries can be scratched. A product reinstalled afterwards, with the
shipped install job, ended RC 00 in every step on both distributions.

## Universal variant

One dummy deleting every id the product has ever used:

```
++VER(Z038) DELETE(TUFS110,TUFS120,TUFS130,TUFS140,TUFS150)
```

also works (TK5: RECEIVE 04, APPLY CHECK 00, APPLY 04, ACCEPT 00). SMP tombstones
every listed id, including ones that never existed on the system, which makes
the later `DEL SYSMOD` lines succeed instead of ending `HMA2532` / RC 08
(`MVS-SMP-0009`).

## A second product: FTPD 1.3.0 (TFTP130), TK5

The same route removed FTPD completely on a TK5 container that had TFTP130 installed through SMP
(QA acceptance run of FTPD 1.3.0, 2026-10-22; job numbers belong to that container). Four jobs, each step
checked: `[tested]`

1. `FTPDDEL`, CC 0004: a dummy function `TFTPDEL` without elements, `++FUNCTION(TFTPDEL) ...
   DELETE(TFTP100,TFTP110,TFTP120,TFTP130)`, then RECEIVE, APPLY and ACCEPT (the universal variant above).
   ```
   HMA3971    SYSMOD TFTPDEL HAS NO ELEMENTS
   HMA3930    SYSMOD TFTPDEL SUCCESSFULLY RECEIVED
   HMA2270    APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTPDEL
   HMA2461    SYSMOD TFTP130 NOT FOUND ON SMPSCDS LIBRARY
   HMA2270    ACCEPT PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTPDEL
   ```
   APPLY RC 0004, ACCEPT 0000. `HMA2461` is again only the missing backup entry.
2. `FTPDUCL`, CC 0004: UCLIN on CDS and ACDS (both `RC=0000`) removes the `TFTPDEL` entry itself
   (`HMA2550 UPDATE COMPLETE FOR TFTPDEL`). Before it, `TFTPDEL` stood in both zones as `REC APP ACC` with a
   `DELBY = TFTPDEL` mark on the deleted ids. The final `LIST` step ends RC 0004 because the entries it asks
   for are gone (`THE FOLLOWING SELECTED ENTRIES WERE NOT FOUND OR WERE NOT ELIGIBLE FOR PROCESSING`), which
   is the wanted answer.
3. `FTPDSCR`, CC 0000: IDCAMS scratch of `FTPD.LINKLIB` and `FTPD.AFTPDLOD` (`IDC0550I ENTRY (A) ... DELETED`).
4. `LIST CDS/ACDS MOD(FTPD) LMOD(FTPD)` answers `NOT FOUND` for both.

A clean first install of the same candidate afterwards (allocation job, install job) ended every step
`RC=0000`, so the ids and the libraries were free again. A fourth UCLIN block run after the main path, a
fallback that cuts the FMID out directly, ended CC 0008 because the entries were already gone; that is
expected and no defect of the product or of the guide.

## Limits

- Throwaway containers; two products: UFSD with four load modules whose LMOD names
  equal their module names, and FTPD (TK5 only, number of modules not recorded).
- The dummy id must be a throwaway id and must never be a released FMID.
- A dummy built from a `++MAC` element instead of an empty function (the dummy
  macro in the RAKF example) was not run.
- UFSD's guide makes this route its main removal procedure (a dummy function
  `TUFSDEL` deleting every release) and keeps UCLIN alone as the fallback.
  `[source: ufsd docs/uninstall.md, 6804ee7]` The measurements above were not
  repeated at ingest.
