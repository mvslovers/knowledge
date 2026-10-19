# 2026-10-19 — SMP-4-Messungen aus der Root-CLAUDE.md, die in der KB fehlen

Quelle: `~/repos/mvs/.workspace/context/smp.md` (bis 2026-10-19 Teil der Root-CLAUDE.md,
workspace-Commit d9a5c0e). Die Abschnitte unten sind **wörtlich** von dort übernommen,
mit den Jobnummern und Ständen der jeweiligen Messung. Abgleich gegen die KB per grep
am 2026-10-19: `DELBY`, `TALIAS`, `HMA2832`, „conjunctive“ kommen in `mvs/` und
`ecosystem/` nicht vor; `NOT SEL` nur in `MVS-SMP-0004`, `REQ(` in `MVS-SMP-0001` und `ECO-0007`.

Plattform: mvs38j. Gemessen überwiegend auf mvsdev (MVS/CE) und drnmig3a (TK5), siehe
die Jobnummern im Text. Beim Ingest beachten: Teile der Texte sind Projekt-Registry
(FMID-Burned-Liste, ftpd/httpd-Bezüge) und gehören nicht in die KB, nur die SMP-Mechanik.

---

## 1. Element-Ownership-Wall (NOT SEL, RC 00, leere Ziel-Library) und „RC ist kein Erfolgsnachweis“

_Hinweis für den Ingest:_ Erweitert `MVS-SMP-0004` (dort nur `NOT SEL` erwähnt). Enthält auch die `^`-über-mvsMF-REST-Falle bei IDCAMS.

### The element-ownership wall

**SMP keys element ownership on `MOD(name)` in the CDS, not on the library the
element lives in.** A SYSMOD that does not own `MOD(x)` cannot install it: the
element summary prints

```
ELEM   ELEMENT   ELEM
TYPE   NAME      STATUS
MOD    FTPD      NOT SEL
```

nothing is copied, and everything else says success — RECEIVE / APPLY CHECK /
APPLY / ACCEPT all RC 00, `HMA2270 … SUCCESSFULLY COMPLETED`, `STATUS = REC APP
ACC` in both zones, and an empty target library. Measured twice: ftpd 1.1.0-dev
on mvsdev 2026-09-13, and again 2026-09-14 (JOB00291) where a *fresh, free*
FMID installing into a dataset unrelated to any other install still lost to the
owner of the module name.

The message that separates a real install from that one is
`HMA2380 COPY SUCCESSFUL - MOD=… - LMOD=… - LIBRARY=…`. **Verify every install
by listing the members of the target library**, never by the condition codes.

**That generalises, and it cost three projects a day each.** A condition code
says whether a job ran, never whether the work happened — met three times
independently on 2026-09-14: the `NOT SEL` install above (RC 00, empty target
library); an upgrade whose `STEPLIB` was never re-pointed (every step RC 00,
old server still serving); and a multi-line IDCAMS scratch that deleted one of
six data sets and reported a single non-zero code (httpd, drnmig3a). Each time
the inventory answered correctly and the return code did not. **Read the
inventory — the member list, the `LIST` stanza, the startup banner.**

That IDCAMS run carries a trap of its own, and it belongs to the transport
rather than to IDCAMS: **`^` does not survive the mvsMF REST API.** `IF LASTCC
^= 0` arrives as `.=`, IDCAMS answers `IDC4229I INVALID RELATIONAL EXPRESSION`
and then discards the rest of the input stream — so every statement after the
bad card is skipped and the job reports one error instead of five omissions.
Write `NE`, and list afterwards (httpd, 2026-09-14).

Two consequences:

- Versioning the product datasets never bought a clean cut between releases —
  the collision is on the module name in the inventory, not on the dataset.
- **A test install needs throwaway module names as well as a throwaway id.**
  A throwaway FMID alone measures this wall instead of whatever it meant to
  measure.

---

## 2. ++VER DELETE: Ablauf, Tombstones, Akkumulation

_Hinweis für den Ingest:_ Nicht in der KB (`DELBY` kommt nirgends vor). `ECO-0007` beschreibt noch das UCLIN-Upgrade, das DELETE ersetzt hat — mögliche Obsoleszenz dort prüfen.

**How DELETE works**, measured on mvsdev 2026-09-14 (HMASMP LVL 04.48, jobs
JOB00291 / JOB00293 / JOB00296–00299):

