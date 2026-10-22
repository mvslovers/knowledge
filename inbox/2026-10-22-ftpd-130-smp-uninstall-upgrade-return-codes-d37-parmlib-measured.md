# 2026-10-22 — FTPD 1.3.0 (TFTP130) through SMP: uninstall with a dummy DELETE, upgrade return codes on TK5 vs MVS/CE, D37-04 in SYS1.PARMLIB

Source: QA acceptance run of FTPD 1.3.0 (FMID TFTP130, deletes TFTP120), release candidate
`6b6367d` (build id `6B6367D`, LIBC370 2.25.1 `FCDE4E8`), installed through SMP from the
candidate's artefacts following `docs/installation.md` (Paperclip MVS-20, ftpd#283 to #287).
Measured in fresh, throwaway containers (`mvsce-target up --host mvsdev`): TK5 (image with
FTPD 1.2.0 / TFTP120 SMP-installed) and MVS/CE (image with an FTPD 1.2.0 that SMP never saw).
Container results, not stand results. The containers are gone. Job numbers restart in every
container, so each number below belongs to its run only. The upgrade in section 1 and the
MVS/CE install are from the run on candidate `6b6367d` (rc3 files, identical in content to rc2);
the uninstall in section 2 and the D37-04 jobs in section 3 are from the run on the same commit
built earlier (rc2), whose upgrade job produced the same result.

Platform: mvs38j (TK5, MVS/CE).

## 1. Upgrade 1.2.0 to 1.3.0: the APPLY return code differs between TK5 and MVS/CE

The install job (RECEIVE, APPLYCHK, APPLY, ACCEPT) ends differently depending on whether SMP
knows the level that TFTP130 deletes.

TK5, TFTP120 in the SMP inventory (job `FTPDINS`, JOB00043, run of 2026-10-22 20:04):

```
FTPDINS    APPLYCHK  HMASMP    HMASMP    RC= 0000
FTPDINS    APPLY     HMASMP    HMASMP    RC= 0004
FTPDINS    ACCEPT    HMASMP    HMASMP    RC= 0000
HMA2380    COPY SUCCESSFUL - MOD=FTPD - LMOD=FTPD - LIBRARY=LINKLIB - SYSMOD=TFTP130 - RETURN CODE=00
HMA2270    APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTP130
HMA2461    SYSMOD TFTP120 NOT FOUND ON SMPSCDS LIBRARY
HMA2270    ACCEPT PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTP130
```

Job CC 0004. `HMA2461` comes after `HMA2270`: SMP reports that the deleted level has no backup
entry in SMPSCDS to keep. The install is complete; `LIST CDS/ACDS` shows FMID = RMID = `TFTP130`
for MOD and LMOD `FTPD`.

MVS/CE, first install (allocation job, then the same install job; JOB00035): all steps
`CC 0000`, no `HMA2461`, `HMA2270` for APPLY and ACCEPT. Reason: SMP never saw the image's
FTPD 1.2.0 (it runs from `MVSLOVER.FTPD.LOADLIB`, not from an SMP install), so there is nothing
named TFTP120 to delete or to complain about.

Without the allocation job on MVS/CE the job ends `JCL ERROR`
(`IEF212I FTPDINS HMASMP APPLYCHK LINKLIB - DATA SET NOT FOUND`, JOB00034 of the earlier run).
If the allocation job is run after the install has already received the SYSMOD, the install job
ends CC 0008 with `HMA3862 ** SYSMOD TFTP130 ALREADY RECEIVED` and APPLYCHK does not run
(JOB00036); APPLY and ACCEPT end 0000.

Rule that follows: the return code of an upgrade is not a pass/fail signal. Verify by
`HMA2380 COPY SUCCESSFUL` for MOD=FTPD, the `LIST` stanza and the banner of the started task
(`F FTPD,VERSION`: `FTPD016I FTPD 1.3.0 (6B6367D)`).

## 2. Removing FTPD completely: a dummy FUNCTION with `DELETE(...)` works on TFTP130

State before: TK5 with TFTP130 installed by the upgrade of section 1. Job sequence (JOB00049 to
JOB00052), each step checked:

