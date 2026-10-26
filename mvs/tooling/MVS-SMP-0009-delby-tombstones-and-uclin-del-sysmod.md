---
id: MVS-SMP-0009
title: Every DELETE leaves a DELBY tombstone per id in both zones — UCLIN DEL SYSMOD clears it, a missing id is an error (RC 08), and the next UCLIN block in the step is skipped
status: tested
platform: [mvs38j]
sources:
  - "TK5 Update 5 throwaway container, SMP 4 HMASMP LVL 04.48, 2026-10-21 (as reported in the inbox note; job numbers container-local) — UFSD 1.5.0 (TUFS150, deletes TUFS140) installed through SMP, then RESTORE/REJECT job JOB00059, then the UCLIN removal job UFSDUCL JOB00053 (UCLCDS RC 08, UCLACDS RC 08, LIST RC 04)"
  - "MVS/CE and TK5 throwaway containers, 2026-10-21 — the same documented UCLIN removal job with every id ever spent in one block per zone; only TUFS140 and TUFS150 had existed on the MVS/CE one: HMA2532 x3, HMA2560, HMA2293, step RC 12; re-measured on both distributions with RESETRC between the blocks"
  - "mvslovers/ftpd#143 — MVS/CE system, 2026-09-14: throwaway TTMP112 deleting TTMP900, an id that was never installed; both pre-flight LISTs NOT FOUND RC 04 (JOB00307), tombstone listed (JOB00310), UCLIN removal back to NOT FOUND RC 04 (JOB00311)"
  - "mvslovers/httpd, TSTHCLN removal job JOB00043, TK5 system — 29 x HMA2550 (as quoted in the inbox note; not re-read at ingest)"
  - "ufsd docs/uninstall.md at commit 6804ee7 — the operator procedure and the list of ids"
verified_on: 2026-10-21
verified_platforms: ["MVS/CE (3.0.0)", "TK5 Update 5"]
applies_to: [ufsd, ftpd, httpd, mbt]
tags: [smp, smp4, uclin, delby, tombstone, del-sysmod, hma2532, hma2560, hma2293, hma2550, resetrc, free-id, inventory]
related: [ECO-0007, MVS-SMP-0006, MVS-SMP-0008, MVS-SMP-0013, MVS-SMP-0014]
---

## The claims

1. **Every function that deletes another function leaves a tombstone for the
   deleted id in both zones, even when that id was never installed.** The entry
   is a `FUNCTION` with a `DELBY` mark, not an absent id. `[tested]`
2. **`UCLIN … DEL SYSMOD(id)` is what clears a tombstone.** After it, `LIST`
   answers "not found" (RC 04) and the id can be received again. `[tested]`
3. **`DEL SYSMOD` of an id the zone has never held is an error, not a no-op.**
   `[tested]` This corrects the statement "an id this system never saw reports
   nothing to do" in the inbox note of 2026-10-19, which these measurements
   refute.
4. **After a failed `UCLIN` block, the next `UCLIN` block in the same step is
   ignored.** `RESETRC` between the blocks, or one block per step, avoids it.
   `[tested]`

## 1. Tombstones

After the upgrade UFSD 1.4.0 to 1.5.0 (TUFS150 deleting TUFS140), a `LIST` of
the predecessor does not answer "not found":

```
TUFS140   TYPE = FUNCTION  DELBY = TUFS150
```

The `LIST` ends RC 00. They accumulate: a system that went through every release
holds one per predecessor (the dummy-function case in `MVS-SMP-0014` shows
`TUFS150` deleted by `TZZ0001` and `TUFS140` deleted by `TUFS150` side by side).
ftpd#143 measured it on an MVS/CE system with a throwaway pair: `TTMP112`
deleting `TTMP900`, which had never existed, left

```
TTMP900   TYPE  = FUNCTION
          DELBY = TTMP112
```

in both zones (JOB00310). `DEL SYSMOD(TTMP900)` cleared it in both (JOB00311).

