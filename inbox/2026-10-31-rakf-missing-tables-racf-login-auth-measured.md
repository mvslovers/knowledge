# RAKF: behaviour of `racf_login` / `racf_auth` when the RAKF tables are missing or invalid

Draft for `knowledge/inbox/`. Measured 2026-10-30 in throwaway containers only (old RAKF 1.2.x as shipped in the TK5 image; RAKF 2.0.0 as shipped in the MVS/CE image). Measured with a small probe program that calls `racf_login()`, `racf_auth()` and `racf_get_acee()` from libc370.

## Summary

- Old RAKF (1.2.x) that comes up **without valid tables** answers "allowed" to everything: `racf_login` returns RC 0 for any userid and any password, and the returned ACEE belongs to `STC`/`STCGROUP`, not to the requested user. `racf_auth` returns RC 0 for every class and entity.
- Because the login itself already succeeds, checking only the `racf_auth` return codes cannot detect this state. The distinguishing signs are on the login side (see below).
- RAKF 2.0.0 does not come up at all without its tables: JES2 does not start. In that case there is nothing to query.
- The "open" state is created by an IPL (or a RAKF restart) with missing/invalid tables. A live reload with `S RAKF` keeps the tables already in storage.

## Old RAKF 1.2.x, tables missing or invalid

"Tables" are the two members `PROFILES` (resource profiles) and `USERS` (user/password table) in `SYS1.SECURE.CNTL`. The state occurs when the tables are missing or contain no valid entries. `RAKF0001` is reported for the user table even if only the resource table is invalid.

Console messages at startup and during use:

```
RAKF0001 USERID TABLE INVALID OR MISSING
RAKF0002 STC ACCESS ALLOWED: USER: <name>
RAKF0003 RESOURCE TABLE INVALID/MISSING: ALLOWED:STC
RAKF0009 STC ,<job> ,<class>,<entity>        (once per authorisation check)
```

Probe results in this state (`racf_rc` = return code of `racf_login`; three RCs are for READ / UPDATE / ALTER):

```
STC ACEE (racf_get_acee): user=STC group=STCGROUP
LOGIN <valid user>, no password        -> racf_rc=0   ACEE user=STC group=STCGROUP
LOGIN <unknown user>, any password     -> racf_rc=0   ACEE user=STC
LOGIN <valid user>, wrong password     -> racf_rc=0   ACEE user=STC
CHECK FACILITY  <entity>               -> 0 / 0 / 0
CHECK DATASET   <dsn>                  -> 0 / 0 / 0
CHECK JESSPOOL  <entity>               -> 0 / 0 / 0
CHECK <undefined class> <entity>       -> 0 / 0 / 0
```

Healthy comparison with the tables in place (same probe):

```
LOGIN <valid user>, no password        -> racf_rc=0   ACEE user = requested user, own group
LOGIN <unknown user>                   -> racf_rc=28  ACEE NULL
LOGIN <valid user>, wrong password     -> racf_rc=8   ACEE NULL
```

Healthy `racf_auth` result for an **unknown class** (tables loaded, class not defined): RC **4** (4 / 4 / 4 for READ / UPDATE / ALTER) on old RAKF. A class with no matching profile (here JESSPOOL) also returns 4 / 4 / 4.

Reload versus restart: if a table member cannot be found, `S RAKF` on a running system does not change anything. RAKF answers `RAKF005I RAKF is already active`, reports `IEC141I ... RAKFPROF` (member not found), and keeps the tables from storage: login (RC 8 for a wrong password) and checks behave as before. Only an IPL, or a restart that actually reloads the tables, produces the open state. Restoring the member and reloading returns the system to normal operation; long-running servers that cache the session identity (for example HTTPD) need a restart afterwards.

## RAKF 2.0.0, tables missing or invalid

The system does not come up. With either table, or both, missing or invalid, the console shows:

```
IEC141I 013-18 ... RAKFPROF / RAKFUSER      (member not found)
RAKF0001 USERID TABLE INVALID OR MISSING
RAKF0002 STC ACCESS ALLOWED: USER: ~ ~
IEA911E COMPLETE DUMP ON SYS1.DUMP00 FOR ASID(0002)
IEF174I SYSTEM ERROR BEFORE JOB INITIATION
```

JES2 does not start, so no server task that depends on it starts either. Control run with intact tables: JES2 and the server tasks start normally. The abend code of the JES2 failure was not analysed; the link to the missing tables rests on the variants with only one table affected and on the control run.

Healthy `racf_auth` result for an **unknown class** on RAKF 2.0.0 (tables loaded): RC **8** (8 / 8 / 8), plus the console message `RAKF0012 UNDEFINED CLASS <name>`. A class that is defined but has no matching profile returns RC 4. Login behaves as in the healthy case above (unknown user RC 28, wrong password RC 8).

## Healthy return codes at a glance

| Situation | `racf_login` | `racf_auth` |
|---|---|---|
| Old RAKF, tables ok, unknown user / wrong password | 28 / 8, ACEE NULL | n/a |
| Old RAKF, tables ok, unknown class | n/a | 4 |
| RAKF 2.0.0, tables ok, unknown class | n/a | 8 (+ `RAKF0012`) |
| Old RAKF, tables missing or invalid | 0 for everything, ACEE `STC`/`STCGROUP` | 0 for everything |
| RAKF 2.0.0, tables missing or invalid | system does not start | system does not start |

The healthy return code for an unknown class depends on the RAKF version (4 versus 8), so it is at most a supplementary signal, not a version-independent test.

## Not covered

- RAKF that is not active at all (no RCVT connection), and RACF instead of RAKF.
- The abend code of JES2 on RAKF 2.0.0 without tables.