- SMP deletes the predecessor's LMODs from the target library
  (`HMA2240 SUCCESSFULLY DELETED LMOD …`) and then copies the new ones in
  (`HMA2380 COPY SUCCESSFUL … SYSMOD=<new>`). `MOD(x)` comes back carrying the
  new `FMID` and `RMID` — **element ownership transfers**.
- **Each zone is deleted by its own pass**: APPLY the CDS, ACCEPT the ACDS.
  Skip the ACCEPT and the old id survives as `REC APP ACC RGN` in the ACDS.
- A deleted id has no SMPSCDS backup entry, so the APPLY ends **RC 04** on
  `HMA2461 … NOT FOUND ON SMPSCDS LIBRARY` *after* reporting `HMA2270`
  success. mbt relaxes the ACCEPT gate to `COND=(4,LT,APPLY.HMASMP)` when
  `delete` is set, and leaves it strict otherwise.
- The predecessor is left as a tombstone — `TYPE = FUNCTION / DELBY = <new>` —
  which `LIST` reports at **RC 00**, so the "RC 04 + empty list = free" rule
  below reads it as occupied. That is correct: the id stays spent.

This replaces the `UCLIN` upgrade step entirely. ufsd's `docs/uninstall.md` keeps its
UCLIN job for *removing* a product and for cleaning up a test install.

**A DELETE leaves a tombstone in both zones**, even for an id that was never
installed: `TYPE = FUNCTION` / `DELBY = <new>`. `LIST` answers **RC 00** for it,
so the "RC 04 and an empty list means free" rule above has a third state — read
the stanza, not the return code. A plain `UCLIN … DEL SYSMOD(<old>)` clears it
— measured by httpd on drnmig3a 2026-09-14 (`TSTHCLN JOB00043`, 29 ×
`HMA2550`, COND 0000).

**They accumulate, one per upgrade, so a removal job must name every id the
product has ever spent.** A system that took two upgrades holds two tombstones;
deleting the release plus its immediate predecessor clears the newer and leaves
the older standing for good. Nothing reports that: the `LIST` answers only
about the ids it was given, and a surviving tombstone answers RC 00 while the
cleared ones answer RC 04, so it does not even lift the step's return code.
Write one `DEL SYSMOD(<id>)` per spent id in both zones. An id this system
never saw reports nothing to do, so the list needs no judgement about which
releases the system has seen — and that judgement is precisely what goes wrong.
ufsd's `docs/uninstall.md` is the worked example.

---

## 3. DELETE und umbenannte Datasets (ddname statt DSN, HMA2832), APF dsname+volser

_Hinweis für den Ingest:_ Nicht in der KB (`HMA2832` kommt nirgends vor). Der APF-Absatz ist teilweise `inferred` (Orphan-Gefahr ungemessen, so im Text markiert).

