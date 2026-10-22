---
id: MVS-LNK-0002
title: IEA703I 106-0F is a sporadic fetch I/O error on unchanged libraries, and under Hercules 4.9.1 a fetch can return a wrong module image without any error
status: tested
platform: [mvs38j]
sources:
  - "mvslovers/httpd#300 (description and all comments, 2026-10-15 to 2026-10-19): the numbers and job numbers below"
  - "mvslovers/httpd internals/fetchprobe/ldlp.asm and README.md (probe LDLP; PR mvslovers/httpd#301)"
  - "mvslovers/mvs-docker README, section 'Inside the image' (BREXX 106-0C)"
  - "Job numbers (JOBnnnnn) are system-local: each of the TK5 systems, the MVS/CE systems and each throwaway container has its own counter"
verified_on: 2026-10-19
verified_platforms: ["TK5 Update 5 systems on Hercules 4.9.1.0-SDL (the TK5 bundle) and on 4.10.0.11774-SDL-DEV-g59d8981c", "MVS/CE 3.0.0 system on 4.10.0.11774-SDL-DEV-g59d8981c", "TK5 and MVS/CE containers (mvs-docker), Hercules 4.10.0.11783-SDL-DEV-ga7423980"]
applies_to: [httpd, mvsmf, brexx370]
tags: [iea703i, abend106, program-fetch, iewfetch, hercules, channel-program, pci, probe, wrong-image, tk5, mvsce]
related: [MVS-LNK-0001, MVS-LNK-0003, MVS-LNK-0004, MVS-LNK-0005]
---

## The claims

1. **`106-0F` is a fetch I/O or channel-program failure, not a storage
   shortage.** Storage is reason `0C`. `[tested]` (below) The text IBM gives
   for 106 reason `0F` is quoted in httpd#300 as *"Either an uncorrectable
   I/O error occurred, or an error in the load module caused the channel
   program to fail."* (z/OS MVS System Codes; quoted in httpd#300, not checked
   against the manual, and a z/OS manual, not a 3.8j one.)
2. **It happens sporadically on libraries that have not changed.** The next
   fetch of the same module succeeds. Measured on TK5 and on MVS/CE, through
   the link list and through a private `STEPLIB`, rates from 1 per 750,000 to
   about 28 per 750,000 depending on system and library. `[tested]`
3. **It follows the library, not the volume, the access path or the control
   unit.** `[tested]`
4. **Separate fault, same probe:** under the Hercules 4.9.1 that TK5 bundles,
   a fetch occasionally *succeeds* and returns a wrong module image, with no
   message and no abend. `[tested]` Not seen under Hercules 4.10.0.
5. **The cause is not found.** Everything in "Reading" below is a hypothesis.

## How it was measured: probe LDLP

`LDLP` (httpd `internals/fetchprobe/ldlp.asm`, assembled and link-edited in
the job) takes `PARM='NAME,COUNT'` and does `LOAD EPLOC=NAME,ERRET=...`
followed by `DELETE` COUNT times, so every LOAD is a fresh program fetch.
`[source: httpd internals/fetchprobe/ldlp.asm, README.md, origin/main]`

- A failed fetch takes the ERRET exit: counted as **FAIL**, with the R1/R15
  the exit received.
- A successful fetch is checksummed over the module's whole main-storage
  block (CDE extent list). A different sum at the same address as the first
  load is **BAD**: wrong contents, no error. For BAD loads a word-by-word
  diff against the first image follows.
- A load at another address is **MOVED**. After a FAIL this is the storage of
  the failed fetch, which MVS never gives back (see MVS-LNK-0003).

The module was IEMRA, a PL/I (F) compiler phase on TK5: 4 KB, no RLD, so its
image is the same at any address. Its first good sums were identical on TK5
and MVS/CE (`B5E18F30/A221D14A`). Every FAIL below is `IEA703I 106- F ...
MODULE ACCESSED IEMRA`, exit registers `R1=00000106 R15=0000000F`, followed by
a load one page higher.

## Rates (FAIL, Hercules 4.10.0 unless stated)

All runs below alternate sources within one job; rates from different jobs
are not directly comparable, the systems share one host.

| where | source | rate | job (system-local) |
|---|---|---|---|
| a TK5 system | `SYS2.LINKLIB` through the link list | 13 and 9 per 750,000 | JOB00908, JOB00914 |
| same | the same library as `STEPLIB DD` | 16 per 750,000 | JOB00908 |
| same | full IEBCOPY copy of the library on another volume (544 members) | 8, 13 and 21 per 750,000 | JOB00914, JOB00916 |
| same | copies with 1 to 4 members | 1 per 2,500,000 (JOB00911 + JOB00912); 1 per 2,000,000 (JOB00907) | |
| an MVS/CE system | the same full library (XMIT, same record layout) | 1 per 750,000 | JOB01788 |
| a TK5 container (mvs-docker), Hercules `ga7423980`, x86-64 host | the same full library | 1 per 1,000,000 | JOB00038, container-local |
| the same container image on an Apple M2 Pro (arm64) | the same full library | 0 per 1,000,000 | container-local |
| an MVS/CE container, same Apple host | the same full library | 0 per 1,000,000 | container-local |

