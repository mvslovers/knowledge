---
id: MVS-HERC-0001
title: Hercules web console API -- how an operator command and its reply appear in the syslog
status: tested
platform: [mvs38j]
sources:
  - "Hercules 4.10.0.11773-SDL-DEV under MVS/CE v2.1.4 (mvsdev.lan:8181), GET /cgi-bin/api/v1/syslog and /cgi-bin/api/v1/devices -- 2026-10-07"
  - "Hercules startup messages (given by the maintainer): HHC01808I HTTP server port is 8181 with noauth"
  - "mbt internal/console (mvslovers/mbt#178): the parser built on this format, unit test and live run"
verified_on: 2026-10-07
applies_to: [mbt]
tags: [hercules, web-console, http, cgi-bin, api, syslog, hhc00013i, operator-command, console, devices, tn3270]
related: [MVS-TSO-0004]
---

## Where it is

The Hercules HTTP server is configured in Hercules, not in MVS. Its startup
log names the port and whether it asks for a password:
`HHC01808I HTTP server port is 8181 with noauth`. `[tested]` On mvsdev, port
8080 is MVS's own HTTPD (mvsMF), not Hercules. Don't mix them up. `[tested]`

## Sending a command

```
GET /cgi-bin/api/v1/syslog?command=/D%20T&msgcount=0
```

The leading `/` routes the command to the guest's console (a Hercules panel
command without it would go to Hercules itself). The call returns at once. MVS
answers asynchronously, so the reply has to be read back with further
`GET /cgi-bin/api/v1/syslog?msgcount=N` calls. `[tested]`

The JSON object has the keys `command`, `msgcount`, `syslog` (an array of
lines) and `index`. `[tested]`

## How the syslog shows command and reply

```
'HHC00013I \'/\' input entered for console 0:0009: "D T"'
'D T'
'/ IEE136I LOCAL: TIME=00.31.37 DATE=2026.280  UTC: TIME=05.31.36 DATE=2026.280'
```
`[tested]`

- **The echo is `HHC00013I … "<cmd>"`, then the bare command.** It is *not*
  `/D T`. A parser that looked for `/<cmd>` (an assumption taken from the
  Hercules source) never found the echo and returned every reply empty
  (mvslovers/mbt#178). `[tested]`
- **Messages from MVS carry a `/ ` prefix.** Multi-line messages keep their
  indentation after it (`'/    00001 TIME SHARING USERS'`). `[tested]`
- **Hercules' own messages (`HHC…`, no prefix) interleave with the reply**,
  for example `HHC01022I … connection closed by client` when a 3270 client
  leaves. Filter on the `/ ` prefix, and anchor on the *last* matching
  `HHC00013I`, because a reply may repeat the command text. `[tested]`

## Device list

```
GET /cgi-bin/api/v1/devices
{'devnum': '0400', 'devclass': 'DSP', 'devtype': '3270', 'status': 'open ', 'assignment': '192.168.0.23 IO[23790]'}
{'devnum': '0401', 'devclass': 'DSP', 'devtype': '3270', 'status': '',      'assignment': '* IO[1552]'}
```

A connected 3270 shows `status 'open '` (with a trailing blank) and the client
IP in `assignment`. This is how to map a TN3270 client to its device, and so to
its VTAM node, without asking VTAM (see MVS-TSO-0004). `[tested]`

## Not measured

- Basic auth on a server configured with authentication (mvsdev runs
  `noauth`).
- How long MVS may take to answer before the reply is lost from a
  `msgcount` window on a busy console.
