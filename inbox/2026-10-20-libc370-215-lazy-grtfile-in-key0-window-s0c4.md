# 2026-10-20 — S0C4 in key 8: libc370 >= 2.15.0 creates the stdio stream table under the caller's PSW key (UFSD start)

Quelle: UFSD #107 / libc370 #693, Paperclip-Task MVS-8. Plattform: mvs38j (MVS/CE), gemessen in einem
Wegwerf-Container (t667fcd auf mvsdev), STC00032–STC00051; Dump-Auswertung mit `ld370 --map`, `cc370 -c`
von `src/ext/array/@@aradd.c` und `dasm370`. Freigabe zum Eintragen: Mike Großmann, 2026-10-20.

## Befund

Ein Programm, das mit einem von 0 verschiedenen PSW-Key läuft (UFSD: Load-Modul AC(1), STC, Key 8) und
innerhalb eines `__super(PSWKEY0, ...)`-Fensters libc370 aufruft, deren **erster** `fopen()` im Prozess
stattfindet, bekommt später ein S0C4 (Schutzverletzung, INTC 0004, PSW-Key 8) im ersten `fopen()` im eigenen
Key. Betroffen sind alle libc370-Releases ab 2.15.0 (#564, "lazy start-up", `GRTFLAG1_STDLAZY` 0x20).

Mechanik:

1. Ab 2.15.0 ist `grt->grtfile` beim Start `NULL` (die Standard-Streams werden beim ersten Gebrauch geöffnet).
   Bis 2.14.0 legt der Start ein Array mit drei Einträgen (stdin/stdout/stderr) im Key des Programms an.
2. `__loadhi()` (`src/mvs/link/@@loadhi.c`) macht `fopen("DD:STEPLIB(member)","rb")` und `fclose()`.
   UFSD ruft es in `ufsd_ssi_load()` (`src/ufsd#sct.c`) im Key-0-Fenster.
3. Der erste `fopen()` ruft `arrayadd(&grt->grtfile, fp)` (`src/stdio/@@fpopn.c`); `grtfile` ist `NULL`,
   also legt `arrayadd` das Array per `calloc()` (GETMAIN unter dem aktuellen PSW-Key) an: **Key-0-Speicher**.
   `fclose()` leert es (Count 0), das Array bleibt.
4. Zurück in Key 8 speichert der nächste `fopen()` (`ufsd_cfg_read` -> `DD:UFSDPRM`) den neuen `FILE *` in
   den Slot des Key-0-Arrays: S0C4. Befehl `ST 6,0(3,4)` bei Offset 0x168 in `@@aradd` (PSW-Adresse 0x16C).

## Bisect (UFSD main d10d40c + Debug-Code, libc370 je Tag privat gebaut, gleicher Container, gleiche JCL)

| libc370 | UFSD-Start |
|---|---|
| 2.10.3 | READY |
| 2.12.1 | READY |
| 2.14.0 | READY |
| 2.15.0 | S0C4 |
| 2.22.0 | S0C4 |
| 2.23.0 | S0C4 |
| 2.24.0 | S0C4 |

2.16.0 bis 2.21.0 nicht gemessen. 2.23.0 und 2.24.0 starten mit dem Workaround.

## Dump-Auswertung

- SYSUDUMP enthält keinen Modulspeicher und keine Programmregister. Die Fehlerstelle ergibt sich aus
  Modulbasis = CDE-EPA minus Einstiegs-Offset aus `ld370 ... --map` und dem Disassemblat von `@@aradd.o`
  (Sektionslänge 0x1D0 passte zur Map).
- 2.24.0-Lauf: `grt` = 0xBBC90 (Key 8, Heap); das leere `grtfile`-Array liegt bei 0xFC384 (Key 0);
  `calloc`-Blöcke aus Key-8-Code liegen bei 0xFD448 und sind schreibbar.

## Workaround (verifiziert auf 2.23.0 und 2.24.0)

Vor dem ersten Key-0-Fenster, im Key des Programms: `{ FILE *wf = fopen("DD:STEPLIB","rb"); if (wf) fclose(wf); }`.
Das legt das Array in Key 8 an. In UFSD: `ufsd_ssi_load()`, PR mvslovers/ufsd#108.

## Offen

- Fix in libc370 (Issue #693): der Stream-Table-Speicher darf nicht vom PSW-Key des ersten Aufrufers abhängen.
- Nicht geprüft: ob die anderen Lazy-Initialisierungen aus #564 (SYSENV, Zeitzone) bei einem ersten Gebrauch
  im Key-0-Fenster dasselbe Muster zeigen.
- Auswirkung auf andere AC(1)-Produkte, die per `__loadhi` laden: ungeprüft.

## Nebenbefund derselben Sitzung (Test-Technik)

Ein temporäres Datenset (`DISP=NEW`, SVC 99 ohne DSN) ist per `&&Name` in einer zweiten SVC-99-Allokation
**nicht** auffindbar (S99 Error 1708). Über Name und Volser aus dem JFCB des Schreib-DD (`rdjfcb`) ist es
mit `DISP=SHR` und anderem DCB erreichbar; so lässt sich ein DCB-Override erzeugen, ohne ein katalogisiertes
Datenset (UFSD #69, `test/mvs/tstufsio.c`, PR #111). Außerdem: `fclose(stdin)` gefolgt von `freopen(..., stdin)`
endet mit S A0A; `freopen()` direkt auf den noch offenen Stream schließt den alten selbst.

## Nachtrag 2026-10-21: behoben in libc370 2.24.1

libc370 2.24.1 (Release 2026-10-20, Issue #693) legt die Dateiliste, die Standard-Streams und die
`SYSENV`-Umgebung im Key der Task an. Laut Release Notes, gemessen mit demselben Testprogramm unter 2.24.0
und 2.24.1 (APF, Key 8): `fopen()` in Key 8 nach einem ersten `fopen()`/`fclose()` im Key-0-Fenster endet
unter 2.24.0 mit S0C4 und öffnet unter 2.24.1. Der Workaround ist ab 2.24.1 nicht mehr nötig.

Damit beantwortet sich der offene Punkt zu den anderen Lazy-Initialisierungen teilweise: Laut denselben
Release Notes war `SYSENV` genauso betroffen (S30A in `setenv()` nach erstem `getenv()` im Key-0-Fenster).
Unverändert gilt: Speicher aus `malloc()` oder `fopen()` innerhalb eines Key-0-Fensters ist Key-0-Speicher
und muss dort freigegeben bzw. geschlossen werden. Quelle des Nachtrags: Release Notes libc370 v2.24.1.