Consequence for the free-id test of `ECO-0007` (`LIST CDS SYSMOD(x)`, RC 04 means
free): an id has three states, not two. RC 04 is free; a `FUNCTION` entry with
`STATUS = REC APP ACC` is installed; a `FUNCTION` entry carrying only `DELBY` is
spent. A tombstone answers RC 00, so the id counts as taken, and it
stays taken until a UCLIN has removed it. Read the stanza, not the return code.

## 2. Clearing them: UCLIN DEL SYSMOD

UFSD's removal job names every id the product ever used, in one `UCLIN` block per
zone (TK5 container, JOB00053; the ACDS block carries the same list without the
`LMOD` lines):

```
 UCLIN CDS .
  DEL SYSMOD(TUFS150) MOD(UFSD) .            (also UFSDSSIR, UFSDCLNP, UFSFMT)
  DEL MOD(UFSD) .                            (also UFSDSSIR, UFSDCLNP, UFSFMT)
  DEL LMOD(UFSD) .                           (also UFSDSSIR, UFSDCLNP, UFSFMT)
  DEL SYSMOD(TUFS150) .
  DEL SYSMOD(TUFS140) .
  DEL SYSMOD(TUFS130) .
  DEL SYSMOD(TUFS120) .
  DEL SYSMOD(TUFS110) .
 ENDUCL .
```

On that system only `TUFS130` to `TUFS150` had ever existed. All ten `LIST`
stanzas afterwards (five ids x CDS and ACDS) answered "NOT FOUND OR WERE NOT
ELIGIBLE". `UCLIN` touches no library: the data sets were deleted by hand
afterwards and the product then installed again, every step RC 00.

The same sequence for the earlier TFTP100 case is in `ECO-0007`. A removal job
for httpd on a TK5 system (TSTHCLN, JOB00043) ended COND 0000 with 29 x
`HMA2550`. httpd#266 shows the effect on the ownership wall (`MVS-SMP-0006`):
once UCLIN had removed the old owner's `MOD` and `LMOD` entries, the blocked
install proceeded.

A removal job has to name **every id the product has ever spent**. A system that
took two upgrades holds two tombstones. A job that clears only the release and its
immediate predecessor leaves the older one standing, and nothing reports that: a
`LIST` answers only about the ids it was given. `[source: ufsd docs/uninstall.md,
6804ee7]`

## 3. A missing id is an error

```
HMA2532 ** SYSMOD ENTRY TUFS120 TO BE DELETED DOES NOT EXIST     (also TUFS110)
HMA2560    UPDATE PROCESSING TERMINATED - UPDATE NOT COMPLETE
```

The block ends RC 08. Every `DEL` that names an existing id is applied
(`HMA2550 UPDATE COMPLETE`); only the statements naming a missing id fail.

The first version of the inbox note said the block was "rejected as a whole".
That was wrong. It was re-measured on an MVS/CE and a TK5 container on
2026-10-21: the CDS entries were gone and only the following block was skipped
(section 4).

Naming only ids that exist ends RC 00. A removal job therefore has to name only
ids that exist, or follow a deleting function that tombstoned them
(`MVS-SMP-0014`, universal variant).

## 4. The cascade into the next block

```
HMA2293 ** CONTROL STATEMENT IGNORED DUE TO PREVIOUS ERROR       (next UCLIN block)
UCLIN step RC 12
```

The `UCLIN ACDS` block that followed the failed `UCLIN CDS` block in the same
step was skipped. The ACDS was left unchanged (`TUFS150` still `STATUS = REC APP
ACC`), while the final `LIST` step answered RC 04 and so looked like a normal
result. Two ways round it:

- `RESETRC .` between the blocks. Measured: the next block then processed its
  own `DEL` statements, with its own `HMA2532` for a missing id. Without it the
  next block is skipped again.
- One `UCLIN` block per step, as in JOB00053. The steps then end RC 08 each and
  nothing is skipped.

**Read the stanzas of the final `LIST`, not the return code.**

## Limits

- Containers, not production systems.
- The effect of `PURGE` on tombstones, and any other UCLIN syntax for the PTS
  entry, are not covered (`MVS-SMP-0013`).
