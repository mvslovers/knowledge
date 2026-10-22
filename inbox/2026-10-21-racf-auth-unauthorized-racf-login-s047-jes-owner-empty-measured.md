# racf_auth without APF, racf_login without APF, JES owner field, `.*` vs `*` in JESSPOOL (RAKF 2.0.0, measured)

Measured 2026-10-21 on a throwaway MVS/CE container (not a stand), RAKF 2.0.0 installed as in the MVS-332 note
(`2026-10-21-rakf-200-jesspool-racf-auth-measured-vs-old-rakf.md`), Paperclip issue MVS-343. Probes are small libc370 programs
(`<mvs/racf.h>`, `<mvs/jes2.h>`), run as batch under a plain user (group USER) and as started tasks.

## racf_auth works from a non-APF library, racf_login does not

- Load library not on the APF list (`IBMUSER.*`), module linked AC(0) **and** AC(1) (an AC(1) module from a non-APF library simply
  runs unauthorized, no S047 at load): `racf_get_acee()` returns the address space's own ACEE and
  `racf_auth(acee, "JESSPOOL", ...)` returns exactly the same RC triples (READ/UPDATE/ALTER) as the authorized AC(1) control run from
  SYS2.LINKLIB: empty class 4/4/4; profile NONE 8/8/8; READ 0/8/8; UPDATE 0/0/8; ALTER 0/0/0; user-specific READ with UACC NONE 0/8/8
  (for that user); undefined class `NOSUCHCL` 8/8/8 with `RAKF0012 UNDEFINED CLASS NOSUCHCL`. No false 0 for "no profile" or NONE.
- Same under a started task whose RAKF user is in group `*USER` (no `FACILITY SVC244`, the 2.0.0 upgrade case): own ACEE user JSPROBS group
  USER, `FACILITY SVC244` = 8, JESSPOOL values as above. Contrast: STC user in `STCGROUP`: `FACILITY SVC244` = 0.
- `racf_login(user, NULL, NULL, &rc)` (RACINIT) from the same unauthorized program **abends S047** (MODESET SVC 107, INTC 006B,
  inside `racf_login`), it does not return an error code. So no ACEE for another user exists in that state.
- Real container FTPD 1.2.0 (not the 1.3.0 JES-policy build) in that state (`APF SETUP FAILED RC=4`): connect and `USER` are answered
  (`220`, `331`), `PASS` gets **no reply at all** for 100 s (client timeout); afterwards `PWD` gives `530 Not logged in`. Login never
  reaches `230`. A hang, not a clean `530`.

## JES2 queue entries: owner field of `jesjob()` (AC(1), from SYS2.LINKLIB)

`JESJOB.owner` is `unsigned char[9]`, NUL-terminated, not blank-padded (bytes after the name are X'00').
- Batch job with USER on the job card: owner = that user (e.g. `IBMUSER`, strlen 7).
- Batch job submitted through the reader **without USER/PASSWORD**: owner = **empty** (strlen 0, all nine bytes X'00'). Reproducible.
- Every started task (HTTPD, FTPD, UFSD, NET, INIT, TSO, RAKFPROF, ...), also those started under their own RAKF user: owner =
  `SYSTEM` (strlen 6). JES2 and MSTR themselves are not in the queue (77 entries listed, none of them JES2/MSTR).

## JESSPOOL: `.*` NONE does not shield against `*` READ

Entity `.JOBA.JOB00001` (empty owner), user MVSCE02, own ACEE:
| profiles | `.JOBA.JOB00001` | `ZQOTHER.JOBA.JOB00001` |
|---|---|---|
| `.*` NONE and `*` READ | R0 U8 A8 (READ wins) | R0 U8 A8 |
| `.*` NONE only | R8 U8 A8 | R4 U4 A4 |
| `*` READ only | R0 U8 A8 | R0 U8 A8 |
In EBCDIC `.` (X'4B') sorts before `*` (X'5C'), last matching profile wins, so `*` READ overrides `.*` NONE.

Result files and job outputs are in the Paperclip scratch directory of MVS-343 (not kept). Container result, not a stand result.