1. `FTPDDEL` (JOB00049, CC 0004): a dummy function without elements, `TFTPDEL`, with
   `++FUNCTION(TFTPDEL) ... DELETE(TFTP100,TFTP110,TFTP120,TFTP130)`, then RECEIVE, APPLY and
   ACCEPT. Decisive lines:
   ```
   HMA3971    SYSMOD TFTPDEL HAS NO ELEMENTS
   HMA3930    SYSMOD TFTPDEL SUCCESSFULLY RECEIVED
   HMA2270    APPLY PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTPDEL
   HMA2461    SYSMOD TFTP130 NOT FOUND ON SMPSCDS LIBRARY
   HMA2270    ACCEPT PROCESSING SUCCESSFULLY COMPLETED FOR SYSMOD TFTPDEL
   ```
   `HMA2461` here is again only the missing backup entry. APPLY ends RC 0004, ACCEPT 0000.
2. `FTPDUCL` (JOB00050, CC 0004): UCLIN on CDS and ACDS (both `RC=0000`) to remove the
   `TFTPDEL` entry itself (`HMA2550 UPDATE COMPLETE FOR TFTPDEL`). The dummy function leaves
   `TFTPDEL` in both zones with status `REC APP ACC` and a `DELBY = TFTPDEL` mark on the deleted
   ids; the ids are not free again until it is cut out. The final `LIST` step ends RC 0004
   because the entries it asks for are gone (`THE FOLLOWING SELECTED ENTRIES WERE NOT FOUND OR
   WERE NOT ELIGIBLE FOR PROCESSING`), which is the wanted answer.
3. `FTPDSCR` (JOB00051, CC 0000): IDCAMS scratch of the two libraries:
   `IDC0550I ENTRY (A) FTPD.LINKLIB DELETED`, `IDC0550I ENTRY (A) FTPD.AFTPDLOD DELETED`.
4. Check: `LIST CDS/ACDS MOD(FTPD) LMOD(FTPD)` answers `NOT FOUND` for both.

Afterwards a clean first install of the same candidate (allocation job, install job) ended
all steps `RC=0000` (`FTPDINS`, JOB00055, CC 0000), which shows the ids and the libraries were
free again.

A fourth UCLIN block run after the main path (a fallback that cuts the FMID out directly) ends
CC 0008 (JOB00052) because the entries are already gone. That is expected and not a defect of
the product or of the guide.

## 3. TK5: `SYS1.PARMLIB` is full; copying the first new member abends D37-04

On a fresh TK5 the copy of `FTPDPRM0` into `SYS1.PARMLIB` (IEBGENER, member to member) ends:

```
IEC031I D37-04,IFG0554T,PARMCPY,COPY,SYSUT2,390,TK5RES,SYS1.PARMLIB
IEF450I PARMCPY COPY - ABEND SD37 U0000
```

(PARMCPY, JOB00045). D37-04 means the directory of that PDS has no room for another member,
so it is the first new member that fails; nothing is wrong with the data. Two ways out, both
measured on the same container:

- Compress `SYS1.PARMLIB` (IEBCOPY with `COPY` of the library onto itself, JOB00046:
  `IEB161I COMPRESS TO BE DONE USING INDD NAMED PARMLIB`, CC 0000), then the copy again
  (JOB00047, CC 0000).
- Use a PARMLIB of your own: allocate `HERC01.PARMLIB` and copy `FTPDPRM0` into it (PRIVPL,
  JOB00048, CC 0000), start with `/S FTPD,D='HERC01.PARMLIB'`; `F FTPD,CONFIG` then lists the
  values from that member.

MVS/CE has `SYS2.PARMLIB` with room; the default `D='SYS2.PARMLIB'` of the shipped procedure
works there without a change. The shipped procedure on MVS/CE has to replace the image's
member `FTPD` in `SYS2.PROCLIB`, otherwise the started task keeps running
`MVSLOVER.FTPD.LOADLIB` (1.2.0).

## 4. A trap for whoever repeats this on TK5

The TK5 image carries stale `HERC01.FTPD.LOAD.XMIT` and `HERC01.FTPD.SAMP.XMIT` of FTPD 1.2.0.
If the upload of the new XMIT files fails (or goes to different data set names) and the install
job still points at those names, RECEIVE succeeds and SMP reports TFTP130, but the installed
module is the old one: the SMP output showed `Receiving 'FTPD.V1R2M0.LINKLIB'` and the started
task printed `FTPD 1.2.0`. Return codes were clean. Delete the old data sets before the STOR
(`DELE` on the product FTPD, port 2121 of the container) and read the banner afterwards.

(In the same containers the port 2121 is the product FTPD itself, so PASV data ports of an FTP
client outside the host are unpublished: run the upload from the host that runs the
containers, against the container's address.)

## Status

Measured on candidate `6b6367d` (rc2 and rc3 builds of the same commit; the upgrade return code
was seen on both). Not measured: the same sequence on a real stand with years of SMP
history (old FMIDs, tombstones).
