---
id: MVS-DASD-0003
title: On a fresh TK5, copying a new member into SYS1.PARMLIB abends SD37 (IEC031I D37-04) — compress it or use a PARMLIB of your own
status: tested
platform: [mvs38j]
sources:
  - "QA acceptance run of FTPD 1.3.0, fresh TK5 throwaway container, 2026-10-22 (Paperclip MVS-20, ftpd#283 to #287): IEBGENER copy of FTPDPRM0 into SYS1.PARMLIB, IEBCOPY compress, repeat copy, private PARMLIB (as reported in the inbox note; job numbers belong to that container)"
  - "ftpd docs/installation.md at origin/main 5afc39a, section 'Which PARMLIB': 'SD37 is the system's out-of-space abend: the member did not fit'"
  - "postmortems/PM-2026-003: IEC031I D37-04,IFG0554T read as space exhausted without a secondary extent"
verified_on: 2026-10-22
verified_platforms: ["TK5 (image with SMP-installed FTPD 1.2.0)", "MVS/CE 3.0.0 (SYS2.PARMLIB, no failure)"]
applies_to: [ftpd, ufsd, httpd, mvsmf]
tags: [parmlib, sys1-parmlib, d37, sd37, iec031i, ifg0554t, iebgener, iebcopy, compress, tk5, space]
related: [PM-2026-003, MVS-DASD-0001, MVS-SMP-0015]
---

## The claims

- **On a fresh TK5, the copy of the first new member into `SYS1.PARMLIB` abends.** `[tested]`
  ```
  IEC031I D37-04,IFG0554T,PARMCPY,COPY,SYSUT2,390,TK5RES,SYS1.PARMLIB
  IEF450I PARMCPY COPY - ABEND SD37 U0000
  ```
  The job was an IEBGENER copy, member to member (`FTPDPRM0`). Nothing is wrong with the input data.
- **A compress of `SYS1.PARMLIB` cures it.** IEBCOPY `COPY` of the library onto itself: `IEB161I COMPRESS TO BE DONE USING INDD NAMED PARMLIB`, CC 0000; the same
  copy then ended CC 0000. `[tested]`
- **A PARMLIB of your own avoids the library.** `HERC01.PARMLIB` allocated and `FTPDPRM0` copied into it ended
  CC 0000; the started task with `/S FTPD,D='HERC01.PARMLIB'` read it (`F FTPD,CONFIG` listed the values from
  that member). `[tested]`
- **MVS/CE does not have the problem here.** `SYS2.PARMLIB` has room, so the default `D='SYS2.PARMLIB'` of the
  shipped FTPD procedure works without a change. `[tested]`

## The reading that is not recorded

The inbox note read `D37-04` as "the directory of that PDS has no room for another member". That reading is
not recorded here. It sits badly with the cure: a compress gives back the space that replaced members
left behind, and adds no directory blocks. That is reasoning, not a measurement. Both other places in the KB that meet this message read it as out
of space: PM-2026-003 (`D37`, space exhausted, no secondary extent) and ftpd's installation guide (`SD37` is
the out-of-space abend: the member did not fit). The measured facts above hold either way. Which of the
two limits (data blocks or directory) `SYS1.PARMLIB` hit was not isolated, for example by listing the
library's directory usage before the compress. `[assumed]`

Container results, not stand results.
