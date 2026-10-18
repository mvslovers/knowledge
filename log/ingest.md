# Ingest log

One line per ingest run (`CLAUDE.md` §8). This is what makes the KB checkable
rather than merely believable.

| date | source | created | changed | conflicts |
|---|---|---|---|---|
| 2026-10-18 | oftpd session — Hercules (hyperion) `control.c`, the `E501 test_protection` handler, read while writing the oftpd#15 probe | none | `MVS-PROT-0001` (**TPROT is privileged** — `PRIV_CHECK`; the key comes from `effective_addr2 & 0xF0`, not from the PSW; the CC order now has a source; the consequence that an unauthorized caller can never check its own access) | none |
| 2026-10-18 | oftpd session — an ecosystem-wide as370 return-code census: clean clones of 13 projects' HEADs built with a logging shim as `MBT_AS` and first on `PATH`, plus a column-72 positive control (as370 1.6.3 802dde1, mbt 3.0.0-dev 436396f) | none | `ECO-0009` (what an rc-4 deck loses, measured: 4 bytes of text against 2; the 818/0 census; the `.s`-vs-`.asm` scope line; the CRLF miscount; `verified_on` → 2026-10-18; filed as mvslovers/mbt#286, the gating decision stays **open**) | none |
| 2026-10-18 | oftpd session — inbox `2026-10-17-oftpsvc-review-vier-beobachtungen.md` (review of `oftpd/asm/oftpsvc.asm`): as370 1.6.3 host runs, IBM `IHAACEE.asm` read by the libc370 session, mbt `internal/build/build.go` | `MVS-PROT-0001`, `ECO-0009` | `ECO-0008` (`ACEEUSER` is length-prefixed; libc370 2.18.0 carries the subfields), `ECO-0004` (`related:` link only -- its `IEAVSY50` item is **held back pending a measurement**, see below) | none |
| 2026-10-18 | oftpd session — the SVC 237 install/restore run on m38x (MVSCE-EXP): `GET /cgi-bin/tasks/syslog` at `mvsdev.lan:8383`, `mbt target console m38x`, oftpd `internals/xmem.md` section 10 | none | `MVS-HERC-0001` (the HTML `tasks/syslog` route; `msgcount` counts messages and the reader's own `D` commands fill the window — answers part of its open "Not measured" bullet; `D A,<jobname>` invalid; the m38x port pair; `verified_on` → 2026-10-18, `applies_to` + `oftpd`) | none |
| 2026-09-26 | rexx370 session — BREXX/370 coexistence on MVSCE-LAB (JOB01315/01316, fix PR #244, JOB01319/01324/01333, foreground run); brexx370 source 794b701 (rxinit.hlasm, rxterm.hlasm, #ENVCTX) | `MVS-TSO-0003` | `MVS-TSO-0001`, `MVS-TSO-0002` (`related:` → `MVS-TSO-0003`) | none |
| 2026-09-25 | rexx370 session — ZMG0002 reinstall on MVSCE-LAB: RESTORE CHECK/RESTORE JOB01301/01302, AMBLIST JOB01303/01304, REJECT JOB01305/01306, LIST JOB01307, RECEIVE/APPLY/verify JOB01310–01313 | `MVS-SMP-0005` | `ECO-0007`, `MVS-SMP-0004` (`related:` → `MVS-SMP-0005`) | none |
| 2026-09-25 | rexx370 session — USERMOD ZMG0002 on MVSCE-LAB: RECEIVE JOB01259, APPLY CHECK JOB01260, APPLY JOB01261 (LKDPRINT), verify JOB01262 | none | `MVS-SMP-0004` (open question on ++JCLIN-added modules answered, `[tested]`) | none |
| 2026-09-25 | rexx370 session — MVSCE-LAB TSO repair: APPLY UY43678/UZ42826 JOB01231 (LKDPRINT), AMBLIST JOB01232, ACCEPT UY43678/UZ42826/UY16532 JOB01234, AMBLIST AOST4 JOB01235; CDS LMOD entries JOB01219/JOB01226 | `MVS-SMP-0004` | `ECO-0007`, `MVS-SMP-0001`, `MVS-SMP-0002`, `MVS-SMP-0003` (`related:` → `MVS-SMP-0004`) | none |
| 2026-09-25 | MVS/CE LAB JOB01201 (KBBLDL: six BLDL forms, IFOX00 listing); SYS1.LINKLIB / SYS1.LPALIB member lists; `IGC018` `CLRENT` / `LIB` | none | `MVS-BLDL-0001` (→ `tested`; root cause narrowed to `(1)`; DCB=0 search order corrected; LPA not searched; R/Z byte reading; control probe rewritten), `CF-2026-002` + `CF-2026-003` (closed, outcome B); `tools/kb-lint.py` (CF warning only for open conflicts) | `CF-2026-002`, `CF-2026-003` closed |
| 2026-09-25 | KB consistency pass — `tools/kb-index.py`, `tools/kb-lint.py`, `IHBINNRA` / `BLDL` macro source, `IGC018` (SVC 18) | `CF-2026-002`, `CF-2026-003`; `tools/kb-lint.py` | `MVS-BLDL-0001` (→ `disputed`; `applies_to` free-text entry dropped), `ECO-0001` (→ `disputed`; `related:` reciprocates `ECO-0008`), `ECO-0007` (`related:` reciprocates `ECO-0008`); `CLAUDE.md` §3 layout gains `mvs/jcl/` | `CF-2026-002`, `CF-2026-003` |
| 2026-09-24 | rexx370 session — WP-33-TSO on MVSCE-LAB (JOB01181, JOB01185, JOB01189, JOB01192, s3270 foreground run); IKT0009C, IKJEFT01 sources | `MVS-TSO-0001`, `MVS-TSO-0002`, `PM-2026-004` | none | none |
| 2026-09-23 | *(backfilled 2026-09-25 from front matter)* rexx370 session — IKJEFTRX BLDL on MVSCE-LAB (JOB01125/01127/01129/01131); IKJEBECI, IKJEBESA sources | `MVS-BLDL-0001` | `PM-2026-001` (`related:` → `MVS-BLDL-0001`) | none |
| 2026-09-23 | MVSHIST session — SMP 4 experiments on MVSCE-LAB (jobs JOB01077–JOB01095) and TK3/TK5 zone measurements | `MVS-SMP-0001`, `MVS-SMP-0002`, `MVS-SMP-0003` | `ECO-0007` (open question on requisite zones answered; RC-04 note qualified; `related:` extended) | none |
| 2026-08-04 | *(backfilled 2026-09-25 from front matter and file dates)* httpd, libc370, ufsd, nsf370, cc370, rexx370 repositories | `ECO-0006`, `MVS-ENC-0001`, `MVS-SSI-0001`, `PM-2026-001`, `PM-2026-002`, `UFSD-ADR-0001`; `tools/kb-index.py` | `ECO-0002`, `ECO-0003`, `ECO-0004` (`related:` links) | none |

## 2026-10-18 — TPROT is privileged, which is a design fact and not a test detail

Found while writing the oftpd#15 probe, by reading the emulator rather than
reasoning: Hercules' `E501` handler calls `PRIV_CHECK(regs)` right after the
operand decode, so a problem-state program issuing `TPROT` gets S0C2.

`MVS-PROT-0001` recommended `TPROT` as the store check without saying who may
issue one. Three things follow, now in the entry:

- The key being tested comes from bits 24-27 of the **second operand's
  address**, not from the PSW key, and nothing is fetched from that address.
  So an authorized routine can ask about key 8 without being in key 8 — which
  is what makes the check usable at all.
- **An unauthorized caller can never check its own access.** Every such check
  has to be made by the service on the caller's behalf. A design that expected
  a client to validate its own pointers before calling has no instrument for
  it. oftpd's `TPRNG` already works this way, so this confirms rather than
  changes it.
- A measurement of the question needs an **APF-authorized job**. The probe
  I had first described to the MBT session as needing no authority at all
  would have abended and measured nothing; corrected before it was scheduled.

The condition-code order in the entry also has a source now (the same handler)
rather than being second-hand along with the rest. The document stays
`inferred`: a reading of the emulator our systems run on is better than an
inference and still not a run on MVS, and it says so.

## 2026-10-18 — what an as370 rc 4 actually costs, measured across the ecosystem

`ECO-0009` already recorded that mbt lets rc 4 pass and that `IFO026` lives in
that band. What it could not say was what an rc-4 deck loses, or what closing
the gap would cost. Both are now measured, and the entry carries them.

**The loss is an instruction, and the deck looks fine.** Two files of the same
four statements, differing only in a trailing comment reaching column 72:
`clean.o` has 4 bytes of text, `warn.o` has 2. The `BR 14` is simply absent.
That reproduces the shape of the httprexx `BALR`/`S0C1` case without waiting
for it to recur, which is what moves the entry from a worked example to a
property.

**Closing the gap would cost nothing today**: 818 as370 invocations across 13
projects, none with a non-zero return code. The number is only worth something
because of two controls. A column-72 file through the same shim logged rc 4 —
without it, "zero" would be the exit-0-and-plausible answer the root
`CLAUDE.md` warns about. And interception was checked arithmetically: libc370's
build prints `737 .s + 29 .asm` and the shim logged exactly 766 calls, so
nothing bypassed it by an absolute path.

**One correction to my own first pass, and it is the useful part.** The static
column-72 scan first reported 474 suspicious lines. 320 of them were a `\r`
from CRLF files sitting at byte 72 of a 71-character line, and most of the rest
were brexx370's card sequence numbers in columns 73-80 behind a real
continuation marker. Byte position is not column position until the line
endings have been looked at, and the `awk 'length($0) >= 72'` defence the entry
recommends cannot tell the three apart. That is now in the document, because
the defence is the thing a reader will actually run.

**Correction, same day, before anything acted on it.** The paragraph above
originally ended "the gating decision stays open and belongs to the
maintainer". It does not: the MBT session pointed at **mvslovers/mbt#278**
(2026-10-17), where the maintainer's position is recorded — rc 4 is a warning,
as on MVS, and he is against failing the build on it. I read that issue myself
before accepting the correction; it carries the same IFO026/BALR/S0C1 case and
the same pipe trap as `ECO-0009`, so the two were written the same day in
ignorance of each other.

So `ECO-0009` had recorded a question as open when the answer existed, and I
had reported it to the maintainer that way — which invited him to decide
something he had already decided, without either of us seeing it was a
reversal. The entry now names #278 in its sources, says the question was
answered on 2026-10-17, and states that the census is **evidence against a
decided question, not grounds to treat it as unmade**. mbt#286 stays open as
that evidence and is cross-linked; no session touches `build.go`.

The general shape is the one the root `CLAUDE.md` names: the measurement was
sound and checked twice, and the sentence beside it — "this is open" — was
carried over from a document rather than from a source. It was caught by the
session that owns the repo, which is the division that keeps working.

## 2026-10-18 — the SVC review's four observations, and one near-conflict

The inbox item was split four ways. Three were ingested; the fourth is held
back and stays in the inbox under a name of its own.

Created: **`MVS-PROT-0001`** — `MVCK`'s key operand is a fetch check, so moving
caller data under the caller's key does not keep a forged pointer out of key-0
storage; `TPROT` is the store check. Filed `inferred`, not `manual`: the
Principles of Operation is not held locally and is not in `sources/`, so the
condition-code table is second-hand and says so. Only the as370 encoding is
`tested`. oftpd#15 is the experiment that would make it `tested`, and it is
scheduled for its own reasons.

Created: **`ECO-0009`** — as370 exits with its severity, mbt gates at rc >= 8,
and the gap is rc 4, where `IFO026` (column-72 continuation) lives. Whether
rc 4 should fail a build is an open maintainer decision and is recorded as
such, not decided here.

**Not changed: `ECO-0004`, deliberately, and this is the interesting part of
the run.** Its sentence "Only R13 is preserved across the call" is `source`
from `@@xmpost.c` — the *caller* — while IBM's `IEAVSY50` exit notes say
"REGS 9,14 ARE SAVED". The three `IEAVSY50` readings were written into the
document during this ingest and then **taken back out the same day** at the
libc370 session's request: what it had was IBM's comment block and a code
reading, not a measurement, and it is building an authorized probe that loads
markers into R0-R15, issues the branch-entry XMPOST and reports which
registers come back. Until that runs, `ECO-0004` keeps its wording and the
item waits in `inbox/2026-10-17-eco0004-ieavsy50-pending-measurement.md`.

The only trace left in the document is the reciprocal `related:` link to
`MVS-PROT-0001`, which asserts nothing. Worth recording as the rule it
illustrates: a `source` claim from the callee does outrank one from the
caller (§9), but "outranks" decides a conflict — it does not license
upgrading a code reading into the document before anyone has run it (§0.4).

Changed: **`ECO-0008`** — a section on `ACEEUSER` being length-prefixed in
IBM's own `IHAACEE`, with the flat eight-byte `MVC` as the failure it invites,
and the caveat that three *consumers* were read and no producer, so the blank
padding is inferred.

Division of labour, recorded because it is the §9 defence working as intended:
the libc370 session read `IEAVSY50` and `IHAACEE` and produced the line
numbers; this session wrote the prose and does the ingest; libc370 cross-reads
what was written — and on `ECO-0004` it stopped the ingest, which is the half
of cross-reading that usually does not happen. Neither party both measured and
published the sentence beside the measurement.

One number in `MVS-PROT-0001` was caught the same way before it shipped: the
inbox note's "two probes cover a range up to 2048 because it spans at most two
**4 K** blocks" carries an XA-era granularity. S/370 keys cover **2 K**, which
makes the stated reason wrong while leaving the 2048 bound safe. The document
now states the bound, both candidate granularities, and that the one that
matters is unmeasured.

The original inbox file is deleted and replaced by the `ECO-0004` remainder.
`inbox/2026-09-25-ihbinnra-bpam-reader.md` remains and is untouched.

## 2026-09-25 — BLDL conflicts settled on MVS/CE LAB

One batch job, JOB01201 (`KBBLDL`), assembled a probe with IFOX00, linked it
into `&&LOAD` and ran six steps, one BLDL form each. Evidence is the WTO
output (return code plus 12 raw bytes of each entry), quoted in both CF
documents together with the macro expansions from the listing.

- **`CF-2026-002` closed, B:** only `BLDL 0,(1)` fails. `(0)`, `(2)` and the
  symbolic form produce identical entries.
- **`CF-2026-003` closed, B:** DCB=0 found a module that existed only in
  `//STEPLIB` (Z=`02`); an explicit `CVTLINK` DCB did not.
- **New, not asked for:** `IKJEFT01` is in `SYS1.LPALIB` on MVS/CE, and BLDL
  does not search the LPA. So the control probe as written in
  `MVS-BLDL-0001` (IEFBR14 + IKJEFT01, checked by R15) returns RC=4 even for
  a correct list. Rewritten to check `IEFBR14`'s R byte.
- **A trap in my own probe:** the step condition codes claimed "both
  entries found" for lists where the second was not. SVC 18 zeroes the R
  byte of every entry before it searches (`IGC018` `CLRENT`), which defeated
  the "TTR still `FFFFFF`" test. The raw bytes caught it. The fact is
  recorded in `MVS-BLDL-0001`.

Convention used for a closed conflict: the CF document takes the status of
its evidence (`tested`), gets a *Resolution* section, and keeps its links.
`kb-lint.py` now warns only about documents linked to an *open* CF.

Outside the KB, not edited: `rexx370/src_ptf/TODO_IKJEFT01.md` (Offen,
item 3) and the comment on `IKJEFTRX.ASM:82` still give "link library only"
as the reason.

## 2026-09-25 — consistency pass

Ran `tools/kb-index.py` and an ad-hoc lint over the working tree (§11's
`kb-lint.py` does not exist yet).

- HEAD's `INDEX.md` listed six documents that had never been committed
  (`ECO-0006`, `MVS-ENC-0001`, `MVS-SSI-0001`, `PM-2026-001`, `PM-2026-002`,
  `UFSD-ADR-0001`), and said it was generated by `tools/kb-index.py`, which
  was not committed either. Both are committed now.
- `ECO-0008` → `ECO-0001` / `ECO-0007` was not reciprocated; fixed.
- `MVS-BLDL-0001` carried `any module doing a BLDL` in `applies_to`, which
  the index turned into a project. Dropped.
- **`CF-2026-002`**: `MVS-BLDL-0001` generalises a measurement of `BLDL 0,(1)`
  to all register notation. The `IHBINNRA` expansion shows why `(1)` in
  particular fails (`LA 1,0` then `LR 0,1`) and suggests other registers
  work. The document is `disputed` until one job settles it.

Second round, same day:

- **`CF-2026-003`**: `MVS-BLDL-0001` says BLDL with DCB=0 searches only the
  link library. That claim has no source and was never measured, and SVC 18
  says the opposite: `IGC018` at `NOLNKSVC` searches the current TCB's
  JOBLIB/STEPLIB (`TCBJLB`) and only then `CVTLINK`. The same claim is in
  `rexx370/src_ptf/TODO_IKJEFT01.md` (Offen, item 3), which is not in the KB.
- `ECO-0001` goes from `assumed` to `disputed`, because `CF-2026-001` rests on
  it (§9). The TK4- gap is still marked, now inline as `[assumed]`.
- `tools/kb-lint.py` implements §11. It was checked against a copy with five
  planted faults and caught all of them (exit 1). On this tree it reports
  0 errors.

The 2026-09-23 BLDL and 2026-08-04 rows above were backfilled in this pass.
Both are reconstructed from the documents' front matter and file dates, not
from the sessions that wrote them.

## 2026-09-24 — TPUT in the background TMP, PUTLINE without a CPPL

Source: rexx370 WP-33-TSO (#228, PR #229) on `MVSCE-LAB`: measurements of TPUT
and PUTLINE output in a batch `IKJEFT01` step and in an s3270 foreground
session, read against `IKT0009C` (SVC 93) and the original `IKJEFT01`.

Created:

- **`MVS-TSO-0001`** — TPUT does nothing in the background TMP. SVC 93 returns
  without work, and without setting R15, when ASCBTSB is zero.
- **`MVS-TSO-0002`** — calling PUTLINE without a CPPL: the UPT via LWA+24 →
  PSCB+52, the ECT via LWA+32, the PTPB bytes and the CVTPUTL call.
- **`PM-2026-004`** — the postmortem, including the wrong turns: a green test
  that checked RCs, a stale LINKLIB, libc370's SYSPRINT, the reconstructed
  source, a 3270 session collision.

No existing document touched the topic, so no conflicts. `mvs/tso-rexx/` is
new.

## 2026-09-23 — SMP 4 requisite zones, receive state, RMID semantics

Source: live SMP 4 runs on `MVSCE-LAB` (MVS/CE 3.0.0, SMP 4 level 04.48)
applying and accepting `UY13431`, plus zone measurements against TK5 Update 5
and TK3 build listings. Full working notes stay in the MVSHIST repo
(`docs/03-tk3-vermessen.md`, `docs/03-zielzone-dlib.md`).

Created:

- **`MVS-SMP-0001`** — `APPLY` resolves requisites against the CDS, `ACCEPT`
  against the ACDS. Closes the open question in `ECO-0007`.
- **`MVS-SMP-0002`** — a received SYSMOD is unknown to `LIST CDS`; the receive
  state lives in `SMPPTS`.
- **`MVS-SMP-0003`** — `status: myth`. `RMID` is not the SYSMOD that installed
  the element, and RMID numbers carry no ordering.

Changed: `ECO-0007`. Its open question is struck through and answered; its RC-04
statement is qualified rather than replaced, because it was correct as written
and only incomplete.

No conflicts raised. Nothing in `ECO-0007` contradicted the new measurements —
`MVS-SMP-0002` extends its RC-04 note, `MVS-SMP-0001` answers a question it had
left explicitly open.

Not ingested, deliberately: an unexplained `IEF722I - FAILED - INVALID PASSWORD
GIVEN` on three consecutive APPLY jobs (JOB01080, JOB01081, JOB01083) on a
system that has no `SYS1.PASSWORD`. Not reproducible afterwards under controlled
variation of job name, job description, SMPCNTL content and submission path. No
root cause, therefore no document — recorded here so the observation is not lost.
