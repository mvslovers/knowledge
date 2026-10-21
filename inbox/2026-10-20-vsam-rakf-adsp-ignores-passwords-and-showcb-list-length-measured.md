# VSAM on MVS/CE: under RAKF, DEFINE makes catalogs RACF-indicated and VSAM then skips cluster passwords; SHOWCB MF=G needs 8n+20 bytes

Source: libc370 session, 2026-10-20. Issue mvslovers/libc370#623, PR #698
(merged, released in libc370 2.25.0: `__vsopenx()` with a password field,
`__vsinfo()`). Probe `test/mvs/tstvsox.c` with `jcl/tstvsox.jcl` and
`jcl/recvvsox.jcl`. Measured in two own throwaway MVS/CE containers
(`mvsce-target up`, local, image `ghcr.io/mvslovers/mvsce:latest` as of
2026-10-20, job log "370/148 VS2 R03.8 MVSC"; image digest and Hercules
version not recorded): A = libc370-623a (exploration), B = libc370-623b
(final runs), C = libc370-623pw (password check). Job numbers are container-local and restart in each container,
so they are always given with the container.

Related: `2026-10-20-vsam-showcb-fdbk-returns-only-reason-code-measured.md`
(SHOWCB FIELDS=FDBK).

## Finding 1: with RAKF, DEFINE makes catalogs and entries RACF-indicated; in a RACF-indicated catalog VSAM does not check cluster passwords

### Measured: everything a normal job DEFINEs is RACF-indicated

- Container A, job DEF623 (JOB00020): a new user catalog LIBC623.UCAT with
  MASTERPW(CATPW). LISTCAT ALL shows RACF (YES) on every cluster, on the
  AIX and path entries, and on the UCAT's cluster entry itself. Only the
  UCAT's own data and index components show RACF (NO).
- Container B: the LISTCAT in the LOAD step of `jcl/tstvsox.jcl`
  (JOB00019/00020/00022) shows the same for the VSOX623.* entries (recorded
  less closely than A).

### Measured: in that RACF-indicated catalog, passwords were not checked

- A KSDS in LIBC623.UCAT, defined with READPW(RDPW) UPDATEPW(UPPW)
  MASTERPW(MSPW) ATTEMPTS(0), opened with rc 0 in every case:
  - `vsopen()` of libc370 2.24.1, no password: container A JOB00022 and
    container B JOB00022, step RED.
  - `__vsopenx()` with no password, with "XXXX" and with "RDPW": container A
    JOB00022 step GREEN (no IEC161I, no WTOR); container B JOB00022 step
    GREEN, case (d) of `tstvsox.c`.

### Measured: in a catalog that is NOT RACF-indicated, passwords are checked, also for a RACF-indicated cluster

Container C = libc370-623pw (own, local, same image). Helper NOADSP (AC=1,
scratch, not in the repo) clears JSCBADSP (JSCB+X'10E', bit X'40') and
LINKs IDCAMS. Catalog VSPW623.UCAT on WORK00, MASTERPW(CATPW); all clusters
KEYS(8 0) READPW(RDPW) UPDATEPW(UPPW) MASTERPW(MSPW) ATTEMPTS(0). Probe:
scratch `tstvspw.c` against libc370 2.25.0; it calls `__vsopenx()` and, for
the diagnosis only, repeats the open through the library's internal open to
read ACBERFLG.

- JOB00019 (TSTVSPW): NOADSP WTOs `JSCBFBYT X'40' AUTH 1`,
  `JSCBFBYT now X'00'`, `LINK IDCAMS rc 0`. Step DEFN (through NOADSP)
  defined the UCAT and VSPW623.PWN; step DEFR (plain IDCAMS, same job)
  defined VSPW623.PWR. LISTCAT: UCAT, PWN and PWR all RACF (NO). So the
  cleared JSCBADSP held for the later steps of the same job: per job, not
  per step (or at least not reset at step start).
- PWN, no password: `__vsopenx()` rc 153 (EVSOPEN), ACBERFLG X'98',
  IEC161I 040(056,006,IGG0CLBM)-002.
- PWN, wrong password "XXXX": rc 153, ACBERFLG X'98',
  IEC161I 040(056,002,IGG0CLBM)-002.
- PWN, right password "RDPW": rc 0, ACBERFLG X'00', ACBOFLGS X'12', record
  read.
