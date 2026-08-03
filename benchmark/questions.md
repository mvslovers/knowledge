# MVSLOVERS Knowledge-Base Benchmark

Ten fixed questions used to measure whether the knowledge base improves the
**correctness** of answers about MVS 3.8j internals and about our own projects.

Every question is trap-shaped by construction: a competent model without the KB
will answer fluently and be specifically wrong — usually because public training
data describes MVS/XA, ESA or z/OS behaviour, or because it assumes the
industry-standard value where we deliberately deviate.

An answer fails `provenance` if its **justification for a graded fact rests on a
named codebase, file, or product that is not ours**. The question asks about our
system; an answer about a different system that happens to agree is not knowledge
of ours. An answer that reasons from the symptoms in the question and attributes
the behaviour to our system *without naming a source* is **not** a provenance
failure — it is graded on *Must contain* alone. Record provenance three-valued:
`ours` / `foreign` / `none`. Applies to both arms.

**Scoring.** An answer passes only if it states every bullet under *Must contain*
and commits none of the *Disqualifying errors*. Partial credit is not recorded —
correctness is the point. Run the suite with and without the KB and compare pass
counts first, tokens and turns second.

A *Must contain* bullet is satisfied **only if the answer commits to the statement
as its conclusion**, not if it lists it among several co-equal possibilities. A
ranked list whose top-ranked item is stated as the conclusion counts as
committing; a list of co-equal alternatives does not.

## Running the benchmark

**One fresh session per question, per arm.** Never run the questions sequentially
in a single session. Q-04 and Q-05 both read `httpxlat.c`, so whichever runs first
puts the file in context and hands the second one its answer. Q-09 and Q-10 share a
meta-lesson — distrust our own toolchain before suspecting MVS — and a model that
has just learned it on one will apply it to the other. Accumulated context
contaminates later questions and inflates the second arm, which is exactly the
measurement the benchmark exists to make.

**The KB-less arm must run with no access to this file**, and no access to the KB.
The question text alone goes into the session; the expected answer, must-contain
bullets and evidence stay with the grader.

**Record per question:** pass/fail, which disqualifier fired if any, tokens, turns.
Use `benchmark/results/TEMPLATE.md`; copy it to
`benchmark/results/<date>-<model>.md` for each run.

**Provenance.** Every claim in every *Expected answer* was read out of the repos
while this file was written. Line numbers refer to the state of `main` in each
local checkout as of 2026-07-27. Nothing here comes from model priors; where a
prior and a source disagreed, the source won and the disagreement became the
question.

Nine questions are scored. Q-03 is retained in full but **blocked** — its premise
is unverified, so it is excluded from pass counts until settled.

| ID | Category | Depth | Platform | Status |
|----|----------|-------|----------|--------|
| Q-01 | mvs-domain | multi-source | mvs38j | scored |
| Q-02 | mvs-domain | multi-source | mvs38j | scored |
| Q-03 | mvs-domain | multi-source | mvs38j | **blocked — not scored** |
| Q-04 | encoding | single-lookup | n/a | scored |
| Q-05 | encoding | single-lookup | n/a | scored |
| Q-06 | project-internals | multi-source | mvs38j | scored |
| Q-07 | project-internals | single-lookup | mvs38j | scored |
| Q-08 | project-internals | multi-source | mvs38j | scored |
| Q-09 | debugging | multi-source | mvs38j | scored |
| Q-10 | debugging | multi-source | mvs38j | scored |

---

### Q-01 — Cross-address-space POST and WAIT from an SSI router

**Category:** mvs-domain
**Depth:** multi-source
**Platform:** mvs38j

**Question**

I have an SSI routine that runs in the caller's address space and has to wake my
server STC, which is waiting in a different address space. The STC then has to
wake the caller back up when the reply is ready. What do I use for the POST in
each direction, what state do I have to be in, and where should the ECBs live?

**Expected answer**

Not SVC 2. Both POSTs go through the POST branch entry addressed by `CVT0PT01`
in the CVT, issued from supervisor state / key 0 — that is what libc370's
`__xmpost(ascb, ecb, postcode)` does. SVC 2 fails both ways: cross-address-space
from problem state gives S102, and from supervisor state it gives S202. The reply
WAIT is the ordinary `WAIT` (SVC 1) issued from **problem** state, and its ECB
must be in key-8 storage — a stack-local ECB in the router's own frame, with a
pointer to it handed to the server. Waiting from problem state on a key-0 CSA ECB
gives X'201' (S047 on the equivalent protection failure).

**Must contain**

- The POST must use the branch entry at `CVT0PT01`, not SVC 2 / the `POST` macro.
- The POSTing side must be in supervisor state (key 0) when it does so.
- The reply ECB the router waits on must be a **stack-local in the router** —
  key-8 storage owned by the client — **not** the key-0 CSA control block. An
  answer that places it in common storage does not satisfy this bullet even if it
  gets the storage key right.
- The WAIT itself must be issued from problem state.
- At least one of the abend codes tying a wrong choice to its failure: S102
  (cross-AS SVC 2 from problem state), S202 (SVC 2 from supervisor state), or
  X'201' / S047 (WAIT from problem state on a key-0 ECB).

**Disqualifying errors**

- Recommending the `POST` macro / SVC 2 with an `ASCB=` (and `ERRET=`) operand as
  the cross-address-space POST mechanism.
- Placing the client's reply ECB in the **key-0** CSA block "so both address
  spaces can see it". (An answer that puts the ECB in common storage but obtains
  it in the *caller's* key does not fire this disqualifier — it fails `M3`
  instead. This disqualifier is about the X'201' trap, not about the location.)
- Stating that the WAIT should be issued in supervisor state, or that the state of
  the waiter does not matter.
- Claiming the POST can be issued from problem state as long as the ECB is shared.

**Evidence**

- `ufsd/docs/cross-as-reference.md:13-15` — summary table: POST cross-AS via
  `__xmpost` / CVT0PT01 in supervisor state; SVC 2 from problem state → S102;
  SVC 2 from supervisor → S202; WAIT (SVC 1) from problem state, key-0 ECB →
  X'201'.
- `ufsd/docs/cross-as-reference.md:75-133` — Abends 1, 3, 4 and 5, each with
  symptom, root cause and fix.
- `ufsd/src/ufsd#ssi.c:178` — `ECB local_ecb;` declared as a router stack local,
  commented "key-8 stack ECB: WAIT target for this request".
- `ufsd/src/ufsd#ssi.c:248-249` — `req->client_ecb_ptr = &local_ecb;` and
  `req->client_ascb = __ascb(0);`.
- `ufsd/src/ufsd#ssi.c:222, 301` — "`__xmpost` (CVT0PT01) must be called from
  supervisor state"; `__xmpost(anchor->server_ascb, &anchor->server_ecb, 0)`.
- `ufsd/src/ufsd#que.c:9-10, 198` — "All client ECB notifications use `__xmpost`
  (CVT0PT01 branch entry) from supervisor state. `__xmpost` does not issue SVC 2."
- `libc370/src/clib/@@xmpost.c` — the inline asm: `L 15,CVTPTR` /
  `L 15,CVT0PT01-CVTMAP(,15)` / `BALR 14,15`, with R13 = ASCB, R11 = ECB,
  R10 = post code.
