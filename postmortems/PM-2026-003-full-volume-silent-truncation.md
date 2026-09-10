---
id: PM-2026-003
title: A hundred source members went unreadable — the volume was full, and every reader reported it differently
status: tested
platform: [mvs38j]
sources:
  - "mvs38src/docs/fahrplan.md — the volume geometry section"
  - "mvs38src/docs/dave-install-log.md — run 5 on MVSTK5-BLD"
  - "Observed on MVSTK5-BLD, 2026-09-10, during Dave Kreiss' SMP build chain"
verified_on: 2026-09-10
applies_to: [mvs38src, mvsmf]
tags: [dasd, space, d37, iec031i, mvsmf, ftp, iehlist, silent-truncation, postmortem, rest, http-200]
related: [MVS-DASD-0001]
---

## Symptom

A 227-job SMP build finished. Reading the resulting source library
`MVSSRC.BLD.AMVSSRC` over mvsMF's REST interface, **100 of 2,012 members came
back as HTTP 200 with an empty body**. The extraction script stored them as
empty files and reported `miss=0`.

The console had been saying so all along, and nobody was looking at it:

```
MVSMF106E I/O ERROR READING MVSSRC.BLD.AMVSSRC ERRNO=5
```

## The three readers, and why only two of them were honest

| reader | what it said |
|---|---|
| **mvsMF REST** | `HTTP 200`, zero bytes — **success with no data** |
| **FTP** | `451 Read error on data set after 0 bytes: transfer is incomplete.` |
| **IEBGENER under MVS** | `CC 0000`, 0 records |

The FTP line is what turned a suspected client bug into a system fact: **two
independent readers hitting the same members**, one of them not going through
mvsMF at all. Until that point the working hypothesis was an mvsMF defect under
load, and it was wrong.

`IEBGENER` returning `CC 0000` with no records is the third reading and the most
misleading — a member that cannot be read and one that is empty are the same
thing to it.

## Cause

```
IEHLIST BLDSR2:  THERE ARE 0 EMPTY CYLINDERS PLUS 0 EMPTY TRACKS ON THIS VOLUME
MAINT04E:        IEC031I D37-04,IFG0554T,MAINT04E,SMP,AMVSSRC,196,BLDSR2
```

`D37` — space exhausted, no secondary extents left. SMP's ACCEPT ran out of room
writing source members into `AMVSSRC`, and the members it could not finish stayed
in the directory as unreadable entries.

Four of the twelve build volumes were at **zero free tracks**: the two source
volumes, one listing volume, one work volume. Each of the two source volumes
carried exactly **one dataset** — `MVSSRC.BLD.MVSSRC` and `MVSSRC.BLD.AMVSSRC` —
so neither could be relieved by moving something else off: a PDS does not span
volumes on MVS 3.8j, and the volume itself had to grow. See `[MVS-DASD-0001]`
for what "grow" is allowed to mean.

## What made it expensive

**The `CC 0016` was read as normal.** `MAINT04E` and its siblings had been
filed as "SMP's usual collective codes" because the equivalent jobs on the other
system were documented harmless. They were harmless there. Here one of them
carried `IEC031I`, and it was never opened.

> A return code that is benign on one system is not thereby benign on another.
> The message text is the evidence; the code is a summary.

**The extraction tool counted a read error as a member.** It treated any HTTP 200
as data and only counted `404` as absent, so 100 unreadable members became 100
empty files and a clean-looking `miss=0`. The fix is one branch:

```python
if not body:
    # An empty 200 is not an empty member.  mvsMF answers a read error with
    # HTTP 200 and no body; the console says MVSMF106E and the client sees
    # success.  A genuinely empty member is indistinguishable here, and that
    # is the right trade -- a wrongly kept empty file is a silent hole in a
    # corpus, a wrongly reported one is a line in a log.
    empty.append(member)
    continue
```

## What to check, in order

1. **Console** for `MVSMF106E` / `IEC031I` / `IEC030I` / `D37` / `B37` / `E37`.
2. **A second reader.** FTP against the same member. If both fail, it is the
   system, not the client.
3. **`IEHLIST LISTVTOC`** on the volume — but see `[MVS-DASD-0001]`: zero free
   space is also what a freshly `dasdload`ed volume reports while allocating
   perfectly well. On a volume that has been *written to*, zero is real.
4. **The failing job's own messages**, not its return code.