- JOB00020 (TSTVSPW2), a new job without NOADSP: step DEFC (plain IDCAMS)
  defined VSPW623.PWC into the same (RACF (NO)) catalog. LISTCAT: PWC
  RACF (YES) on cluster, data and index, so JSCBADSP is on again in a new
  job. PWC, no password: rc 153, ACBERFLG X'98',
  IEC161I 040(056,006,IGG0CLBM)-002. Refused.
- No WTOR, no IEC301A (ATTEMPTS(0)). Probe 3/3, CC 0000.

So the deciding fact is the catalog's RACF indication, not the cluster's.

### Source (read, not measured)

- RAKF `SRCLIB/ICHSFR00.hlasm` line 508 (RACINIT):
  `OI ACEEFLG1,ACEERACF+ACEECNTL`. In IBM's IHAACEE (copy read:
  `brexx370-books/sysmac/IHAACEE.mac`) ACEECNTL is X'40', a bit of
  ACEEFLG2 (CONTROL authority); in ACEEFLG1, X'40' is ACEEADSP. So RAKF's
  RACINIT turns on automatic data set protection for every user. Not
  checked: whether RAKF's own macro copy defines these bits the same way
  (i.e. whether the ADSP effect is intended).
- IGG0CLAL lines 2566/2572 (catalog DEFINE):
  `IF JSCBADSP=ON|CTGFVRON=ON` (TM JSCBADSP,X'40') leads to RACF definition
  of the new entry.
- IGG0CLB6 (IGGPCKCC, the security check around statements 0263-0292 and
  869-957): VSAM first checks whether the catalog or entity is RACF-defined;
  for a RACF-defined catalog, RACF definition is implied for its entries.
  Password information is extracted only "IF THE CATALOG IS NOT
  RAC-DEFINED". This fits the measurement.

### Inferred, not measured

- That the initiator sets JSCBADSP from ACEEADSP (not found in source).
- Why the RACF-indicated catalog lets every open through: RAKF's RACHECK
  answer for the cluster was not traced.

### What it means

- On a system with RAKF (MVS/CE, TK5), a user catalog a normal job DEFINEs
  is RACF-indicated, and VSAM passwords of the clusters in it are not
  checked; access control is RAKF's.
- Clusters in a catalog that is not RACF-indicated (one DEFINEd without
  JSCBADSP) are password-checked even when they are RACF-indicated
  themselves: a missing or wrong password fails OPEN with ACBERFLG X'98'
  and IEC161I 040.

## Finding 2: SHOWCB with MF=G needs 8n+20 bytes for n fields

### Measured

- Container A JOB00026, exploration program VSEX2 (scratch, not in the
  repo): `SHOWCB ACB=...,FIELDS=(KEYLEN,RKP,LRECL,CINV,BUFND,BUFNI,BUFSP),
  LENGTH=28` with a 128-byte list area: R15 0, values 8 0 80 4096 0 0 0.
  Afterwards the list area held:
  - 8 address words: the first points to the 16-byte header, the next seven
    to one word each, the last with the high bit set (800AA338);
  - the header A0030000 000A9B28 000AA370 001C0000;
  - 7 field-code words 00100000 001F0000 00110000 00080000 00040000
    00050000 00070000.

  That is 32 + 16 + 28 = 76 bytes = 8*7+20.
- With a 64-byte list (16 words, as the other libc370 VSAM functions use)
  the same 7-field SHOWCB returned R15 4 on every call (container A JOB00022,
  step GREEN of an early build). The same fields one at a time with 64 bytes
  returned R15 0 (container A JOB00024, VSEX); two and four fields also
  returned 0 (JOB00026).
- With an 80-byte list (`pl[20]`, `src/mvs/vsam/@@vsinfo.c` in libc370
  2.25.0) the probe passed 40/40 (container B JOB00022).

### Inferred, not measured

- The general formula (n+1 address words, a 16-byte header, n field-code
  words) is read off one dump with n=7 and fits the 64-byte failure; the
  generation in IDACB2 was not read.
- How the overflow produces R15 4 (presumably the generated list overruns
  and corrupts the parameter list itself): only the R15 4 is measured.

### What it means

- Size an MF=G list area for SHOWCB at 8n+20 bytes for n fields, not 4n
  plus a little. (TESTCB/MODCB were not measured.)