- `nsf370/m5-stage0a-ssi-probe.md:22-24` — the same state/key rules restated
  independently for NSF, inherited "verbatim on the UFSD AP-1c pattern".

**Likely failure without KB**

The model will describe the cross-memory POST interface it knows from MVS/XA and
later: `POST ECB,ASCB=addr,ERRET=addr`, presented as the sanctioned way to post
across address spaces, possibly with `MF=` list-form scaffolding. It is an
attractive answer because it *is* the documented interface on later releases and
appears in every SPL-derived text. Expect it to be silent on the storage key of
the waiting ECB, or to actively recommend putting the ECB in CSA "since both
address spaces must be able to address it" — which is the exact X'201' trap. A
secondary common error is asserting the POST must be issued in the waiting task's
key rather than key 0.

---

### Q-02 — Starting an SSI-registered STC a second time

**Category:** mvs-domain
**Depth:** multi-source
**Platform:** mvs38j

**Question**

Our server registers itself dynamically in the SSI (it builds an SSCT and SSVT at
startup). If somebody issues `S` for it a second time while the first copy is
still up, what actually appears on the console? We have our own "already
registered" check in the program and it never seems to produce a message.

**Expected answer**

The console shows **IEF612I PROCEDURE NOT FOUND**. MVS routes the START through
the SSI — the job-step / system-internal notification goes to the registered
router — *before* the second instance's own code gets control. The registered
router rejects that call and the failure surfaces as IEF612I. Your in-program
guard is a second layer that is never reached, which is why it stays silent.
Stopping the first instance deregisters the SSCT and `S` works again. The related
operational hazard: if the STC abends without its ESTAE cleaning up, the SSCT
stays registered until IPL, which is why the deregistering ESTAE is mandatory.

**Must contain**

- The message is **IEF612I** (PROCEDURE NOT FOUND).
- The cause is that MVS routes the START request through the SSI to the
  already-registered router before the second instance's own code runs.
- The application's own "already registered" check does not fire — it is not
  reached.
- Stopping the first instance (which deregisters the SSCT) makes `S` work again.

**Disqualifying errors**

- Naming IEF403I, IEF450I, IEF238D, or a duplicate-name / ENQ conflict as the
  symptom.
- Claiming the second START succeeds and produces two live instances.
- Attributing the message to the application's own duplicate-registration check.
- Claiming MVS detects the duplicate by procedure name or job name.

**Evidence**

- `ufsd/docs/cross-as-reference.md:135-141` — "Known Behavior: double start":
  "While UFSD is registered, `S UFSD` fails with IEF612I PROCEDURE NOT FOUND. MVS
  routes system-internal SSI calls (job-step notifications) through ufsdssir which
  rejects them. After `/P UFSD` (deregisters SSCT), `S UFSD` works again. If UFSD
  abends without cleanup, SSCT remains registered until IPL. ESTAE exit is
  mandatory."
- `nsf370/m5-stage0a-ssi-probe.md:104-107` — "while the SSCT is live the 'already
  registered' symptom is **IEF612I** (MVS routes the START through the SSI before
  `main` runs — ufsd's documented double-start), not NSFP092E (that guard is the
  second layer)."
- `nsf370/m5-stage0a-ssi-probe.md:69-71` — the live MVSCE Stage-1 run: after a
  clean `P NSFP`, the second `S NSFP` re-registered cleanly with **no** IEF612I and
  no NSFP092E — confirming the message is tied to the SSCT still being live rather
  than to the restart itself.

**Likely failure without KB**

The model will reach for the ordinary duplicate-STC story and answer IEF403I /
"job already active", or describe ENQ contention on the procedure name, or say the
second START simply starts a second address space that then fails in the
application's own registration check. IEF612I PROCEDURE NOT FOUND is
counter-intuitive precisely because the procedure obviously *is* found — it was
found the first time — so a model reasoning from the message text will reject it.
Expect a confident recommendation to "add a duplicate-instance guard in the
program", which is the layer the evidence shows is never reached.

---

### Q-03 — Running authorized without an APF-authorized library

**STATUS: BLOCKED — premise unverified.** Excluded from scoring until
`SYS1.PARMLIB(IEAAPF00)` is inspected directly. See G-1, G-2.

**Category:** mvs-domain
**Depth:** multi-source
**Platform:** mvs38j

**Question**

Our servers issue IEFSSREQ and do key-0 work in the caller's address space, so
they clearly run authorized. But neither their LINKLIB nor the STEPLIBs the
clients run from are listed in IEAAPF00. How is that possible, and what would I
have to do to get a new program of ours into the same state?

**Expected answer**

They authorize themselves at run time. libc370's `__autask()` checks the current
state with `TESTAUTH FCTN=1`, and if not authorized issues **SVC 244** with R0 = 0
and R1 = 1, then re-tests with `TESTAUTH FCTN=1` and records success in
`crt->crtauth` (`CRTAUTH_ON`). The inverse, `__uatask()`, issues SVC 244 with
R0 = 0 and R1 = 0 to drop it. Callers use the wrapper `clib_apf_setup(pgm)`, which
calls `__autask()` and then also authorizes the STEPLIB (`__austep()`) and the
program name (`clib_auth_name`, plus `CTHREAD`). This is independent of whether
the load library is APF-authorized: on MVSCE, NSF.LINKLIB is not in IEAAPF00, and
neither are ufsd's or httpd's STEPLIBs, yet all of them run authorized. To get a
new program there, call `clib_apf_setup()` early — no IEAAPFxx change and no IPL
are required.

**Must contain**

- The mechanism is a runtime self-authorization SVC — specifically **SVC 244**.
- `__autask()` issues SVC 244 to authorize and `__uatask()` issues SVC 244 to
  unauthorize; the two differ in the register setup. (Do not grade the specific
  register contract — see gap G-2. The R0/R1 values in the expected answer are
  descriptive of the two call sites, not a documented interface.)
- It is reached through libc370's `__autask()` / `clib_apf_setup()`, and works
  regardless of whether the load library appears in IEAAPFxx.
- Authorization state is checked with `TESTAUTH FCTN=1`.

**Disqualifying errors**

- Answering that the library *must* be in IEAAPFxx and the module link-edited
  AC(1), and that there is no other way — i.e. denying that a runtime path exists.
- Naming MODESET (SVC 107) as the mechanism that confers APF authorization.
- Claiming an IPL or an IEAAPFxx update is required to put a new program into the
  same state.
- Claiming the authorization is inherited from the caller's JSCB (JSCBAUTH) merely
  by being LINKed from an authorized program.

**Evidence**

- `libc370/src/clib/@@autask.c` — `__autask()`: inline `TESTAUTH FCTN=1`, then
  `try(authorize,0)` where `authorize()` is `SR 0,0 / LA 1,1 / SVC 244`, then a
  second `TESTAUTH FCTN=1`, then `crt->crtauth |= CRTAUTH_ON`.
- `libc370/src/clib/@@uatask.c` — `__uatask()`: `unauthorize()` is
  `SR 0,0 / SR 1,1 / SVC 244`, and clears `CRTAUTH_ON`.
