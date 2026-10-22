# RAKF profile loader (CJYRPROF) sorts unsorted input; U0300 only for duplicates (measured, old RAKF and 2.0.0)

Date: 2026-10-21. Source: Paperclip MVS-340 (follow-up to MVS-332/MVS-326). Own throwaway MVS/CE container, not a stand.

## Finding

`S RAKFPROF` with an UNSORTED SYS1.SECURE.CNTL(PROFILES) loads normally on both the container's original RAKF and RAKF 2.0.0 (TRKF200 applied and accepted, CLPA IPL):

    RAKFPROF7  RAKF PROFILES UPDATED

The loader reads all non-comment records into a table and sorts them itself (source: CJYRPROF.hlasm, RRKF007, bubble sort over the 80-byte record). `RAKFPROF3  I/P RECORDS OUT OF ORDER` + `ABEND S000 U0300` happens only for DUPLICATES of class+entity+id (same key twice), never for merely unsorted order. The earlier wording "loader sorts, U0300 only for duplicates" was source-derived and ambiguous about which RAKF was measured; it is now measured explicitly for both builds.

Docs may therefore say: profile order in the file does not matter; a duplicate class/entity/user line aborts the reload with U0300.

## Test input (unsorted, JESSPOOL before DASDVOL/FACILITY, entity blocks reversed, two user lines swapped)

racf_auth results (AC(1) probe, libc370 2.25.1, R=READ U=UPDATE A=ALTER, 0 permitted / 4 no profile / 8 denied), identical on old RAKF and 2.0.0:

    MVSCE02 JESSPOOL ZQSORT.X   R0 U8 A8
    MVSCE02 JESSPOOL ZQALPHA.X  R0 U0 A8
    MVSCE01 JESSPOOL ZQALPHA.X  R0 U8 A8
    MVSCE01 JESSPOOL ZQSORT.X   R8 U8 A8
    MVSCE02 JESSPOOL OTHER.X    R8
    MVSCE02 FACILITY FTPAUTH    R8 (unchanged)
    MVSCE02 DATASET SYS1.SECURE.CNTL  R8 (unchanged)
    MVSCE02 NOSUCHCL X.Y        old RAKF R4, RAKF 2.0.0 R8 (this tells the builds apart)

So racf_auth is level-correct after the loader's own sort.

## Duplicate case

Same input plus a duplicate `JESSPOOL ZQSORT.* MVSCE02 READ` line (and a variant that also raises an access level in a non-duplicate line):

    RAKFPROF3  I/P RECORDS OUT OF ORDER
    RAKFPROF3  **  PROGRAM TERMINATED  **
    IEF450I RAKFPROF RAKFPROF - ABEND S000 U0300

Old chain stays: the probe after the failed reload still shows the previous levels (the raised access was not applied). Measured on the old RAKF and on 2.0.0.

## Caveat

At IPL a failing CJYRPROF is fatal for JES2 on 2.0.0 (see the MVS-332 A14 measurement); a duplicate in the file at IPL is therefore worse than at `S RAKFPROF`.