Outside the probe, `IEA703I 106- F` was counted in the console logs of the
five systems (2026-10-15): on one TK5 system 7 times (PL/I
phases IEMRA x3, IEMQK, IEMML, IEMED, and MVSMF in HTTPD), on a second TK5
system twice (MVSMF in HTTPD), on three MVS/CE systems never. An `IEB139I I/O
ERROR DURING READ ... PROGRAM CHECK` in an IEBCOPY step occurred twice on the
first TK5 system, once under Hercules 4.9.1 and once (JOB01989, 2026-10-16)
under 4.10.0; the identical rerun was clean each time.

```
MBTDEPL JOB01989, step MERGE (IEBCOPY)
IEB139I I/O ERROR DURING READ - MBTDEPL ,MERGE ,190,DA,STAGE ,00- OP,PROGRAM CHECK ,0000034400010A,EXCP
IEB100I I/O ERROR READING MEMBER TT111PPR
```

## What the measurements separate

- **Not the access path.** Link list and private `STEPLIB` on the same data
  set fail alike: 13 against 16 per 750,000 (JOB00908).
- **Not the volume.** The full copy on a different volume fails like the
  original: 8 against 9 (JOB00914).
- **Not the control unit.** With the failing library, `cu=3880` and
  `cu=3990` fail alike: 21 against 13 (JOB00916). (JOB00907 had compared the
  two with a library that hardly ever fails: 0 against 1 per 1,000,000, no
  conclusion.)
- **Not one Hercules build.** Seen under 4.9.1 (TK5 bundle), under 4.10.0
  `59d8981c` (the systems) and under 4.10.0 `a7423980` (containers).
- **Not TK5 alone.** An MVS/CE system fails on the same library, about ten
  times less often than the TK5 system (1 against 8 to 21 per 750,000; the
  chance of 1 or 0 events at the lowest TK5 rate, 8, is about 0.3 %).
- **The library matters.** Full copies (544 members, 210 directory blocks,
  IEMRA's text from R53 on a full track, last text record at R2 of the next
  track) fail at the original's rate; copies of 1 to 4 members hardly fail.
  Whether the record layout or the large directory counts is open.
- **The rate depends on the system.** On the TK5 system it was about ten times
  that of the MVS/CE system and of the containers, at similar host load. Host
  load moves the rate between jobs (a run beside a second probe job on the
  same host ran at about twice the rate), so it is a factor in how often, not
  in which library.

Rates that moved when the TK5 system changed from Hercules 4.9.1 to 4.10.0
(too few events to prove a change): link list, from 10 to 4 per 400,000;
`STEPLIB` copy, from 1 per 200,000 to 1 per 2,000,000. Hercules is therefore
at most one factor, "not sufficient on its own".

## The second fault: a wrong image without any error (Hercules 4.9.1)

Under the Hercules `4.9.1.0-SDL` that TK5 bundles (GCC 13.3, `-O3
-march=alderlake`; the TK5 systems ran it until moved to 4.10.0), the probe
counted BAD loads on a TK5 system: 31 in 400,000 (JOB00898 and JOB00899,
IEMRA from the link list; 10 FAIL in the same loads), and 9 in 200,000 on a
copy with all records on one track (JOB00904).

- Always one of three fixed wrong images, never random bits. All three have
  the plain word sum `DDD21740` (the good image `B5E18F30`); only the
  position-weighted sum differs:

| sums | bytes at offset 0 | equal to | words differing |
|---|---|---|---|
| `DDD21740/0B18B1B4` | `920082A3 95FFAF86` | IEMRA TEXT2 | 0x200, offsets 0-0x7FC |
| `DDD21740/F2887BB4` | `47F0A0C6 920082A5` | IEMRA TEXT3 | 0x200, offsets 0-0xBFC |
| `DDD21740/D30CFAB4` | `58908270 18294130` | IEMRA TEXT4 | 0x1F8, offsets 0-0xFFC |

  So the content of a later text record stands at the address of the first
  one. All 29 BAD whose sums were reported (the probe reports the first ten
  per step) carry one of these three pairs. `[tested]`
- BAD does not need the track break: the single-track copy gave the same three
  variants (JOB00904).
- The same TK5 system on Hercules 4.10.0 `59d8981c`: **0 BAD in 400,000**
  (JOB00905; 4 FAIL). Every later run on 4.10.0 gave BAD 0.
- **Not separated:** 4.9.1 alone, or 4.9.1 together with TK5's IEWFETCH
  level. MVS/CE never ran on 4.9.1.
- A Hercules source diff `Release_4.9.1` against `59d8981c` showed no change
  in the lines that test `CCW_FLAGS_PCI` (they moved by about 29 lines); the
  418-line `channel.c` diff was not read in full. The build (compiler and
  flags) differs as well and is as likely a candidate. `[inferred]`