- `libc370/src/clib/@@apfset.c` — `clib_apf_setup()` → `unauth_setup()` →
  `__autask()`, then `__austep()` for the STEPLIB, then `auth_pgm()`
  (`clib_auth_name(name)`, `clib_identify_cthread()`, `clib_auth_name("CTHREAD")`).
- `nsf370/m5-stage0a-ssi-probe.md:35-40` — "a task self-authorises at runtime via
  `clib_apf_setup` → `__autask()` (**SVC 244**), independent of its library.
  Verified against `SYS1.PARMLIB(IEAAPF00)`: **NSF.LINKLIB is not APF, and neither
  are UFSD's/HTTPD's steplibs**, yet both run authorized on MVSCE. … No
  IEAAPFxx/IPL install needed."
- `nsf370/m5-stage0a-ssi-probe.md:72-74` — live gate: "The client self-authorized
  via SVC 244 from TESTLIB", TSTSSI batch CC 0 + TSO CC 0.

**Likely failure without KB**

The model will give the standard, correct-for-z/OS answer and stop: the library
must be APF-authorized via PROGxx/IEAAPFxx, the module link-edited with AC(1), and
the program entered as a job step — with the usual warning that there is no
legitimate way to become authorized at run time, since that would be an integrity
exposure. That framing makes it very unlikely to volunteer SVC 244 at all; if
pushed, expect MODESET (SVC 107, which changes state and key, not APF
authorization) or an insistence that "authorized library plus AC(1)" is necessary
and sufficient. It cannot know that this ecosystem's target systems supply a user
SVC 244 that libc370 drives.

---

### Q-04 — What an ASCII newline becomes in httpd's translation tables

**Category:** encoding
**Depth:** single-lookup
**Platform:** n/a

**Question**

We're pushing text out through httpd's ASCII↔EBCDIC layer. Which EBCDIC byte does
an ASCII newline (0x0A) turn into, and if I take that byte back the other way do I
get 0x0A again? Also, what happens to an EBCDIC 0x25 that arrives from somewhere
else?

**Expected answer**

ASCII 0x0A maps to EBCDIC **0x15** (NEL), not to 0x25. This is a deliberate
override of both pure CP037 and pure IBM-1047, and it is present in *both* of those
tables in httpd, because the whole mvslovers ecosystem uses 0x15 as its newline
(the C compiler's `'\n'`, the C runtime's `printf`, and every UFS file written by a
C program). The reverse direction is deliberately asymmetric: `etoa[0x15]` is 0x0A,
so 0x0A → 0x15 → 0x0A round-trips, but `etoa[0x25]` is **0x85** (Latin-1 NEL), left
unchanged — an EBCDIC LF arriving from elsewhere does not come back as 0x0A. The
LEGACY table is the exception: its `atoe` maps 0x0A to 0x25, and its `etoa`
collapses both 0x15 and 0x25 to 0x0A.

**Must contain**

- ASCII 0x0A maps to EBCDIC **0x15**, not 0x25, under CP037 *and* under IBM-1047.
- This is a deliberate deviation from the pure code pages, motivated by the
  ecosystem's use of 0x15 as newline.
- `etoa[0x25]` is **0x85**, not 0x0A — the two directions are not symmetric.

**Disqualifying errors**

- Answering 0x25 as the CP037 or IBM-1047 result for ASCII 0x0A.
- Stating that the tables are a symmetric bijection, or that any EBCDIC byte
  translated to ASCII and back is unchanged.
- Claiming EBCDIC 0x25 translates to ASCII 0x0A in the CP037 or IBM-1047 tables.

**Evidence**

