# 2026-10-20 — libc370 lazy GRT file table: Rest nach dem Ingest vom 2026-10-22

Quelle: UFSD #107 / libc370 #693, PR ufsd#111 (`test/mvs/tstufsio.c`). Der Befund, die Bisect-Tabelle, der
Workaround und der Nachtrag zu 2.24.1 sind in `ECO-0013`, `MVS-SUP-0002` und `ECO-0014` eingegangen.
Zwei Seitenaussagen aus dem Nebenbefund blieben unbelegt (keine oeffentliche Quelle, keine zitierte Ausgabe)
und stehen unveraendert hier, bis sie jemand misst: SVC 99 `&&Name` -> Error 1708, und `fclose(stdin)` +
`freopen()` -> S A0A. Plattform: mvs38j.

## Nebenbefund derselben Sitzung (Test-Technik)

Ein temporäres Datenset (`DISP=NEW`, SVC 99 ohne DSN) ist per `&&Name` in einer zweiten SVC-99-Allokation
**nicht** auffindbar (S99 Error 1708). Über Name und Volser aus dem JFCB des Schreib-DD (`rdjfcb`) ist es
mit `DISP=SHR` und anderem DCB erreichbar; so lässt sich ein DCB-Override erzeugen, ohne ein katalogisiertes
Datenset (UFSD #69, `test/mvs/tstufsio.c`, PR #111). Außerdem: `fclose(stdin)` gefolgt von `freopen(..., stdin)`
endet mit S A0A; `freopen()` direkt auf den noch offenen Stream schließt den alten selbst.