Consequence: a TK5 system on the bundled 4.9.1 can execute wrong code with
nothing reported. Two candidates seen on one such system on 2026-10-15
(interpretation, not proof): an S0C4 at MVSMF start, with the next "DSA" in
the chain at `001C0A60` inside MVSMF's own text (`R13` pointing at module
text), after about 30,000 clean runs of the same path; and
`IEM3856I COMPILER ERROR, PROGRAM CHECK TYPE 1 IN PHASE 'OB'` from the PL/I
(F) compiler on source that had compiled cleanly before.

## Where TK5 and MVS/CE differ in the fetch path

SMP `LIST` on both systems (CDS and ACDS identical on each) `[tested]`:

| module | TK5 RMID | MVS/CE RMID |
|---|---|---|
| IEWFETCH (LPALIB) | UZ41374 | UZ54723 |
| IEAVLK00 / 01 | UZ48820 | UZ53937 / UZ51713 |
| IECVEXCP / IECVEXPR | UY09531 | UZ73316 / UZ61195 |

Per the PTF tapes (quoted in httpd#300), UZ41374 is the last of the IEWFETCH
chain (June 1985) and supersedes UZ54723 and every fetch PTF in between.
Three of those PTFs describe the fault class (APAR texts quoted in httpd#300
from the PTF tapes, not re-checked):
OZ80463 *"ABEND106-F CAN OCCUR ... THE RESULT OF AN INCORRECT FIX FOR
OZ67752 AND OZ61811"*; OZ80498 *"THE FETCH PCI FLAG IN THE IOSB FILEMASK
DOES NOT GET SET ON. THIS MAY RESULT IN INCORRECT CCW CHAINS"*; OZ81870 *"PCI
ROUTINE FAILS ON REDRIVE ... IEWFETCH PROCESSES DATA FROM THE CTL (CTL/RLD)
RECORD BEFORE THE ENTIRE RECORD HAS BEEN READ"*.

Hercules configuration differences read on the two systems: TK5 `NUMCPU 1`,
`CPUMODEL 3033`, `TIMERINT 10000`, every 3390 `cu=3990`; MVS/CE `NUMCPU 2`,
`CPUMODEL 0148`, default `TIMERINT`. The TK5 container (`NUMCPU 1`,
`TIMERINT 10000`, `CPUMODEL 3033`, UZ41374 applied, same library layout)
fails at the MVS/CE rate, so those settings and the PTF are not sufficient by
themselves. What still differs between the TK5 system and the TK5 container:
the Hercules commit and build, bare process against container, and the MVS
workload around the probe. `[tested]` for what was read; the rest open.

## Reading (hypothesis, not proven)

IEWFETCH patches its running channel program from the PCI appendage
(NOP to TIC). If the patch comes late, the channel runs on and reads the next
record: without any error under 4.9.1 (wrong record, BAD), more rarely and
with a program check under 4.10.0 (106-0F). That would be one interaction with
two detections. `[inferred]` From the inbox note and httpd#300; the IEWFETCH
listing was not re-read at ingest. The sync-read paths being commented out in
the 3.8 source is likewise from httpd#300. Whether the cause lies in IEWFETCH
or in Hercules' emulation of a channel program that changes while it runs
cannot be separated without real hardware.

Retracted in httpd#300 while measuring, so do not repeat them:
"TK5 only" (MVS/CE fails too); "the silently wrong images belong to Hercules
4.9.1, not to MVS" (only TK5-on-4.9.1 against TK5-on-4.10.0 was measured);
"the emulator is cleared for the 106-0F" (the rate fell on both paths on
4.10.0); "one PCI window explains the wrong-record images and the 106-0F in
that form".

## Relation to MVS-LNK-0001

`106-F` in MVS-LNK-0001 is persistent: every fetch of the affected modules
fails until the IPL, after a new extent or a compress. Here the same
`IEA703I 106- F` (reason `0F`) is intermittent: the next fetch of the same
module succeeds, the library is unchanged. Same code, different causes.
MVS-LNK-0001's reading "the module is fetched from a place the link list does
not know" holds for its two causes and does not cover this one; see the
qualification added there.

## Consequences

- Read `106-0F` as a channel/I/O fault, not as storage shortage (that is
  `106-0C`). The mvs-docker README states the real storage case: BREXX from
  `SYS2.LINKLIB` without `REGION` fails `IEA703I 106-0C`, `REGION=4M` works
  (not re-measured here).
- Decide between MVS-LNK-0001 and this one by repetition: the same module
  fetches fine on the next call, and no link-list library was changed, so it is
  this sporadic fault.
- Every fetch can be hit; every hit costs the module's storage (MVS-LNK-0003).
  A server that fetches per request accumulates this; a server that holds its
  modules fetches once per module (MVS-LNK-0005).
- Under 4.9.1, wrong code can run silently. BAD was not seen under 4.10.0
  (0 in 400,000 on the same system, and 0 in every later 4.10.0 run); that is
  a measurement, not a proof that 4.10.0 is safe.
- The ERRET exit gives the code (LOAD) or only the completion code (LINK):
  MVS-LNK-0004.