- `httpd/src/httpxlat.c:29-38` — the CP037 header comment: "ASCII LF (0x0A) ->
  EBCDIC NEL (0x15)  <- override for ecosystem", "EBCDIC NEL(0x15) -> ASCII LF
  (0x0A)", "EBCDIC LF (0x25) -> ASCII NEL (0x85)  <- unchanged", plus the rationale
  ("Pure CP037 maps ASCII LF to EBCDIC LF (0x25), but the mvslovers ecosystem uses
  NEL (0x15) as newline …").
- `httpd/src/httpxlat.c:43` — `cp037_atoe` row 0x08-0x0F: index 0x0A holds `0x15`.
- `httpd/src/httpxlat.c:91` — `cp037_etoa` row 0x10-0x17: index 0x15 holds `0x0A`.
- `httpd/src/httpxlat.c:93` — `cp037_etoa` row 0x20-0x27: index 0x25 holds `0x85`.
- `httpd/src/httpxlat.c:150-160, 164, 212, 214` — the same comment and the same
  three values in `ibm1047_atoe` / `ibm1047_etoa`. (Both comments name the
  ecosystem's newline emitters as "c2asm370 '\n', crent370 printf" — the legacy
  names for what are now cc370 and libc370. The expected answer uses the current
  names; the fact graded is the 0x15 convention, not the tool naming.)
- `httpd/src/httpxlat.c:282` — `legacy_atoe` row 0x08-0x0F: index 0x0A holds `0x25`
  (the un-overridden value).
- `httpd/src/httpxlat.c:320-323` — `legacy_etoa`: index 0x15 → `0x0A` (marked "NB:
  [0x15] = 0x0A (httpetoa.c switch baked in)") and index 0x25 → `0x0A`.
- Commit `71b21b3` (httpd, 2026-03-21) — "fix: map ASCII LF to EBCDIC NEL (0x15) in
  IBM-1047 atoe table".
- Commit `00119cb` (httpd, 2026-03-21) — "fix: correct CP037 translation table
  values for [ ] and add NEL override".

**Likely failure without KB**

The model will answer 0x25 with high confidence, because that *is* the correct
pure-CP037 and pure-IBM-1047 value for LF and it appears in every published code
page chart. It will then almost certainly assert the round trip is symmetric, since
a code page is normally a bijection — missing that the override is applied to
`atoe` only, leaving `etoa[0x25] = 0x85`. A model that has seen z/OS USS material
may correctly mention 0x15 as "newline" but will typically frame it as an
IBM-1047-only property and still give 0x25 for CP037, which is wrong here for both
tables.

---

### Q-05 — Square brackets and the pipe character across httpd's three codepages

**Category:** encoding
**Depth:** single-lookup
**Platform:** n/a

**Question**

A JSON payload going through httpd is coming back with mangled square brackets and
a broken pipe character, and it seems to depend on how the server is configured.
What actually differs between the codepage options, and which one would break the
pipe?

**Expected answer**

httpd offers three pairs — CP037 (the default), IBM1047 and LEGACY. CP037 puts `[`
at EBCDIC 0xBA and `]` at 0xBB; IBM-1047 puts them at 0xAD and 0xBD. LEGACY is a
documented hybrid: otherwise CP037-shaped, but it takes the IBM-1047 bracket
positions (0xAD / 0xBD). The pipe is broken **only** under LEGACY, which maps `|`
to 0x6A instead of 0x4F and whose reverse table decodes 0x4F back to `]` rather
than `|`. Under CP037 and IBM-1047, `|` is 0x4F in both directions. LEGACY exists
purely for backward compatibility with httpd 3.3.x and is marked in the source as
carrying known bugs.

**Must contain**

- CP037: `[` = 0xBA, `]` = 0xBB. IBM-1047: `[` = 0xAD, `]` = 0xBD.
- LEGACY uses the IBM-1047 bracket positions (0xAD / 0xBD) while otherwise being
  CP037-shaped — it is a hybrid, not a third clean code page.
- Under LEGACY, `|` maps to 0x6A rather than 0x4F, and the reverse table decodes
  0x4F as `]` — so the pipe does not round-trip under LEGACY only.

**Disqualifying errors**

- Giving 0xAD as the CP037 position for `[` (that is the IBM-1047 value).
- Stating that all three tables agree on `|`, or that `|` is 0x4F in all of them.
- Describing LEGACY as plain CP037 or as plain IBM-1047.
- Claiming the bracket positions are the same in CP037 and IBM-1047.
- Naming any configuration other than LEGACY as the cause of the broken pipe.
  (Added 2026-08-01. The 2026-07-31 baseline showed the bullet above it cannot
  fire against the most likely wrong answer, which does not know there are three
  tables at all and blames IBM-500 or a national code page; this one fires 3/3 on
  that run. Both are kept — the older bullet still catches an answer that *does*
  know the three tables and claims they agree on `|`.)

**Evidence**

- `httpd/src/httpxlat.c:60` — `cp037_atoe` row 0x58-0x5F: `[` (0x5B) → `0xBA`,
  `]` (0x5D) → `0xBB`.
- `httpd/src/httpxlat.c:181` — `ibm1047_atoe` row 0x58-0x5F: `[` → `0xAD`,
  `]` → `0xBD`.
- `httpd/src/httpxlat.c:68, 189` — `|` (0x7C) → `0x4F` in both `cp037_atoe` and
  `ibm1047_atoe`; `cp037_etoa` / `ibm1047_etoa` index 0x4F → `0x7C`.
- `httpd/src/httpxlat.c:269-278` — the LEGACY header: "HTTPD 3.3.x hybrid tables
  (backward compatibility) … Known issues: Brackets [/] patched to IBM-1047
  positions (0xAD/0xBD); Pipe | left at non-standard position (0x6A atoe, wrong
  etoa)".
- `httpd/src/httpxlat.c:292` — `legacy_atoe` row comment "[ = 0xAD, ] = 0xBD
  (1047), | = 0x6A (broken)", with those values on the following line.
- `httpd/src/httpxlat.c:297` — `legacy_atoe` row comment "| at 0x6A instead of 0x4F
  (KNOWN BUG)", with `0x6A` at index 0x7C.
- `httpd/src/httpxlat.c:328-329` — `legacy_etoa` row 0x48-0x4F, commented "NB:
  [0x4A] = 0x5B([), [0x4F] = 0x5D(]) — legacy": index 0x4F holds `0x5D` (`]`), not
  `0x7C` (`|`).
- `httpd/src/httpxlat.c:360-362, 385-406` — the three `HTTPCP` pairs and
  `http_xlate_init()`, which selects on the strings "CP037", "IBM1047" and "LEGACY"
  and falls back to CP037 with `HTTPD070E` on an unknown name.

**Likely failure without KB**

The most attractive wrong answer is `[` = 0xAD, `]` = 0xBD stated as *the* EBCDIC
bracket positions, because IBM-1047 is the code page most represented in training
data (it is the z/OS USS default) and its bracket positions are widely quoted. A
model will typically present those as "the" EBCDIC values and therefore see no
difference between the options at all. On the pipe it will say 0x4F everywhere —
correct for two of the three tables and wrong for exactly the one the question is
about. Expect it to treat LEGACY as either "an older CP037" or "an alias for
IBM-1047" rather than a hybrid with two specific documented defects.

---

### Q-06 — Why a CGI cannot see httpd's core statics

**Category:** project-internals
**Depth:** multi-source
**Platform:** mvs38j

**Question**

A CGI module calls back into an httpd core function through the vector table, and
that function reads a file-scope static that httpd set up at init. From the CGI the
static always reads back empty, so the call silently does nothing. The CGI is in the
same address space as httpd. What's going on, and what's the right fix?

**Expected answer**

Being in the same address space is not enough. A CGI is a separately linked
reentrant module brought in with LINK, and it runs under **its own GRT** — its own
writable static area. httpd's core statics live in httpd's GRT, so the same core
function called from the CGI reads the CGI's empty slot instead. That is exactly the
`http_logout()` bug (#113): it reached the credential store through
`credtok_logout()` → `cred_array()`, which reads the array out of the current GRT's
WSA, so from a CGI the token scan found nothing, the CRED stayed in httpd's real
store, and the token kept resolving after a "successful" logout. The established fix
pattern is to resolve the pointer once in httpd's own GRT at init time and cache it
in the shared HTTPD control block (`httpd->credarr = cred_array()` at `cred_init()`),
then pass it explicitly to an array-explicit variant of the function — the same
GRT-independent pattern `http_get_password()` uses for the blowfish key. CGIs reach
the HTTPD and HTTPC control blocks through `grt->grtapp1` / `grt->grtapp2`, which
`cgistart.c` populates.

**Must contain**

- The loaded module and httpd do not share the writable static area despite
  sharing the address space **and the TCB**: the module's read of the static comes
  back empty while httpd's own read of the same static is populated. This follows
  from the module being a separately linked load module built with a full
  startfile (`crt0`/`crt1`), which calls `__grtset()` and establishes a fresh
  CLIBGRT — it is **not** a link-line mistake, and re-linking the module against
  httpd's objects does not merge the two static areas.
- Therefore httpd-core file-scope statics read back empty/NULL when the core
  function is invoked from the CGI.
- The fix is to resolve the pointer while running in httpd's own GRT and then pass
  it explicitly into the call made from the CGI, rather than to change the static's
  linkage. (The specific implementation — caching it in the shared HTTPD control
  block at `cred_init()` time — is sufficient but not required; any answer with the
  right shape passes, and the disqualifiers below catch the wrong shapes.)
- The CGI obtains HTTPD/HTTPC via `grt->grtapp1` / `grt->grtapp2`.

G-3 was resolved on 2026-08-01 (see the *Gaps* section), so the GRT mechanism is
now part of `M1` above rather than being excluded from grading.

**Disqualifying errors**

- Asserting that because the CGI runs in httpd's address space the statics are
  shared, and looking for the bug elsewhere.
- Proposing to fix it by making the static a non-static global / `extern`, by moving
  it into a GETMAIN'd address-space-wide singleton, by re-linking the CGI into
  httpd, or by removing httpd's objects from the module's link line so the symbol
  "resolves to one copy".
- Attributing the empty read to storage-key protection, subpool ownership, or
  reentrancy (RENT) alone, without identifying that the two modules hold separate
  copies of the static.
- Claiming CGI modules cannot call back into the server at all.

**Evidence**

- Commit `4a97226` (httpd, 2026-07-06) — "Fix http_logout() no-op from a CGI: reach
  httpd's store, not the CGI's GRT". The message states the mechanism ("reads the
  credential array out of the current GRT's WSA. A CGI reached through the HTTPX
  vector runs under its own GRT, where that slot is empty"), the fix
  (`httpd->credarr = cred_array()` at `cred_init()` time, plus
  `credtok_logout_arr(array, token)`), the precedent (`http_get_password()` /
  blowfish key), and that it is the "Same GRT/WSA class as #109 (userid) and #111
  (password)". Fixes #113.
- `httpd/CLAUDE.md:143-149` — "CGI modules are loaded via MVS LINK SVC
  (`__linkds`). The HTTPD/HTTPC pointers are passed through the GRT … and discovered
  by the CGI's custom `__start` (cgistart.c / cgxstart.c)", with the
  `grt->grtapp1` / `grt->grtapp2` idiom.
- `httpd/src/cgistart.c:81, 86, 98` — `grt->grtapp1 = httpd;`,
  `grt->grtapp2 = httpc;`.
- `httpd/src/cgihttpd.c:19-20`, `httpd/src/cgihttpc.c:18-19` — the eyecatcher checks
  (`HTTPD_EYE` / `HTTPC_EYE`) before trusting the GRT slots.
- `libc370/doc/startup.md:38, 46` — CLIBGRT is anchored at `crt->crtgrt` and
  `ppa->ppagrt`; `__grtget` is simply `crt->crtgrt`.
- `libc370/asm/@@crt1.asm:77-78` — `L R15,=V(@@GRTSET)` / `BALR R14,R15`,
  commented "Anchor a CLIBGRT area as CRTGRT". Same at `@@crt0.asm:74-75`.
  `@@crtm.asm` contains neither call — it only does `@@CRTGET` (lines 54, 106).
- `libc370/src/clib/@@grtset.c` — `__grtset()` `calloc`s a fresh CLIBGRT and
  assigns `crt->crtgrt = grt; ppa->ppagrt = grt;` **unconditionally**, with no
  check for an existing one.
- `httpd/project.toml:44-68` — every loaded module (`HTTPJES2`, `HTTPDM`,
  `HTTPDMTT`, `HTTPDSL`, `HTTPDSRV`) is `startup = "crt1"` with
  `src/cgistart.c` as its root.
- `httpd/src/httplink.c:38` — `__linkds(pgm, dcb, plist, &prc)`, issued from the
  worker thread, so the module runs on the worker's own TCB. No ATTACH.

**Likely failure without KB**

The model will anchor on "same address space ⇒ same storage" and conclude the static
must be shared, then look for the bug in the vector table, in initialization order,
or in a caching/lifetime problem. If it does reach for a storage explanation it will
most likely name storage keys or subpool ownership, not a per-module writable static
area. The specific wrong *fix* to expect is "drop the `static` qualifier / export the
symbol so both modules resolve to one copy" — which cannot work here, because the
separately linked CGI gets its own copy of the writable static regardless of linkage,
and which a reviewer would plausibly accept as reasonable C advice.

---

### Q-07 — Choosing a libc370 startfile for a LINKed C module

**Category:** project-internals
**Depth:** single-lookup
**Platform:** mvs38j

**Question**

I'm writing a C module that gets LINKed from another C program and runs on the same
TCB. Which libc370 startfile do I link it with, and what goes wrong if I pick the
wrong one?

**Expected answer**

`crtm.o`. libc370 has three startfiles — `crt0.o`, `crt1.o`, `crtm.o` — which all
define the **same** entry point `@@CRT0` and are mutually exclusive: they live
outside `libc.a` so the linker pulls exactly one into any given program, like
glibc's `crt1.o`. `crt0` and `crt1` build a full runtime (PPA, CLIBCRT, CLIBGRT,
stack); `crtm` builds none and reuses the caller's runtime on the same TCB. The only
functional difference between `crt0` and `crt1` is the `IDENTIFY EPLOC=CTHREAD` at
startup — use `crt0` if the program creates threads (`cthread_create*`), `crt1`
otherwise, which is the common case. Using `crtm` as a top-level startfile abends:
without a prior `crt0`/`crt1` on the same TCB, its unchecked `@@CRTGET` dereferences
a NULL CLIBCRT.

**Must contain**

- `crtm` (`crtm.o`) is the correct startfile for a module entered inside an
  already-running C runtime on the same TCB (LINK / XCTL / LOAD+BALR from a C
  program).
- All three define the same entry point `@@CRT0` and are mutually exclusive
  startfiles — exactly one is linked per program.
- `crt0` versus `crt1` differ only by `IDENTIFY EPLOC=CTHREAD`, i.e. thread support;
  `crt1` is the default for a non-threaded standalone program.
- `crtm` used as a top-level startfile fails because `@@CRTGET` returns NULL and is
  dereferenced unchecked.

**Disqualifying errors**

- Recommending `crt0` or `crt1` for the LINKed module on the grounds that "the
  runtime handles nesting".
- Describing the startfiles as additive — e.g. linking `crtm` alongside `crt1`, or
  treating them as ordinary library members pulled in by autocall.
- Stating that `crt0` and `crt1` differ in stack size, storage subpool, or
  reentrancy rather than in the `IDENTIFY`.
- Claiming the module needs no startfile at all because it inherits the caller's.

**Evidence**

- `libc370/doc/startup.md:5-20` — the TL;DR: all three define the same entry point
  `@@CRT0`, are "**mutually exclusive** startfiles — exactly like glibc's `crt1.o`",
  built as separate objects outside `libc.a`; the table row for `crtm.o` reads "A C
  module entered **inside an already-running C runtime on the same TCB**
  (LINK/XCTL/LOAD+BALR from a C program) … no — it **reuses** the caller's runtime".
- `libc370/doc/startup.md:22-27` — rules of thumb: "crt0 vs crt1 = *do I need
  threads?* — the only real difference is the `IDENTIFY EPLOC=CTHREAD` at startup";
  "**Never use `crtm` as the top-level startfile.** Without a prior crt0/crt1 on the
  same TCB its unchecked `@@CRTGET` dereferences a NULL CLIBCRT and abends."
- `libc370/doc/startup.md:83-86` — crt0 step 12, `IDENTIFY EPLOC=CTHREAD`, required
  so `ATTACH EP=CTHREAD,DPMOD=-1` in `@@ctcrtx.c` resolves.
- `libc370/doc/startup.md:99-101` — `@@crt1.asm` is a line-for-line copy of crt0
  with the `IDENTIFY EPLOC=CTHREAD` commented out.
- `libc370/doc/startup.md:34-38` — the three runtime anchors: CLIBPPA per program
  invocation, CLIBCRT per TCB/thread, CLIBGRT per process/address space.
- **Practice note (added 2026-08-01).** No module in the ecosystem is actually
  built with `crtm`. Across every `project.toml` under `~/repos/mvs` the counts
  are **120 × `startup = "crt1"`, 1 × `crt0`, 0 × `crtm`**, although `crtm.o` is
  built and shipped (`libc370/build/sdk/crtm.o`). httpd's own loaded modules use
  `crt1` deliberately — "`startup=crt1` for the threading runtime (`@@CRT1`)"
  (`httprexx/project.toml:16-17`, `httplua/project.toml:20`) — because `crtm`
  carries no CTHREAD entry (`@@crt1.asm:166` has it, `@@crtm.asm` does not).
  **The graded fact is the documented rule in `startup.md`, not current
  practice.** The two diverge; the divergence is itself KB material and should be
  written up before the with-KB arm, so a KB document does not end up
  contradicting the repos.

**Likely failure without KB**

The model will map the question onto the Unix model it knows and answer `crt0.o` —
the name it recognizes as "the" C startup object — or say that on MVS the C runtime
is initialized once per address space so the LINKed module needs no special
startfile. Either way it will miss that this ecosystem ships three mutually
exclusive startfiles behind one shared entry point and that the nested case has a
dedicated one. If it does guess `crtm`, expect it to justify the choice as "the
minimal runtime" and to describe `crt0` vs `crt1` as a size or optimization
difference rather than the `IDENTIFY`.

---

### Q-08 — How ufsd learns which user a session belongs to

**Category:** project-internals
**Depth:** multi-source
**Platform:** mvs38j

**Question**

When mvsMF opens a UFS session through the ufsd SSI router, how does ufsd establish
which RACF user the request belongs to? The router runs in the caller's address
space, so can't it just pick up the caller's ACEE?

**Expected answer**

No — that is specifically forbidden, and the client supplies the identity instead.
`UFSREQ_SESS_OPEN` (0x0010) creates the session with owner and group **empty**; the
client then issues a separate `UFSREQ_SETUSER` (0x0012) request to set them. On the
client side that is `ufs_setuser()` in libufs, which mvsMF calls from `ussapi.c`.
The router must not call `racf_get_acee()` during SESS_OPEN, because
`racf_get_acee()` reads ASXBSENV (ASXB + X'C8'), which is **per address space** and
shared by all worker threads. Concurrent `racf_login` / `racf_logout` from parallel
HTTP requests can therefore hand back a stale pointer to an already-freed ACEE,
giving S0C4 inside `ufsdssir`. The client is the right source because it already
knows the authenticated user.

**Must contain**

- Identity is supplied by the client in a separate `UFSREQ_SETUSER` request *after*
  `SESS_OPEN`, not derived inside the router.
- The SSI router must **not** call `racf_get_acee()` during SESS_OPEN.
- The reason is that ASXBSENV is per-address-space and shared across worker threads,
  so a concurrent login/logout leaves a stale or freed ACEE pointer.
- The failure mode that motivated it is S0C4 inside the router.

**Disqualifying errors**

- Answering that the router picks up the caller's ACEE (via ASXBSENV or TCBSENV) at
  SESS_OPEN, and that this is the intended design.
- Claiming the SESS_OPEN request itself carries the userid.
- Claiming ufsd performs its own RACINIT/RACHECK to establish the session identity.
- Describing ASXBSENV as per-task / per-TCB.

**Evidence**

- Commit `0b63fda` (ufsd, 2026-03-20) — "fix: remove racf_get_acee() from SESS_OPEN
  in SSI router": "ASXBSENV is per-address-space and shared across all worker
  threads. Concurrent racf_login/racf_logout from parallel HTTP requests creates a
  race condition where racf_get_acee() returns a stale pointer, causing S0C4 in
  ufsdssir when accessing the freed ACEE. Session owner/group are now set exclusively
  via UFSREQ_SETUSER after SESS_OPEN. The client (mvsMF) already knows the
  authenticated user." Fixes #10.
- `ufsd/src/ufsd#ses.c:217` — "Owner/group start empty — set by SETUSER after
  SESS_OPEN".
- `ufsd/src/ufsd#ses.c:276-285` — `ufsd_sess_setuser(UFSD_ANCHOR *anchor,
  UFSREQ *req)`.
- `ufsd/include/ufsd.h:329, 331` — `UFSREQ_SESS_OPEN 0x0010`,
  `UFSREQ_SETUSER 0x0012`.
- `ufsd/client/libufs.c:287-296` — `ufs_setuser(UFS *ufs, const char *userid,
  const char *group)` builds an SSOB with `ufsssob.func = UFSREQ_SETUSER`.
- `mvsmf/src/ussapi.c:115` — `ufs_setuser(ufs, userid, group);` — the mvsMF side of
  the contract.
- `libc370/src/racf/racgacee.c:13` and `libc370/src/racf/racsacee.c:15` —
  `ACEE **asxbsenv = (ACEE **) &asxb[0xC8/4];` — get and set both go through
  ASXBSENV at ASXB + X'C8'.

**Likely failure without KB**

The model will answer with the textbook MVS identity rule: the ACEE is located via
TCBSENV if non-zero, otherwise ASXBSENV, and since the SSI router runs in the
caller's address space and under the caller's task it should simply pick up the
active ACEE there. That is a fluent, well-formed, and specifically wrong answer — it
is exactly the design that was removed, and its failure mode (a stale ACEE pointer
under concurrency) is invisible from the MVS rule alone. Expect it to describe the
identity as flowing implicitly with the SSI call rather than as an explicit second
request the client must issue, and to be unaware that `UFSREQ_SETUSER` exists as a
distinct function code.

---

### Q-09 — A crash that only happens when the interpreter is called from C

**Category:** debugging
**Depth:** multi-source
**Platform:** mvs38j

**Question**

We had a crash that only ever showed up when our REXX interpreter's termination
routine was invoked from a C program — never from the pure-assembler test cases. The
abend code rotated between S0C1, S0C2, S0C4 and S0C6 depending on timing. In every
dump R13 and R14 looked completely sane, but R0 through R12 were full of what looked
like system control blocks. What causes that?

**Expected answer**

An assembler syntax pitfall in the caller-side shim — not the interpreter, the C
runtime, or the LINK/BALR machinery. `LM` and `STM` are RS-format: the operand is
`D2(B2)`. Written RX-style with an empty index — `LM R0,R12,20(,R13)` — as370
silently assembled it with **base register 0**: `98 0C 0014` instead of
`98 0C D014`. So the shim's epilog restored R0–R12 from absolute low storage
0x14–0x48 (the PSA: CVT pointer, old PSWs, CSWs) rather than from the caller's save
area. The adjacent `L R14,12(,R13)` is RX-format, which legitimately has an index
field, so it assembled correctly — that is precisely why R13 and R14 were always
intact. The "garbage" in R0–R12 was literally our own task's old PSWs and nucleus
addresses, which vary with interrupt timing, hence the wandering branch targets and
rotating abend codes. The fix is the `D(B)` spelling in the shims; as370 was
subsequently hardened to reject `D(,B)` on RS/SI/S operands with a severity-12
diagnostic, matching IFOX00's ERR216.

**Must contain**

- The root cause is the RX-style empty-index form `D(,B)` written on an RS-format
  instruction (`LM` / `STM`).
- as370 assembled it with base register 0 — an absolute low-storage reference — with
  no diagnostic; `980C0014` instead of `980CD014`.
- The registers that looked like control blocks were PSA low storage, and R13/R14
  survived because the adjacent instruction was RX-format and assembled correctly.
- The fix is the `D(B)` spelling; as370 now rejects `D(,B)` on RS/SI/S operands.

**Disqualifying errors**

- Concluding that the C caller's save area / DSA was being corrupted or overwritten
  (explicitly refuted by word-by-word instrumentation).
- Blaming the interpreter's termination path, the LINK-versus-BALR asymmetry, or a
  subpool-0 collision.
- Stating that `20(,R13)` and `20(R13)` are equivalent spellings, or that the
  assembler would have diagnosed the difference at the time.
- Attributing the rotating abend codes to a race or to uninitialized storage rather
  than to timing-dependent contents of low core.

**Evidence**

- `rexx370/docs/irxterm-c-host-crash.md`, "TL;DR — root cause" — the broken versus
  correct `LM`, the two encodings (`98 0C 0014` versus `98 0C D014`), the PSA
  0x14–0x48 explanation, and why R13/R14 stayed valid (`L R14,12(,R13)` is
  RX-format).
- `rexx370/docs/irxterm-c-host-crash.md`, "Why every earlier hypothesis mis-fit" —
  the C-DSA-corruption theory refuted by word-by-word diffs of the caller frame, the
  shim workarea, a 28 KB module window and a 2M-iteration SVC-free spin probe:
  "Storage was never corrupted; the broken LM simply never read it."
- `rexx370/docs/irxterm-c-host-crash.md`, "Verification" — negative proof:
  re-introducing the `D(,B)` spelling reproduces the crash signature (JOB 890); the
  fixed spelling with the identical LINKLIB is green (JOB 899).
- Commit `a04a945` (rexx370, 2026-07-02) — "fix: IRXTERM C-host crash root-caused
  (as370 RS-format D(,B) shim bug) + istso EXTRACT S328 (#206)".
- Commit `15927eb` (cc370, 2026-07-15) — "fix(as370): reject RS/SI/S storage operand
  with an index/length subscript (#12) (#16)". The message records that `resolve()`
  produced two subscripts (`sub[0]=0`, `sub[1]=base`) and the encoder took the first
  as the base; that IFOX00 issues ERR216 ILLEGAL OPERAND FORMAT at severity 12 for
  this; and that it "was the root cause of the rexx370/httprexx IRXTERM-from-C
  crash".
- `cc370/as370/src/as370.c:1256-1257, 1511, 2200-2205` — the `note_badfmt`
  diagnostic on `ns >= 2` in the F_RS / F_SI / F_S encoders, and the error text
  "Illegal operand format (index/length not allowed on RS/SI/S operand)".

**Likely failure without KB**

The two attractive wrong answers are both about storage. First: "the C caller's
stack frame / DSA is being overwritten" — irresistible because corrupted registers
on return normally *do* mean a clobbered save area, and rotating abend codes
normally *do* mean a race. Second: "the assembler shim doesn't follow OS linkage
conventions / R13 chaining". Expect proposals to add storage-overlay
instrumentation, move the workarea to a private subpool, or switch LINK to BALR (or
the reverse). A model is very unlikely to volunteer that `20(,R13)` and `20(R13)`
assemble differently, since in RX context the empty index is a normal idiom and
reads as a harmless stylistic variant.

---

### Q-10 — A load module that runs, then takes S0C1 past 16 KB

**Category:** debugging
**Depth:** multi-source
**Platform:** mvs38j

**Question**

A load module built by our own linker installs and starts executing, then takes S0C1
at a roughly fixed point a little past 16 KB in. AMBLIST and the control-record CCW
counts both say the module is the full size we expect, and the load point and extent
are correct. The cut lands inside a single text record in one reproduction and inside
the second text record in another. Where's the problem?

**Expected answer**

In the linker's own emission — not in program fetch, and not in DASD geometry. The
on-disk member really is truncated; the CCW counts were an inference and nobody had
scanned the member bytes. `struct obj` in `ld370.c` held each object's text in a
fixed 16384-byte array, and the OBJ TXT-card reader dropped every TXT card that
would not fit, silently. Everything past the last 56-byte TXT-card boundary at or
below 16384 stayed zeros — 16352 or 16376 depending on the layout — and the first
zero halfword executed there gives S0C1. The fix was to grow `o->text` with
`realloc` (tracked by `textcap`), zero-filling gaps and erroring on OOM instead of
dropping. Two neighbours in the same class: `rld[512]` / `ld[64]` were fixed arrays
with no bounds check, so an object with more than 512 RLD items overflowed `rld[]`
into `ld[]` and exported LD symbols silently vanished; and separately, an oversized
RLD *record* causes S106 reason 0E, because program fetch reads each RLD record into
a 256-byte buffer, so IEWL caps RLD data at 236 bytes per record.

**Must contain**

- The truncation is in the linker's object reader / emitter — the emitted member is
  already short — not in IEWFETCH, not a track-crossing or geometry limit, and not
  the multi-text-record split.
- The cut is at a fixed cumulative text offset, independent of the text-record
  boundaries, and lands on **the last 56-byte TXT card at or below 16384** — not
  at 16384 itself. Naming the ~16 KB magnitude alone does **not** satisfy this
  bullet: the card granularity is required, because it is what explains the
  16352 / 16376 pair. (Tightened 2026-08-01. "A hard stop at 2^14 is a buffer in
  your own code" is pattern-matching on a power of two, which the *Likely failure*
  note below already calls a magnet; it is not knowledge of `ld370.c`.)
- The dropped region is zeros, and the first zero halfword executed is what gives
  S0C1.

**Disqualifying errors**

- Attributing it to IEWFETCH / program fetch, to a track or extent boundary, to the
  block size, or to the module being split into multiple text records.
- Claiming the on-disk member is complete and the loader is at fault.
- Claiming the S0C1 is caused by a bad entry point, a missing relocation, or an
  AMODE/RMODE problem.
- Explaining the 16352-versus-16376 difference as noise or as a rounding artefact
  rather than as the layout-dependent position of the last surviving TXT card.

**Evidence**

- `cc370/docs/multitext-fetch-truncation.md` — the RESOLVED banner: "it was never
  FETCH, never placement"; the fixed 16384-byte array and the
  `if (addr + cnt <= sizeof o->text)` guard that "silently dropped every TXT card
  past 16384 B"; the two reproductions (292 × 56 = 16352; 12288 + 73 × 56 = 16376);
  and the post-mortem — "nobody scanned the actual member bytes … the member `ld370`
  *emits* is already truncated. The IDR-82 and off33 directory diffs were red
  herrings."
- `cc370/docs/multitext-fetch-truncation.md` §1 — the symptom table: EPA `0x095590`
  and extent `0x4A70` both correct; the second run's cut falls *inside* a single text
  record, which rules out the multi-record theory.
- `cc370/ld370/src/ld370.c:201-210` — the comment recording both bugs: text "grown on
  demand (was a fixed 16384-byte buffer that SILENTLY dropped text past 16K -> any
  module > 16K truncated to zeros, S0C1 at run time)", and the `rld[512]` / `ld[64]`
  overflow ("exported LD symbols silently vanished -> 'unresolved' at a later link.
  Same class as the text-buffer bug above").
- `cc370/ld370/src/ld370.c:285-292` — the `realloc` growth with `textcap` and the
  `memset` zero-fill of gaps.
- `cc370/ld370/src/ld370.c:1898-1908` — "IEWL caps each RLD record at 236 so the
  whole record (16-byte header + data) fits program fetch's 256-byte RLD buffer
  (IEWFETCH FTRBUF); one oversized RLD record makes fetch read past the buffer and
  relocate garbage addresses -> S106 reason 0E", with `const long RLDMAX = 236;`.
- Commit `de39a60` (cc370, 2026-06-21) — "fix(ld): emit complete object text for
  multi-text load modules".
- Commit `47a6cc7` (cc370, 2026-06-21) — "fix(ld): split RLD records to <= 236 bytes
  so program fetch can relocate them".
- Commit `6e4dbef` (cc370, 2026-06-24) — "fix(ld370): grow rld/ld on demand (>512 RLD
  items clobbered LD symbols)".

**Likely failure without KB**

The 16 KB figure is a magnet. Expect a confident answer built around a buffer or
block boundary *in the loader*: program fetch's channel program, a 16384-byte
BLKSIZE limit, a track boundary on 3350, or note-list / extent handling for
multi-extent modules — with the further claim that the module image on disk is fine
because AMBLIST says so. That is the exact inference the investigation records as its
own wrong turn, and it is durable: a model will keep reasoning about the reader as
long as it accepts the premise that the member is complete. Expect suggestions to
reduce the block size, relink with a single text record, or check RMODE — none of
which touch the actual defect, which is a `sizeof`-guarded `memcpy` in the linker's
TXT-card reader.

---

## Gaps

Questions worth asking that this benchmark cannot ask, because the answer is not
written down anywhere in the repos. These are the highest-value candidates for the
first knowledge-base documents.

**G-1 — Why does UFSD still need AC(1) if libc370 self-authorizes via SVC 244?**
Commit `bf859e0` restores `setcode AC(1)` on the UFSD load module ("UFSD is an
APF-authorized STC; the v2 migration dropped the v1 'setcode AC(1)'"), while
`nsf370/m5-stage0a-ssi-probe.md:35-40` states that a task self-authorizes at runtime
through `clib_apf_setup` → `__autask()` → SVC 244 "independent of its library", with
UFSD's own STEPLIB explicitly not in IEAAPF00. Both cannot be the whole story.
Missing: which paths actually depend on AC(1), and whether it covers something the
SVC-244 path cannot (the STC entry itself?) or is vestigial. Nothing in the repos
states the rule.

**G-2 — What is SVC 244 on our target systems, and what exactly does it grant?**
libc370 calls it (`@@autask.c`, `@@uatask.c`) and the ecosystem depends on it
completely, but no repo records where it comes from (TK4-, TK5, MVS/CE, or an
mvslovers-installed SVC), what its parameter contract is beyond R0/R1, which target
systems ship it, or what happens on one that does not. Every "will this run on TK5 /
on a stock 3.8j?" question depends on this and none of it is written down.

**G-3 — Is the GRT per address space or per linked module? — RESOLVED 2026-08-01.**
Both repo statements are correct; the documentation is incomplete rather than wrong.
`__CRTSET()` (`libc370/src/clib/@@crtset.c`) inherits the **originating** TCB's GRT
via `TCBOTC` at `tcb[0x84/4]`, and the CTHREAD entry at `@@crt1.asm:166` calls only
`@@CRTSET`, never `@@GRTSET`. An ATTACHed worker therefore inherits httpd's GRT, which
is exactly the scope `startup.md:38` describes. The case the document does not cover is
the **LINK** case: a module fetched by LINK SVC on the same TCB with a full startfile
runs `@@GRTSET` (`@@crt1.asm:77-78`), which `calloc`s a fresh CLIBGRT and overwrites
`crt->crtgrt` unconditionally. `crtm` is precisely the startfile that does not do this.
`cgistart.c` re-seeds only `grtapp1`/`grtapp2` into the fresh GRT (lines 81, 86, 98);
everything else httpd holds in its own GRT stays invisible from the module — which is
what #109, #111 and #113 each are. Now graded as part of Q-06's `M1`. The full trace,
including a derived-but-unverified consequence about CRT ordering that still wants a
live check, is in `benchmark/results/2026-07-31-baseline/` follow-up notes.

**G-3a — Why is nothing built with `crtm`?** Falls out of resolving G-3: `startup.md`
documents `crtm` as the correct startfile for a module entered inside a running C
runtime on the same TCB, and no module in the ecosystem uses it (120 × `crt1`, 1 ×
`crt0`, 0 × `crtm`). For httpd's modules the `crt1` choice is deliberate and recorded
(threading runtime), but whether the rule in `startup.md` should be restated, scoped,
or retired is not written down anywhere. Un-askable as a graded question until it is.

**G-4 — Which reply-wait and drain timings are contractual, and which are incidental?**
`ufsd/src/ufsd#ssi.c:49,54` fix `UFSD_WAIT_INTERVAL` at 500 hundredths and
`UFSD_TIMEOUT_CODE` at X'0FFFF', and `ufsd/src/ufsdclnp.c:39` waits
`2 * UFSD_WAIT_INTERVAL`. Whether these are tuned values, safety margins derived from
something measurable, or arbitrary, is not recorded — nor whether a client
implementing the protocol independently (nsf370 is about to) must match them. That
makes it un-askable as a graded question today, and it is exactly the kind of
cross-repo contract the KB exists to hold.

**G-5 — Why is EBCDIC 0x25 → ASCII 0x85 rather than 0x0A in the non-LEGACY tables?**
`httpd/src/httpxlat.c:29-38` documents the `atoe` override and marks the `etoa` side
"EBCDIC LF (0x25) -> ASCII NEL (0x85)  <- unchanged", but never says whether leaving
it unchanged was a decision (so that data originating outside the ecosystem is not
silently normalized) or simply the pure-code-page value nobody revisited. LEGACY maps
both 0x15 and 0x25 to 0x0A, so the ecosystem has shipped both behaviours. A question
about which is correct for inbound data cannot be graded until somebody records the
intent.

---

## Notes on construction

- **Coverage:** ten questions written, **9 scored and 1 blocked** (Q-03). By
  category: 3 mvs-domain (Q-01, Q-02, Q-03 — of which Q-03 is the blocked one, so
  2 scored), 2 encoding (Q-04, Q-05), 3 project-internals (Q-06, Q-07, Q-08),
  2 debugging (Q-09, Q-10).
- **Retrieval depth:** seven questions are multi-source (Q-01, Q-02, Q-03, Q-06,
  Q-08, Q-09, Q-10 — six of them scored), each requiring facts combined from at
  least two files, or from a file plus a commit message. Three are single-lookup
  (Q-04, Q-05, Q-07). The scored set therefore still clears the floor of three
  multi-source questions with room to spare.
- **Independence:** no question's *Expected answer* states a fact that is graded in
  another question. Q-01, Q-02 and Q-08 all touch the ufsd SSI router but grade
  disjoint facts (cross-AS POST/WAIT mechanics; the double-start message; the session
  identity contract). Q-04 and Q-05 both read `httpxlat.c` but grade disjoint table
  regions (newline versus brackets and pipe).
- **Stability:** every graded fact is a recorded root cause, a committed source
  constant, or a documented design rule. None depends on a version number, an open
  issue, or current task status. Q-09 grades a historical root cause; the later as370
  hardening (`15927eb`) is part of the expected answer so the question stays correct
  as the toolchain evolves.
- **Not included, deliberately:** questions answerable from a README's first line or
  by a single symbol lookup (e.g. "what does mbt's `make deploy` do", "what is
  `UFSREQ_SETUSER`'s numeric value in isolation"), and questions whose only source was
  a `status:` line or an open issue.
