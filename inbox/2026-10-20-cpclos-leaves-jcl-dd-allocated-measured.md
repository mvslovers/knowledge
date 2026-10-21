# libc370 __cpclos()/__jsclos(): a DD statement from the JCL stays allocated after their dynamic unallocation request

Source: libc370 session, 2026-10-19. Measured on the way while doing
mvslovers/libc370#142 (`jesopen()` without DD statements, `jesopen_ex()`),
PR mvslovers/libc370#679 (merged; "Also measured on the way" in the PR
body). Platform: MVS 3.8j, MVS/CE in an own throwaway container. KB check
before writing: no document covers dynamic unallocation (SVC 99 S99VRBUN)
of a JCL-allocated DD.

## Finding

`__cpclos()` (`src/mvs/jes2ckpt/@@cpclos.c`) and `__jsclos()`
(`src/mvs/jes2spool/@@jsclos.c`) close the DCB and then always issue an
SVC 99 unallocation (`S99VRBUN`, `S99NOCNV`, text unit DDNAME only) for the
handle's DD name, however that DD was allocated. When the DD came from a
DD statement in the step's JCL, it is still allocated afterwards: its DSAB
is still found, and a second open through the same DD works.

## Measurement

Probe `test/mvs/tstjsop.c` (libc370), JCL `jcl/recvjsop.jcl` /
`jcl/tstjsop.jcl`, step GDD (JCL has `HASPCKPT` and `HASPACE1` DD
statements), JOB00019 (container-local), COND CODE 0000:

```
+TSTJSOP   checkpoint DD HASPCKPT, spool DD HASPACE1
+TSTJSOP PASS: the DDs of the JCL were used
+TSTJSOP   after jesclose(): HASPCKPT allocated, HASPACE1 allocated
+TSTJSOP PASS: a second jesopen() uses the HASPCKPT DD again
```

"allocated" = `get_dsab(NULL, "HASPCKPT")` / `get_dsab(NULL, "HASPACE1")`
non-NULL after `jesclose()`, which calls `__cpclos()` and `__jsclos()`.
The same job's step GNODD (no DD statements) shows the dynamically
allocated pair going away: `jesclose() unallocated both DDs`, "DDs in the
step: 2 before, 2 after" over ten open/close rounds.

Not measured: the SVC 99 return code and error reason of the unallocation
request for the JCL DD (`__cpclos()` discards them). So it is established
that the DD survives, not why (refused by SVC 99 or otherwise). An earlier
draft of the Library Reference said "MVS refuses to unallocate it"; that
was cut back to "stays allocated" for this reason.

## What it means for callers

- A program can pass its own JCL DD to `__cpopen("DD:...")`/`jesopen()`
  and call `__cpclos()`/`jesclose()` without losing the DD; it can be
  opened again later in the same step (Library Reference, `__cpopen,
  __cpclos` and `jesclose`).
- Dynamically allocated DDs (no DD statement, `jesopen()` after PR #679, unreleased
  on 2026-10-20, allocates `SYS1.HASPCKPT`/`SYS1.HASPACE` itself) are freed by
  `jesclose()`; the step needed no `DYNAMNBR` for the two (measured in a
  step with no other dynamic allocation).
- Do not generalise to "SVC 99 never unallocates a JCL DD" from this
  probe: the return code was not looked at.
