# Benchmark run — <date> — <model>

Copy this file to `benchmark/results/<date>-<model>.md` and fill it in. One run
covers **both arms**. Questions come from `benchmark/questions.md`.

**Arm:** `with-kb` = the session could read the knowledge base.
`without-kb` = no KB and no access to `benchmark/questions.md` (question text only).

**Protocol reminder:** one fresh session per question per arm. Do not run the
questions sequentially in a single session — see "Running the benchmark" in
`questions.md` for why.

**Disqualifier fired:** the *Disqualifying errors* bullet that failed the answer,
by position (`D1`, `D2`, …), or `—` if none fired. An answer can also fail by
missing a *Must contain* bullet without any disqualifier firing — record that as
`—` with `Pass = no` and name the missing bullet (`M1`, `M2`, …) in Notes.

**Q-03 is blocked** and is excluded from pass counts. Leave its rows blank, or fill
them in for information and keep them out of the totals.

---

## Run metadata

| Field | Value |
|-------|-------|
| Date | |
| Model | |
| KB commit (with-kb arm) | |
| Repo checkouts as of | |
| Grader | |

---

## Results

| Question | Arm | Pass | Disqualifier fired | Tokens | Turns | Notes |
|----------|-----|------|--------------------|--------|-------|-------|
| Q-01 | with-kb | | | | | |
| Q-01 | without-kb | | | | | |
| Q-02 | with-kb | | | | | |
| Q-02 | without-kb | | | | | |
| Q-03 *(blocked)* | with-kb | — | — | | | not scored |
| Q-03 *(blocked)* | without-kb | — | — | | | not scored |
| Q-04 | with-kb | | | | | |
| Q-04 | without-kb | | | | | |
| Q-05 | with-kb | | | | | |
| Q-05 | without-kb | | | | | |
| Q-06 | with-kb | | | | | |
| Q-06 | without-kb | | | | | |
| Q-07 | with-kb | | | | | |
| Q-07 | without-kb | | | | | |
| Q-08 | with-kb | | | | | |
| Q-08 | without-kb | | | | | |
| Q-09 | with-kb | | | | | |
| Q-09 | without-kb | | | | | |
| Q-10 | with-kb | | | | | |
| Q-10 | without-kb | | | | | |

---

## Totals

Scored questions only (Q-03 excluded) — denominator is **9**.

| Arm | Passed | Of | Total tokens | Total turns |
|-----|--------|----|--------------|-------------|
| with-kb | | 9 | | |
| without-kb | | 9 | | |

---

## Observations

Correctness first. Record tokens and turns, but do not trade a pass for either.

- **Questions that flipped** (failed without the KB, passed with it) — the ones
  that justify the KB:
- **Questions that failed in both arms** — the KB does not yet cover these, or
  covers them unretrievably. Each is a candidate KB document or an indexing fix:
- **Questions that passed in both arms** — candidates for retirement or
  replacement with something harder; they measure nothing:
- **Questions that regressed** (passed without the KB, failed with it) — treat as
  urgent. A KB that makes an answer worse is worse than no KB:
- **Disqualifiers that never fired across the whole run** — either the trap is not
  attractive after all, or the wording is not discriminating. Review before the
  next run:
