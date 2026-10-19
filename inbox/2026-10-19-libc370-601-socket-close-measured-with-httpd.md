# libc370 2.20.0 (#601): a cancelled server gives its port back -- measured with HTTPD

Date: 2026-10-19. Source: httpd session, httpd#303 / PR httpd#306, coordinated with
the libc370 session (code reading of src/net/@@soadd.c, @@soupd.c,
src/mvs/crt/@@crtset.c, @@ppahrv.c, @@exit.c on libc370 main).

## Setup

Local MVS/CE container (mvsce-target, Apple `container` runtime,
image sha256:a6096e33...). Two HTTPD instances run side by side as batch jobs,
each with in-stream HTTPPRM:

| job | build | libc370 (HTTPD005I) | port |
|---|---|---|---|
| T303HTTP JOB00035 | httpd 4.4.0-dev (c8faa0e + fix) | 2.20.0 (D5D2B53) | 8081 |
| T303CTRL JOB00036 | httpd 4.3.0 (32F2A0F), installed HTTPD.LINKLIB | 2.12.1 (0C5E84F) | 8082 |

## Measurement 1: port after CANCEL

`C T303HTTP` and `C T303CTRL`; both jobs end with ABEND S222. Then
`curl --max-time 8 http://<vm>:<port>/`:

- 8081 (2.20.0): curl rc 7, connection refused at once. The listening socket
  was closed when the job ended.
- 8082 (2.12.1): curl rc 28, timeout. The socket outlives the job (the emulator's
  socket table is system-wide), so the port stays occupied until Hercules restarts.

Consequence: before 2.20.0, a server that abends or is cancelled blocks its port
until the next Hercules restart. From 2.20.0 on, an unrecovered abend (S0C1, S322,
S222 per the libc370 changelog) runs the start-up ESTAE (__soestae), which closes
the program's sockets.

## Measurement 2: a LINKed module's abend does not close the server's client socket

A socket belongs to the program (GRT) whose socket() or accept() created it. CTHREAD
subtasks inherit the parent's GRT via __crtset, so HTTPD's socket thread and
workers share HTTPD's GRT. A LINKed CGI module has its own PPA/GRT. Its harvest
(__ppahrv on an abend under try(), __exit on a normal end) closes only its own list,
which is empty for a module that never calls socket()/accept(). That was the code
reading; the measurement:

On 8081 (2.20.0), curl keep-alive sequence `/.abend` (ABEND0C1, S0C1 under try(),
HTTPD908E) and then `/.dm` (HTTPDM) on the **same** connection gives 503, then 200
with the connection reused. The client socket accept()ed by the server survived the
module's abend.

Edge case per the libc370 session (not measured): a LINKed module that itself calls
socket()/accept() gets a start-up ESTAE in the worker TCB. __soexit deletes it only
when crtestct == 1, so a module ending with its own estae() still set would leave
an ESTAE pointing into the deleted module.

## Unrelated finding in the same run (httpd#307)

A module abend as the 2nd or later request on a keep-alive connection gets no
response (curl 000). As the 1st request it gets 503. This is identical on 4.3.0/2.12.1
and 4.4.0-dev/2.20.0, so it is not caused by libc370.
