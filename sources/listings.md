# Source listings and decks

Catalogue only. Large or binary material stays outside the repository; small
text artifacts that documents cite directly are kept here so citations resolve
in a fresh clone.

---

### SRC-0001 — SYS1.MACLIB member list, MVS 3.8j (MVS/CE, Hercules)

    format:   plain text, 742 member names, one per line
    location: sources/sys1-maclib-members-mvs38j.txt  (in this repo)
    obtained: zowe files list ds "SYS1.MACLIB" --member-pattern "*"
    date:     2026-08-03
    system:   Mike's MVS 3.8j under Hercules
    covers:   which executable service macros exist on the target system
    cited by: ECO-0005

    why kept: settles "does MVS 3.8j have <macro>" mechanically instead of by
              inference. Note the scope limit — on MVS 3.8j the *mapping* macros
              (CVT, IHAPSA, IHAASCB, IHAASSB …) live in SYS1.AMODGEN, not in
              SYS1.MACLIB, so absence from this list is conclusive for service
              macros only. An AMODGEN listing is still missing.
