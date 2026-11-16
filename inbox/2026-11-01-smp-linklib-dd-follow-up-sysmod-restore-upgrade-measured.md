# SMP records the DD name of an element, not the data set: what a later SYSMOD, RESTORE or upgrade does when a product is installed through DD LINKLIB (MVS/CE and TK5 Update 5)

Source: measurement MVS-1415 (and the control runs for an own DD name), 2026-11-01.
Platform: MVS/CE and TK5 Update 5, own throwaway containers, SMP `HMASMP LVL 04.48` on both.
Images: `ghcr.io/mvslovers/mvsce:latest` and `ghcr.io/mvslovers/tk5:latest`. The digests below were read
from the local images after the run, not recorded during it: mvsce
`sha256:7ce810ce0fba609af00c14293d0532348a0bca3945d1a5b24adbdab2da7779e8`, tk5
`sha256:2e4210c4c2d21c9dfd31199139d7142cc3d2c6bf593d5258dd612325c29c14c6`.
Container result, not a stand result. Throwaway FMIDs `TZQV/TZQW/TZQX/TZQY` 100 and 110, USERMODs
`ZZQ0001`/`ZZQ0002`, one module per product (a copy, no re-link).
Maintainer approved this inbox entry (2026-11-01).

## Setting

A throwaway product is installed with its load library given as DD `LINKLIB` (override in the install
job, COPY-style JCLIN, `++MOD LKLIB/DISTLIB`), as mbt generates it for products whose library ends in
`.LINKLIB`. SMP records the element under DD `LINKLIB`.

Plain procedures: `SMPREC` and `SMPAPP` on both systems; `SMPACC` on TK5 only (MVS/CE has no `SMPACC`, job
37 ends S013-18). In `SMPAPP` (both systems) and `SMPACC` (TK5) the DD `LINKLIB` is `SYS1.LINKLIB`.
Cards that override a procedure DD must come before any added card, otherwise the procedure's DD wins
silently. `SYS1.LINKLIB` had 915 members on MVS/CE and 916 on TK5 at the start.

## Results (job numbers: MVS/CE / TK5)

1. **Install through DD LINKLIB** (RECV, APPLY CHECK, APPLY, ACCEPT) 45 / 52, all RC 0. HMA2380
   `LIBRARY=LINKLIB` and `LIBRARY=AZQXLOD`. The product library gets the module, `SYS1.LINKLIB` is unchanged.
   CDS LMOD: `SYSTEM LIBRARY = LINKLIB`.
2. **Follow-up SYSMOD, plain `SMPAPP`, no LINKLIB card** (RECEIVE, APPLY CHECK, APPLY) 49 / 56: RC 0,
   HMA2380 `LIBRARY=LINKLIB`, the module is written into **`SYS1.LINKLIB`** as a new member (915 to 916 on
   MVS/CE, 916 to 917 on TK5; contents checked by IEBGENER in jobs 51 / 58: the service level). The product
   library is untouched and keeps the old module. CDS: the SYSMOD is `REC APP`, the MOD's RMID is the SYSMOD
   (job 50 / 57). Nothing in the return codes shows the wrong target.
3. **RESTORE of that SYSMOD, plain procedure.** Without a card for the DLIB DD (`AZQXLOD`): 52 / 59, RC 12,
   `HMA2832 AZQXLOD DDCARD MISSING FOR ELEMENT`, nothing written. With the DLIB card: 53 / 60 (through `SMPACC`),
   RC 0, writes the previous level into **`SYS1.LINKLIB`**, replacing the member (member count unchanged); the
   product library is untouched; CDS back to the original FMID (MVS/CE job 54). An orphan copy of the old level stays
   in `SYS1.LINKLIB`. RESTORE takes the SYSMOD from the PTS; a second APPLY needs a new RECEIVE (TK5 job 63:
   `HMA4012 NOT FOUND ON SMPPTS`), a second RESTORE gives `HMA2452 HAS NOT BEEN APPLIED` (TK5 job 65).
   Repeated through `SMPAPP` on TK5 (jobs 68 and 72): the same.
4. **Control, product with an own DD name** (library `ZQY.ZQYLINK`, DD `ZQYLINK`), plain procedure, no
   card: APPLY CHECK and APPLY RC 12, `HMA2832 ZQYLINK DDCARD MISSING FOR LOAD MODULE` (58 / 77); RESTORE
   without card RC 12, same message (62 / 81). Nothing written, `SYS1.LINKLIB` never holds the module. With the
   card, APPLY (61 / 80) and RESTORE (65 / 84) end RC 0. A DD name outside the procedures fails loud and safe.
5. **Upgrade, predecessor under LINKLIB, successor (next FMID with DELETE of the predecessor) under an own
   DD name** (second container pair; predecessor installed in jobs 40-42 / 49-51; orphan module in
   `SYS1.LINKLIB` from case 2 for product X, jobs 44 / 53):
   - **V, no card for the old DD** (47 / 56, snapshot 48 / 57): APPLY RC 4, `HMA2240 SUCCESSFULLY DELETED LMOD ...
     ON LINKLIB LIBRARY`, no HMA2832, because `LINKLIB` exists in the procedure and resolves to `SYS1.LINKLIB`.
     `SYS1.LINKLIB` unchanged, the **product library keeps the old module**, the new library has the new one. The
     RC 4 comes from `HMA2461 SYSMOD T...100 NOT FOUND ON SMPSCDS LIBRARY`, which appeared in all three cases and
     is not explained.
   - **W, old library on a `//HMASMP.LINKLIB` card** (49 / 58, snapshot 50 / 59): the module is deleted from the
     product library, which stays behind empty; the new library has the new module.
   - **X, no card, and a module of the same name in `SYS1.LINKLIB`** (51 / 60, snapshot 52 / 61, content job
     53 / 62): `HMA4451`/`HMA4460` warn that the USERMOD in that MOD will be overlaid, `HMA2240 DELETED LMOD ...
     ON LINKLIB`; **the member in `SYS1.LINKLIB` is gone** (916 to 915 on MVS/CE, 917 to 916 on TK5; reading it
     gives S013-18), the product library keeps its old module.
6. MVS/CE and TK5 behave the same in every measured point; only member counts and TTRs differ.

## Consequences

- A DD name that is also a DD of the SMP procedures (`LINKLIB`, `SAMPLIB`, `MACLIB`, `PROCLIB`, `CMDLIB`, ...)
  turns every later SYSMOD or RESTORE run without the product's own card into a silent write to the SYS1
  library, with RC 0.
- A DD name outside the procedures turns the same mistake into HMA2832 and RC 12.
- Renaming the DD of a released product needs an upgrade job that carries the old DD, pointing at the old
  library, for the DELETE. Without it the old library keeps the old modules and, if a same-named module is in
  the SYS1 library, that one is deleted.

## Not measured

PTFs (only USERMODs); a real re-link (JCLIN with the linkage editor); several modules or aliases; APPLY of
the follow-up through `SMPACC` on TK5; a DD rename where the data set name stays the same (does the DELETE
of the old element delete the module the same job just wrote?). The last one is measured in MVS-1423; add the
result here.

## Earlier statements this settles

`smp.md` (workspace) said that a later SYSMOD or RESTORE with the plain procedure resolves a product's
`LINKLIB` to `SYS1.LINKLIB` "inferred, not yet measured". Measured now, cases 2 and 3.
