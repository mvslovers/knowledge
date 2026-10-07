---
id: MVS-TSO-0004
title: A dropped TN3270 logon can leave its local terminal unallocated -- V NET,INACT/ACT gives it back to NETSOL
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE v2.1.4 on Hercules 4.10.0.11773-SDL-DEV (mvsdev.lan), SYS1.VTAMLST(LCL400): 31 local 3277 terminals CUU400-CUU41E -- 2026-10-07"
  - "Operator commands through the mvsMF console API, replies quoted below -- 2026-10-07"
  - "Hercules device list, http://mvsdev.lan:8181/cgi-bin/api/v1/devices -- 2026-10-07"
verified_on: 2026-10-07
applies_to: [mbt]
tags: [tso, vtam, netsol, tn3270, local-terminal, logon, hercules, v-net, ist082i, stuck-logon]
related: [MVS-HERC-0001]
---

## Symptom

Every new TN3270 connection gets the MVS/CE NETSOL logo screen ("CLEAR the
screen or hit ENTER"), and then nothing: ENTER and CLEAR get no answer.
Connections that already existed keep working. `[tested]`

`D TS,L` shows a logon that never finishes. Its line carries no userid, so
`C U=` cannot address it (`IEE324I STARTING NOT LOGGED ON`). `[tested]`

```
IEE102I 23.57.30 26.279 ACTIVITY
00001 TIME SHARING USERS
00001 ACTIVE  00008 MAX VTAM TSO USERS
STARTINGS
```

## Trigger

A TN3270 client connected a second time with a userid that was already logged
on. At the `IKJ56400A` prompt that follows `IKJ56425I ... IN USE`, it dropped
the connection instead of answering. `[tested]` (mbt's TN3270 client, test
`TestTSOIntegrationInUse`, first run, the night before 2026-10-07.) Answering
the prompt with `LOGOFF` may avoid this. That has not been measured. `[assumed]`

## Diagnosis: find the device, then its VTAM node

Hercules gives a new connection the **lowest free** 3270 device. When another
client holds `0400`, every new connection lands on `0401`, so `0401` is the one
that hangs. `[tested]`

Hercules' device list maps a client IP to a device number, and it does not
depend on VTAM:

```
GET http://<host>:8181/cgi-bin/api/v1/devices
{'devnum': '0400', ..., 'status': 'open ', 'assignment': '192.168.0.23 IO[23790]'}
{'devnum': '0401', ..., 'status': '',      'assignment': '* IO[1552]'}
```

On MVS/CE the device number is the node name: `0401` is `CUU401`. A healthy idle
terminal reads `ALLOC TO= NETSOL`. The stuck one had nobody: `[tested]`

```
IST075I  VTAM DISPLAY- NODE TYPE= LOCAL ,NAME= CUU401   ,STATUS= ACT
IST082I  DEVICE TYPE= 3277 , ALLOC TO=          ,SIMLOGON= NETSOL
```

`STATUS= ACT` is the same for good and bad terminals. Only the `ALLOC TO=` field
tells them apart.

## Fix

Deactivate the node immediately, then activate it again. VTAM gives the terminal
back to its `SIMLOGON` application: `[tested]`

```
V NET,INACT,ID=CUU401,I
IST141I  NODE CUU401   NOW DORMANT
IST105I  CUU401   NODE NOW INACTIVE
V NET,ACT,ID=CUU401
IST093I  CUU401   ACTIVE
IEA000I 401,IOE,05,0200,400000000001,,,NET     ,00.11.44
D NET,ID=CUU401
IST082I  DEVICE TYPE= 3277 , ALLOC TO= NETSOL   ,SIMLOGON= NETSOL
```

The `IEA000I` is an intervention-required condition on a device with no client
connected. It is harmless. `[inferred]`

Right afterwards a logon as a different userid reached `READY` in 1.7 s and
logged off cleanly. `[tested]`

## What the fix does not clear

The `STARTINGS` line in `D TS,L` was still there after the fix. `[tested]` It
seems to occupy one of the `MAX VTAM TSO USERS` slots. `[inferred]` No operator
command was found that removes it. Whether only an IPL clears it is open.
`[assumed]`

## Wrong turn

`D NET,ID=` showed a large `SIO=` count on `CUU400` and zero on most other
terminals, so `CUU400` was reset first. That count is history, not state.
`CUU400` belonged to a different, live 3270 client, and `INACT,I` cut that
session. **Map the device from Hercules' device list before resetting a node.**
`[tested]`

Displays through the console API can also come back truncated (some nodes
lacked the `IST082I` line on one call and showed it on the next), so read an
`ALLOC TO=` from a single-node display before acting on it. `[tested]`
