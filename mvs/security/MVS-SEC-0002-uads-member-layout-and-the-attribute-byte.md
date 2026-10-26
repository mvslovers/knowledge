---
id: MVS-SEC-0002
title: SYS1.UADS member naming and the attribute byte (OPER, ACCT, JCL, MOUNT)
status: tested
platform: [mvs38j]
sources:
  - "MVS/CE and TK5 throwaway containers, 2026-10-21: IEBPTPCH PRINT TYPORG=PO,MAXNAME=1,TOTCONV=XE of single UADS members after changing one attribute at a time with ACCOUNT/CHANGE; job output is container-local and not kept"
verified_on: 2026-10-21
applies_to: [libc370, ftpd, mvsmf]
tags: [uads, oper, tso, account, pscb, security]
related: [MVS-SEC-0001, MVS-SEC-0003]
---

## The claims

- `SYS1.UADS` is a PDS (DSORG=PO, RECFM=FB, LRECL=80, BLKSIZE=800). `[tested]`
- A user's member is named **userid followed by `0`**: `IBMUSER0`, `MVSCE020`, `HERC030`. A
  7-character userid gives an 8-character member name. `[tested]`
- Record 1 of the member: bytes 0-3 `03 20 00 40`, bytes 4-11 the userid, blank padded (EBCDIC),
  and the **attribute byte at offset 16** (0-based). `[tested]`
- Attribute bits, found by changing one attribute at a time: `[tested]`

  | Bit | Attribute |
  |---|---|
  | `0x80` | OPER |
  | `0x40` | ACCT |
  | `0x20` | JCL |
  | `0x10` | MOUNT |

  Identical on MVS/CE and TK5.
- A program can therefore read the OPER bit from record 1 of the member. The UADS password field is
  not needed for that and was not examined. `[tested]`

## The evidence

Attribute byte as dumped, MVS/CE user MVSCE02 (each line adds one attribute to the base
state) and IBMUSER:

```
MVSCE02  NOOPER NOACCT JCL (base)    20
         base + OPER                 A0
         base + ACCT                 60
         base + MOUNT                30
IBMUSER  OPER ACCT JCL MOUNT         F0
```

## Authorization to read the member

With no profile for `SYS1.UADS`, the universal `DATASET *` READ profile applies. RACHECK for the
FTPD user (RACINIT without password): READ rc 0, UPDATE rc 8 (group USER on MVS/CE, group FTPD on
TK5); an operator ACEE gets UPDATE too. `[tested]` Not tried: an actual OPEN of the PDS under the
FTPD started-task identity.

Which of the two operator flags does what is in MVS-SEC-0001.
