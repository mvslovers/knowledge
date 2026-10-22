# 2026-10-19 — SMP-4-Messungen aus der Root-CLAUDE.md: Rest nach dem Ingest vom 2026-10-22

Quelle: `~/repos/mvs/.workspace/context/smp.md` (workspace-Commit d9a5c0e), Abschnitt 3, zweiter Absatz.
Die Abschnitte 1, 2, 4 und 5 und der erste Absatz von Abschnitt 3 sind in `MVS-SMP-0006` bis `MVS-SMP-0012`
und `MVS-SMP-0014` eingegangen. Dieser Absatz bleibt liegen: die Volser-/Orphan-Behauptungen liessen sich
aus den zitierten Quellen nicht pruefen (ufsd-Messung nicht oeffentlich belegt, Orphan-Gefahr ist laut
Text selbst eine ungemessene Inferenz). Plattform: mvs38j.

---

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
