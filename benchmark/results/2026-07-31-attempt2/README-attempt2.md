# Baseline attempt 2 — 2026-07-31

**Incomplete. Not a valid measurement on its own.** Five of nine questions have no
data at all. The nine answers that did come back are clean and worth scoring.

See `../2026-07-31-aborted/README.md` for attempt 1.

## What changed against attempt 1

| | attempt 1 | attempt 2 |
|---|---|---|
| Working directory | `~/kb-baseline` (held `questions/`, `results/`) | `~/kb-run`, empty |
| `--max-turns` | 3 | 6 |
| Invocations with a result | 6 / 27 | 9 / 27 |

- Command: `claude -p "$(cat Q-NN.txt)" --model opus --output-format json --max-turns 6`
- Model string: _(fill in from `modelUsage` in any JSON here)_
- Q-03 excluded, see `conflicts/CF-2026-001-*.md`

**Attempt 1's contamination defect is fixed.** The working directory was empty, so no
invocation could read the other questions. These nine answers are cleaner evidence
than attempt 1's six.

Note: `--disallowedTools "WebSearch,WebFetch"` was dropped from the command line by
accident in this attempt. Whether any invocation actually reached the web is not
established; check `usage` and the answer texts before treating any of them as
prior-only responses.

## Coverage

| Question | result / 3 |
|---|---|
| Q-01 | 0 |
| Q-02 | 1 |
| Q-04 | 0 |
| Q-05 | 0 |
| Q-06 | 3 |
| Q-07 | 0 |
| Q-08 | 0 |
| Q-09 | 3 |
| Q-10 | 2 |

## Why raising the turn budget is not the fix

Doubling the budget from 3 to 6 moved 6/27 to 9/27. But the movement was not where it
would need to be: **Q-01, Q-05, Q-07 and Q-08 returned nothing in either attempt** —
twelve invocations, two different budgets, two different working directories, zero
results. Q-04 went the other way, from 1/3 to 0/3.

That is suggestive rather than conclusive; 3 → 6 is a short jump and a much larger
budget might still complete them. The question is being left open rather than
resolved, because the design decision below makes it moot.

## The pattern that matters

Across both attempts the questions split cleanly into two groups, and the split is
stable regardless of harness configuration:

**Answered from priors** — Q-06, Q-09, and partly Q-02 and Q-10. Narrative questions
about mechanisms. The model recognises the shape of the problem and produces a
confident answer without looking anything up.

**Never answered** — Q-01, Q-05, Q-07, Q-08. Every one of these names an MVSLOVERS
identifier: `UFSREQ_SETUSER`, `crt0`/`crt1`/`crtm`, the LEGACY translation table. The
model sees a symbol it does not know, reaches for the filesystem, finds an empty
directory, and searches again until the budget is gone.

This is itself a finding, independent of the measurement failure: on our own
identifiers the model **knows that it does not know** and goes looking, rather than
inventing. On MVS-domain questions like Q-09 it does not know that it does not know,
and answers fluently from the wrong platform. The knowledge base buys something
different in each case, and the results file should not blur them together.

## Decision taken as a result

**The baseline arm will run with tools disabled.** The earlier reasoning — that both
arms must be identically equipped or the comparison measures two differences — was
wrong on inspection. `CLAUDE.md` §10 defines the benchmark as measuring *knowledge*,
not workflow: the insurance being bought is against a confidently wrong answer about
an SSI function code, not against inefficient searching. The correct comparison is
therefore *answer from priors* versus *answer grounded in the KB*.

The search behaviour is in any case an artifact of the harness. Asked these questions
in a chat window with no repository, the model answers from priors. It only searches
because file tools were placed in front of it pointing at an empty directory.

The resulting asymmetry between the arms must be stated explicitly at the top of the
final results file, with this reasoning, so that it is on the record rather than
looking like a comparison arranged after the fact.

## Still usable

The nine answers in `answers.txt` are scoreable and uncontaminated by cross-question
reading. Five questions — Q-01, Q-04, Q-05, Q-07, Q-08 — have no data and must come
from the next run.

---

## Footnote (added 2026-07-31 by the baseline run) — the tool-loop question

The baseline run spent its two permitted diagnostic invocations on the open question
above: *does the model burn the turn budget searching?*

**Q-01, tools enabled, no turn cap, empty working directory, `--no-chrome
--strict-mcp-config --disallowedTools "WebSearch,WebFetch"`, `claude` 2.1.220,
`--output-format stream-json` so every tool call would be visible:**

| | |
|---|---|
| `num_turns` | **1** |
| tool calls made | **0** |
| `permission_denials` | 0 |
| `terminal_reason` | `completed` |
| answer | full, 5588 characters |

**The model made no tool call at all and answered directly.** In this environment the
"reaches for the filesystem and searches until the budget is gone" hypothesis is not
reproduced — Q-01 answers in one turn whether tools are present or absent.

Second diagnostic invocation: `--max-turns` **is** accepted by CLI 2.1.220 (it is
undocumented in `--help` but parses and runs), so the empty results in attempts 1 and 2
were not a rejected flag either.

That leaves the cause of the 21/27 and 18/27 empties unexplained rather than explained.
Two candidates not ruled out: the CLI version used for those attempts differed from
2.1.220, and those runs executed on a different host with a different tool and
permission environment. **Nothing here changes the decision to run the baseline arm with
tools disabled** — §1 of `../2026-07-31-baseline.md` argues that from the definition of
the benchmark, not from the empty-result rate.

One thing the baseline run did establish, which bears on this file: with tools removed,
8 of 27 invocations still returned `has_result: true` carrying only a narrated,
un-makeable tool call — two of them fabricating the `ls` output. The reflex survives
tool removal; it changes shape from "no `result` field" to "a `result` field containing
a stub". See §4 of the baseline results file.