**A DELETE never touches the predecessor's data set, and this is the trap of
the rename.** SMP records the *ddname* an element was installed through and
never the data set behind it — the CDS `LMOD` entry reads `SYSTEM LIBRARY =
LINKLIB`. So a SYSMOD deleting its predecessor resolves that ddname in **its
own** job, deletes from the new library, and leaves the old data set populated,
working and still APF-authorised, with nothing in the job log naming it.
Measured on mvsdev 2026-09-14 (mvslovers/ftpd#145) with a throwaway module name
in libraries belonging to no product — **this is SMP's behaviour, not any one
project's**, so it transfers to every project in the ecosystem without a
per-project measurement. What does need checking per project is only which of
the two cases below it falls into.

Two consequences for a project dropping the version qualifier:

- **Last qualifier unchanged** (`FTPD.V1R0M2.LINKLIB` → `FTPD.LINKLIB`, both
  `LINKLIB`): the install succeeds. Re-pointing `STEPLIB`/`IEAAPF00` and
  scratching the old libraries are then *the upgrade*, not housekeeping — skip
  them and the old server keeps running while every condition code says the
  upgrade worked. ufsd and ftpd are both this case.
- **Last qualifier changed**: APPLY CHECK fails RC 12 with `HMA2832 <dd> DDCARD
  MISSING` and the APPLY is skipped. It fails safely, but the shipped job needs
  a `//HMASMP.<olddd> DD` naming the old data set, which the generator cannot
  emit — `delete` is a list of ids and carries no DSNs. Filed as
  **mvslovers/mbt#100**. Neither ufsd nor ftpd is in this case; the first
  project to change a last qualifier will be, and **the failure is loud while
  the cause is not** — `HMA2832` names a ddname and says nothing about a
  renamed data set. Read this paragraph before renaming one.

**An APF entry is `dsname` *plus* volser, and the rename upgrade replaces one
rather than adding one.** A library that is present but sitting on a different
volume is there and not authorised: ufsd degrades quietly to SVC 244 where RAKF
permits it and does not start at all where it does not, and `UFSD007I` reports
which route it took (ufsd-measured). Two consequences once the old data set is
scratched: the new entry must *replace* the old, and an orphaned entry is more
dangerous after the scratch than before it, because a data set later allocated
under that name **on that volume** inherits the authorisation the entry still
grants. So an orphan left behind is worse than an old library left in place
(the volser pairing is measured; the orphan hazard is httpd's inference and has
not been measured).

---

## 4. Aliase nur mit TALIAS

_Hinweis für den Ingest:_ Nicht in der KB. Offener Punkt: Release, das einen Alias weglässt, ist ungemessen (mbt#115).

**Aliases travel as `TALIAS`, or not at all.** A load module's aliases
(`aliases = [...]` on `[[module]]`, mbt#113) reach the LKLIB as true aliases,
but a `++MOD` without `TALIAS(…)` makes SMP copy the main member only: target
library and DLIB end up without a single alias, and every step reports CC 0000
(`TTST008`, JOB00509). With `TALIAS` on the `++MOD` — the JCLIN stays COPY —
SMP installs true aliases into both libraries, re-binds nothing (`AC=1` and
`norent` survive) and records `TALIAS = …` on the MOD entry in both zones
(`TTST009`, JOB00515/00516). An upgrade with `DELETE` moves them onto the new
module; all three names ran the new code (`TTST010`, JOB00518/00519). mbt emits
`TALIAS` since **mvslovers/mbt#114**. **Not measured: a release that drops an
alias** — APPLY deletes only the LMOD in the target library (ACCEPT deletes
module and aliases in the DLIB), so a dropped alias most likely survives there,
pointing at the deleted module. **mvslovers/mbt#115**; read it before removing
an alias from a shipped product.

---

## 5. REQ ist konjunktiv — keine Versionsuntergrenze per REQ

_Hinweis für den Ingest:_ Erweitert `MVS-SMP-0001` (requisite zone) — dort prüfen, ob die AND-Semantik schon steht.

### `REQ` is an AND, so it cannot express a version floor

**Measured on mvsdev 2026-09-14** (job `TZMFREQ`, throwaway ids `TTST005`–
`TTST007`, APPLY CHECK only, all three REJECTed afterwards). Three SYSMODs
carrying nothing but a `++VER`:

| `REQ` | APPLY CHECK |
|---|---|
| `REQ(THTP410)` — installed | **CC 0000** |
| `REQ(TZZZ999)` — absent | CC 0012 |
| `REQ(THTP410,TZZZ999)` | **CC 0012** |

```
HMA3022 ** APPLY PROCESSING TERMINATED FOR SYSMOD TTST007
        - REASON = MISSING/NOGO REQUISITES:
HMA3590     --- TZZZ999 REQ
```

A present requisite does not satisfy a list that also names an absent one:
`REQ` is **conjunctive**. So the tempting shape — name every level of a
dependency you can work with, `REQ(THTP410,THTP411,…)`, and add the next one
each release — demands **all of them installed at once**, which one-id-per-
release makes impossible: `THTP410` itself carries `DELETE VER(001) = THTP400`.
Such a list makes the product uninstallable everywhere.

There is no range syntax either, so `REQ` can only ever say *"exactly this
level"*. That fails in both directions for a dependency that moves: an older
level does not satisfy it, and a system where a **newer** one was installed
fresh never saw the id being named.

**So a version floor on another product belongs in the installation guide, as
prose.** Every project in the ecosystem declares `prereq = []` and says so in
its docs — httpd on UFSD, mvsMF on httpd. `REQ` remains right only for a
genuinely fixed co-requisite that will not move.

Two things the probe also settled: a `++FUNCTION` with no elements is received
without complaint (`HMA3971 … HAS NO ELEMENTS` is a warning, `HMA3930
SUCCESSFULLY RECEIVED` follows), so a requisite question needs no throwaway
module names — the APPLY CHECK fails long before elements matter. And `REJECT`
does clean a received-but-never-applied id out of the inventory (`HMA2270`,
then `LIST` reports RC 04 not found) — but the id stays **burned** all the
same, exactly as `TXPR100` did.
