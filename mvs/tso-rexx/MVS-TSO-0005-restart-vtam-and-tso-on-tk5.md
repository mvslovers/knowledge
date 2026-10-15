---
id: MVS-TSO-0005
title: Restarting VTAM (NET) on TK5 -- HALT NET,QUICK waits on IKT012D, and S NET does not bring TSO back
status: tested
platform: [mvs38j]
sources:
  - "TK5 on Hercules 4.9.1.0-SDL (mvsdev.lan, stand m38r / MVSTK5-REF): operator commands through `mbt target console m38r`, replies quoted below -- 2026-10-15"
  - "m38r console log read through the mvsMF console API (`/zosmf/restconsoles/v1/log`) -- 2026-10-15"
verified_on: 2026-10-15
applies_to: [mbt]
tags: [tso, vtam, net, tcas, ikt012d, halt-net, tk5, logon, operator-command]
related: [MVS-TSO-0004]
---

## When to use it

TSO logons on a TK5 system stop working while the system itself runs on. A
restart of VTAM (started task `NET`) and of TSO (started task `TSO`, TCAS) brings
logons back without an IPL. `[tested]` On 2026-10-15 the sequence below ran through
as described, and the maintainer's TSO logon worked again afterwards.

Try the narrower fix first if the terminal is known: a single local terminal that
lost its NETSOL allocation is given back with `V NET,INACT/ACT` on that one node,
and every other session survives [MVS-TSO-0004]. A NET restart ends **every** VTAM
session on the system.

## What it does not touch

`JES2`, `TP` (TCAM), and the TCP/IP servers `HTTPD`, `FTPD`, `UFSD` and `OFTPD` kept
running through the restart; `D A,L` listed all of them before, during and after.
`[tested]` Their network access goes through Hercules, not through VTAM, so a NET
restart does not touch them. `[inferred]`

## Before: check that nobody is logged on

```
D TS,L
IEE102I 09.39.11 26.288 ACTIVITY 247
00000 TIME SHARING USERS
00000 ACTIVE  00040 MAX VTAM TSO USERS
```

`D NET,APPLS` and `D NET,TERMS` are refused on this VTAM
(`IST039I DISPLAY FAILED- UNIDENTIFIABLE KEYWORD`). `D NET,ID=TSO` works. `[tested]`

## Step 1: halt VTAM

```
Z NET,QUICK
IST097I  HALT     ACCEPTED
IST133I  VTAM TERMINATION IN PROGRESS
IST109I  NETWORK SOLICITOR IS NOW TERMINATED
IKT009I TPEND HAS OCCURRED, TCAS TERMINATION IN PROGRESS
01 IKT012D TCAS TERMINATION IN PROGRESS - SPECIFY 'U' OR 'DUMP'
```

The nodes then go `IST105I ... NODE NOW INACTIVE` / `IST141I ... NOW DORMANT`.
**The halt does not finish on its own:** while `IKT012D` is outstanding, `NET` and
`TSO` both stay in `D A,L`. `[tested]`

## Step 2: answer TCAS

Take the reply id from the `IKT012D` line (it was `01` here; it changes):

```
R 01,U
IEE600I REPLY TO 01 IS;U
```

Ten seconds after the reply, `NET` and `TSO` were both gone from `D A,L`. `[tested]`

## Step 3: start VTAM

```
S NET
IEA000I 0C6,IOE,05,0200,400000000001,,,NET     ,09.41.14
IFL003I  IFLOADRN COMPLETED
IST270I  370X N07      NOW LOADED WITH LOADMOD N07
IST020I  VTAM INITIALIZATION COMPLETE
```

The `IEA000I` came during the start and did not stop it. `[tested]` What it means
for device `0C6` was not looked into.

## Step 4: start TSO -- it does not come back by itself

Thirty seconds after `IST020I`, `D A,L` showed `NET` but no `TSO`. `[tested]` TSO
needs its own start:

```
S TSO
$HASP373 TSO      STARTED
IKT007I TCAS ACCEPTING LOGONS
IKT005I TCAS IS INITIALIZED
```

```
D NET,ID=TSO
IST075I  VTAM DISPLAY- NODE TYPE= APPL  ,NAME= TSO      ,STATUS= ACT
```

## Wrong turn

`D A,L` already listed `NET` and `TSO` before the restart, and `D NET,ID=TSO` showed
`STATUS= ACT` with 0 sessions. Neither tells you whether a logon works. The
cause of the broken logon was not found: this VTAM refuses `D NET,TERMS`, so the
terminals could not be listed to look for the [MVS-TSO-0004] case.
