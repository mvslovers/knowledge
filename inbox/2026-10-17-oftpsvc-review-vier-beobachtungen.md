# 2026-10-17 — Review der OFTPD-SVC-Routine (oftpd#1, PR #5/#6): vier Beobachtungen

Roh erfasst beim Review von `oftpd/asm/oftpsvc.asm`, noch nicht eingepflegt.
Nichts davon lief auf MVS; alles ist Quellen- oder Host-Messung.

1. **as370 exitet mit der Severity, und mbt gatet korrekt darauf — die Lücke
   ist rc 4.** Gemessen mit as370 1.6.3 (802dde1): zwei Severity-12-Fehler →
   `exit 12`; doppeltes Symbol allein (IFO196, dort Severity 8) → 8;
   undefinierter Opcode → 8; Warnungen → 4; fehlerfrei → 0 und *gar keine*
   Ausgabe. mbts `as`-Step failt bei **rc >= 8** und löscht das Object Deck,
   damit ein späterer Build es nicht für aktuell nimmt; ein `cc370`-Step failt
   bei jedem rc != 0 und gibt ein Assembler-Problem als rc 1 weiter.
   Quelle: MBT-Sitzung, `mbt/internal/build/build.go`, am selben Tag auf ihrer
   Seite nachgemessen.

   **Gefährlich ist rc 4**: Warnungen passen per Design (wie `COND=(8,LT)`),
   as370 hat keinen Warnings-as-Errors-Schalter — und darunter fällt
   **IFO026, die Spalte-72-Continuation**, deren Schaden das Verschlucken der
   nächsten Quellzeile ist. Konkreter Fall: httprexx `asm/htrxterm.asm`
   verlor so ein `BALR` und abendete S0C1. Verteidigung ist mechanisch, nicht
   der Exitcode: `awk 'length($0)>=72' x.asm` muss leer sein. Ob rc 4 einen
   Build failen soll, liegt beim Maintainer (MBT legt es vor).

   Nebenbei, Kuriosität mit echtem Beleg: **IFO213 nullt die Instruktion.**
   Im Listing steht `000202 0000 0000`, wo `58F0 F098` hingehört — ein Deck
   kann strukturell in Ordnung sein und eine Instruktion fehlt. Durch den
   Exitcode gefangen, also heute harmlos.

   *Vorsicht bei der eigenen Messung:* eine erste Fassung dieser Beobachtung
   behauptete „as370 exitet 0 bei Severity 12". Falsch — das kam aus
   `as370 … 2>&1 | head -40; echo $?`, also dem Status von `head`. Ohne Pipe
   messen: `as370 … > out 2>&1; echo $?`.

2. **`MVCK`s Key-Check ist ein FETCH-Check, nicht der Schutz, für den er
   gehalten wird.** In der KB bisher gar nicht vorhanden (kein `MVCK`,
   `MVCP`, `MVCS`, `TPROT` irgendwo). `MVCK`s R3 gibt den Key, mit dem das
   *zweite* Operand (die Quelle) gelesen wird; ein Fetch mit Key 8 aus
   Speicher, dessen Key abweicht, dessen **Fetch-Protection-Bit aber aus
   ist**, ist erlaubt — und das ist der Normalzustand von Key-0-CSA.

   Folge für jede SVC- oder Cross-AS-Routine: „`MVCK` unter dem Key des
   Callers" hindert einen gefälschten Pointer **nicht** daran, Key-0-Speicher
   zu lesen. Nur eine Store-Prüfung tut das. `TPROT` liefert sie ohne Fault
   (CC 0 Store erlaubt, 1 nur Fetch, 2 kein Zugriff, 3 Speicher nicht
   verfügbar), also: `TPROT` auf Store verlangen, dann muss der Range im
   eigenen Key des Callers liegen. Zwei `TPROT`s pro Range genügen, solange
   der Range <= 2048 Bytes ist (spannt höchstens zwei 4K-Blöcke, erstes und
   letztes Byte deckt beide) — ab > 4096 braucht es einen Walk.
   `TPROT` assembliert in as370 als SSE: `TPROT 4(5),8(9)` → `E501 5004 9008`.

3. **Präzisiert `ECO-0004`** (Cross-AS-POST), dort `status: source` und
   ausschließlich aus libc370/ufsd belegt. Diese drei Punkte kommen aus
   **IBMs eigener Quelle** (`mvs38-ibmsrc/ibm/IEA/IEAVSY50.asm`), gelesen von
   der libc370-Sitzung — nicht silently korrigieren, bitte triagieren (§9):

   - **POST setzt das Post-Bit selbst.** Jeder Pfad macht
     `N XRPTCODE,OFFWAIT` dann `O XRPTCODE,ONCOMPL` vor dem Store ins ECB
     (Zeilen 966, 1101, 1359, 1386, XM-SRB-Pfad 1498; `OFFWAIT DC XL4'7FFFFFFF'`,
     `ONCOMPL DC XL4'40000000'` bei 2013). libc370s `postcode | 0x40000000`
     in `@@xmpost.c` ist also redundant, nicht erforderlich.
   - **Das High-Bit von R10 fordert die ECBKEY-Option an**, mit dem Key aus
     R0 Byte 3 (Interface-Block 628-646, Notizen 3 und 7; der XM-Pfad testet
     es bei `ECBVALCK`, Zeile 1660, `LTR`/`BNM`). libc370s `& 0x7FFFFFFF`
     ist, was das ausschließt. R10 ist damit Pflichteingabe, aber aus diesem
     Grund — nicht weil das ECB sonst ungepostet bliebe.
   - **R9 *und* R14 überleben den Call**, nicht nur eines: Exit-Notizen
     675-680, „REGS 9,14 ARE SAVED OTHERS ARE LOST IF LOCAL LOCK IS NOT
     HELD". ECO-0004 sagt „Only R13 is preserved across the call" — das
     beschreibt, was `@@xmpost.c`s Wrapper für seinen C-Aufrufer leistet
     (er rettet R13 über R9), liest sich aber wie der Interface-Vertrag und
     verschweigt, dass der R9-Trick genau *deshalb* funktioniert. Die
     Registertabelle in ECO-0004 ist korrekt, inklusive R10.

4. **`aceeuser` ist längenpräfixiert, und das ist IBMs Layout**, nicht eine
   Konvention seiner Konsumenten: `macros/maclib/IHAACEE.asm:53-55` ist
   `ACEEUSER DS 0CL9` / `ACEEUSRL DS AL1` / `ACEEUSRI DS CL8`. libc370s
   `ihaacee.h:22` fasst die drei zu `char aceeuser[9]` zusammen — daher der
   Fehlgriff, ein glattes 8-Byte-`MVC` ab +0 zu schreiben, das das
   Längenbyte in das erste Zielbyte legt, den Namen um eins verschiebt und
   das letzte Zeichen verliert. `ACEEUSRI` wird von IBM selbst als auf 8
   blank-gepaddet behandelt (`ibm/IEF/IEFSMFIE.asm:395`,
   `HASPSSSM.asm:9055`) und von RAKF (`ICHSFR00.hlasm:527` vergleicht
   `=CL8'STC'`) — nicht gelesen: der RACINIT-Pfad, der die ACEE *baut*, also
   drei Konsumenten als Evidenz, nicht der Produzent. Berührt den
   `acee`-Bereich von `ECO-0008`. libc370#581 nimmt die Unterfelder in
   `ihaacee.h` auf.
