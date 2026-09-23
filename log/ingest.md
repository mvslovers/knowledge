# Ingest log

One line per ingest run (`CLAUDE.md` §8). This is what makes the KB checkable
rather than merely believable.

| date | source | created | changed | conflicts |
|---|---|---|---|---|
| 2026-09-23 | MVSHIST session — SMP 4 experiments on MVSCE-LAB (jobs JOB01077–JOB01095) and TK3/TK5 zone measurements | `MVS-SMP-0001`, `MVS-SMP-0002`, `MVS-SMP-0003` | `ECO-0007` (open question on requisite zones answered; RC-04 note qualified; `related:` extended) | none |

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
