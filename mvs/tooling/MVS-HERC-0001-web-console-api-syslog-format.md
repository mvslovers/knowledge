---
id: MVS-HERC-0001
title: Hercules web console API -- how an operator command and its reply appear in the syslog
status: tested
platform: [mvs38j]
sources:
  - "Hercules 4.10.0.11773-SDL-DEV under MVS/CE v2.1.4 (mvsdev.lan:8181), GET /cgi-bin/api/v1/syslog and /cgi-bin/api/v1/devices -- 2026-10-07"
  - "Hercules startup messages (given by the maintainer): HHC01808I HTTP server port is 8181 with noauth"
  - "mbt internal/console (mvslovers/mbt#178): the parser built on this format, unit test and live run"
  - "Hercules under MVS/CE on m38x (MVSCE-EXP, mvsdev.lan:8383), GET /cgi-bin/tasks/syslog?msgcount=N -- 2026-10-18, during the OFTPD SVC install run (oftpd internals/xmem.md section 10)"
verified_on: 2026-10-18
applies_to: [mbt, oftpd]
tags: [hercules, web-console, http, cgi-bin, api, syslog, hhc00013i, operator-command, console, devices, tn3270, msgcount, wto, display-active]
related: [MVS-TSO-0004]
---

## Where it is

The Hercules HTTP server is configured in Hercules, not in MVS. Its startup
log names the port and whether it asks for a password:
`HHC01808I HTTP server port is 8181 with noauth`. `[tested]` On mvsdev, port
8080 is MVS's own HTTPD (mvsMF), not Hercules. Don't mix them up. `[tested]`

The M38 stands run on the same host, each with a pair of its own: on m38x,
8083 is mvsMF and 8383 is Hercules. `[tested, 2026-10-18]` **The pairing is
per stand, not an offset** — dev1 is 8080/8181, m38x is 8083/8383. Read the
pair from the target entry (`mbt target` lists the mvsMF one), not from
arithmetic. The Hercules version and the auth mode on m38x were not read; no
credentials were asked for. `[tested, 2026-10-18]`

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

## Reading the log without issuing a command: `/cgi-bin/tasks/syslog`

```
GET /cgi-bin/tasks/syslog?msgcount=200
```

A second route of the same HTTP server, and the one to use when all that is
wanted is the recent console log. It answers **HTML**, not JSON — strip the
tags and grep:

```
curl -s 'http://mvsdev.lan:8383/cgi-bin/tasks/syslog?msgcount=200' \
  | sed 's/<[^>]*>//g' | grep -iE 'OFTP[0-9]|IEF40[34]I|HASP395'
```

HTTP 200 with no credentials sent, measured on m38x. `[tested, 2026-10-18]`
It is the same `msgcount` parameter as the API route, and messages from MVS
carry the same `/ ` prefix, indentation kept:

```
/ IEE102I 22.55.58 26.290 ACTIVITY 748
/    00006 JOBS    00003 INITIATORS
/   JES2     JES2     IEFPROC   V=V
```
`[tested, 2026-10-18]`

**A command issued through mvsMF leaves no `HHC00013I` echo.**
`mbt target console` goes through the mvsMF console API (it prints
`[mbt] console (mvsmf): <cmd>`), i.e. SVC 34 inside MVS, not a `/` command
entered at the Hercules panel — so only the reply appears. In one 30-entry
window holding three such commands there was no `HHC` line at all.
`[tested, 2026-10-18]` The `HHC00013I` anchor above belongs to commands
entered through Hercules; do not rely on it when the command went in
another way.

**This is the route to a started task's WTOs when the usual ones are closed.**
On m38x `/.dm` is not registered (404) and the mvsMF REST API refused basic
auth (401) — `[tested, by the session that owns that stand]` — and the
Hercules console still gave the task's whole start and stop sequence.
`mbt target console <name> -- CMD` issues the command and returns the reply
the console shows at once; WTOs the task writes afterwards are **not** in its
output, and were read from this route. `[tested, 2026-10-18]`

## `msgcount` counts messages, and your own polling fills the window

The window is not a time span and nothing ages out of it: messages are pushed
out by later messages, the operator's own displays included. `[tested]`

One `D A,L` on an idle m38x costs 10 entries: `IEE102I` plus its
continuations — six started tasks, the initiator line, the two TSO user
lines. Three of them, issued to wait for a task to end, filled a
`msgcount=30` read **completely**: all 30 entries were those three activity
displays, and nothing else was in the window. The task's own stop messages
(`OFTP002I`, `OFTP003I`, `IEF404I`, `$HASP395`) were absent there and all
present at `msgcount=400`, minutes later in the same session.
`[tested, 2026-10-18]`

Two rules follow. **Do not poll the console of a stand whose log you are
about to read** — the poll buries what you came for, and the gap reads
exactly like a message that was never written. And when looking for specific
messages, ask for several hundred; the request is cheap.

Where a wait is needed anyway, wait on something that writes nothing to the
console (a REST poll, a job status, a sleep), or issue the displays *after*
reading the log rather than before.

Aside, met the same way: **`D A,<jobname>` does not exist here.**
`D A,OFTPD` answers `IEE535I D        INVALID PARAMETER` on m38x (MVS/CE,
MVS 3.8j); `D A,L` is the only form. `[tested, 2026-10-18]`

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
  `noauth`); whether m38x runs `noauth` too, or something else that asked for
  nothing.
- ~~How long MVS may take to answer before the reply is lost from a
  `msgcount` window on a busy console.~~ Partly answered on 2026-10-18: the
  window is counted in **messages**, not time, and the usual flooder is the
  reader's own `D` commands — see above. Still open is the narrower case: a
  command whose reply is slow while *other* traffic fills the window.
- Whether `/cgi-bin/api/v1/` exists on m38x's Hercules, and whether
  `/cgi-bin/tasks/syslog` exists on mvsdev's. Each route was used on one
  stand only; neither was tried on the other.
