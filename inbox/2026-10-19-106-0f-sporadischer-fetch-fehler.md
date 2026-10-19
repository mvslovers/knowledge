# 2026-10-19 — IEA703I 106-0F: sporadischer Fetch-Fehler auf unveränderten Bibliotheken

Quelle: mvslovers/httpd#300 (Beschreibung und alle Kommentare, 2026-10-15 bis
2026-10-19), gemessen mit der Fetch-Probe `LDLP` (httpd `internals/fetchprobe/`,
PR mvslovers/httpd#301). Die Zahlen unten sind aus den Kommentaren übernommen;
die Jobnummern stehen dort mit den vollen Tabellen.

**Berührt `MVS-LNK-0001`** (`status: tested`). Dessen Konsequenz „`106-F` …
means the module is fetched from a place the link list does not know" ist für
die zwei dort gemessenen Ursachen (neue Extent, Compress) belegt, als
allgemeine Deutung von `106-F` aber zu weit: Punkt 2 unten zeigt `106-0F` auf
einer Bibliothek, die sich nicht verändert hat, über einen privaten STEPLIB
genauso wie über die Link List. Bitte beim Ingest prüfen, ob das ein Konflikt
(§9) ist oder nur eine Ergänzung („eine dritte Ursache"); MVS-LNK-0001 habe ich
nicht angefasst.

---

## 1. Was `106-0F` heißt, und was nicht

- IBMs Text zu Completion Code 106, Reason `0F` (z/OS MVS System Codes, also
  ein z/OS-Handbuch): *"Either an uncorrectable I/O error occurred, or an error
  in the load module caused the channel program to fail."* Speichermangel ist
  `0C`, nicht `0F`. Für 3.8j durch die Messungen unten gestützt, nicht durch ein
  3.8j-Handbuch.
- Gegenprobe: auf m38b (TK5) bekam HTTPD am 2026-10-15 `106-0F` beim Fetch von
  MVSMF bei 7.274.496 Bytes freiem Speicher in einem Block (`fn=storage`).
- Im Gegensatz dazu `106-0C` mit echtem Speichermangel: BREXX aus
  `SYS2.LINKLIB` ohne `REGION` (mvs-docker README, MVS/CE-Image).

## 2. Der Fehler tritt sporadisch auf, auf Bibliotheken, die sich nicht ändern

Probe: `LOAD EPLOC=IEMRA,ERRET=…` + `DELETE`, in Schleife; IEMRA ist eine
PL/I-(F)-Phase, 4 KB, ohne RLD. Jeder Fehler: `IEA703I 106- F … MODULE ACCESSED
IEMRA`, ERRET-Exit mit `R1=00000106 R15=0000000F`. **Der nächste LOAD gelingt
wieder.**

Gemessen (alle unter Hercules 4.10.0, sofern nicht anders gesagt):

| wo | Quelle | Rate | Jobs |
|---|---|---|---|
| m38r (TK5, MVSTK5-REF) | `SYS2.LINKLIB` über die Link List | 9–13 pro 750.000 | JOB00908, 00914 |
| m38r | dieselbe Bibliothek als `STEPLIB DD` | 16 pro 750.000 | JOB00908 |
| m38r | volle IEBCOPY-Kopie der Bibliothek, anderes Volume | 8–21 pro 750.000 | JOB00914, 00916 |
| m38r | Kopien mit nur 1–4 Membern | ca. 1 pro 2.500.000 (JOB00911 + 00912); 1 pro 2.000.000 (JOB00907) | JOB00907, 00911, 00912 |
| m38l (MVS/CE, MVSCE-LAB) | dieselbe volle Bibliothek (XMIT, gleiche Satzlage) | 1 pro 750.000 | JOB01788 |
| TK5-Container (mvs-docker, Hercules `a7423980`) auf mvsdev, x86-64 | dieselbe volle Bibliothek | 1 pro 1.000.000 | JOB00038 im Container |
| derselbe Container unter Apples `container` auf einem M2 Pro | dieselbe volle Bibliothek | 0 pro 1.000.000 | JOB37 im Container |

Was die Messungen trennen:

- **Nicht der Zugriffsweg:** Link List und privater STEPLIB auf demselben Data
  Set fallen gleich oft aus (13 gegen 16, JOB00908).
- **Nicht das Volume:** die volle Kopie auf TSO001 fällt wie das Original auf
  TK5RES aus (8 gegen 9, JOB00914).
- **Nicht die Control Unit:** `cu=3880` gegen `cu=3990` mit der fehlerhaften
  Bibliothek 21 gegen 13 (JOB00916).
- **Nicht ein Hercules-Stand allein:** unter 4.9.1 (TK5-Bundle), 4.10.0
  `59d8981c` (die Stände) und 4.10.0 `a7423980` (Container) gesehen.
- **Nicht TK5 allein:** MVS/CE (IEWFETCH-Stand UZ54723) fällt auch aus, TK5 hat
  UZ41374.
- **Was trennt, ist die Bibliothek:** volle Kopien (544 Member, 210
  Directory-Blöcke, IEMRA ab R53, letzter Textsatz auf der nächsten Spur)
  fallen wie das Original aus, kleine Kopien kaum. Ob die Satzlage oder das
  große Directory zählt, ist offen.
- **Die Rate hängt vom System ab:** m38r etwa zehnmal häufiger als m38l und die
  Container, bei ähnlicher Host-Last. Ursache offen (Hercules-Commit, Container
  gegen nackten Prozess, die übrige Last im MVS).

Auch außerhalb der Probe: `IEA703I 106- F` auf m38b für PL/I-Phasen (IEMRA ×3,
IEMQK, IEMML, IEMED) und MVSMF, auf m38r zweimal für MVSMF in HTTPD (Konsolen-
Logs, Zählung 2026-10-15). Verwandt, nicht im Fetch: `IEB139I I/O ERROR DURING
READ … PROGRAM CHECK` in IEBCOPY auf m38b (JOB01694 unter 4.9.1, JOB01989 unter
4.10.0), Wiederholung jeweils sauber.

## 3. Ein fehlgeschlagener Fetch kostet den Speicher des Moduls, dauerhaft

- In der Probe landet jeder LOAD nach einem FAIL eine Seite höher
  (`0xA6000` → `0xA7000` …): MVS gibt den Speicher des fehlgeschlagenen Fetch
  nicht zurück, auch ohne HTTPD.
- In HTTPD auf m38b: nach einem `106-0F` für MVSMF fehlten 335.872 Bytes
  (82 Seiten, die Textgröße von MVSMF auf 4K-Seiten gerundet) und blieben über
  die restlichen rund 9.000 Requests des Soaks weg.
- Bei einem erfolgreichen Fetch mit anschließendem Abend (S0C4) wurde dagegen
  normal aufgeräumt.

## 4. ERRET-Konvention auf MVS 3.8j, gemessen

- `LOAD`/`LINK` mit ERRET: der Exit bekommt den Completion Code in R1
  (rechtsbündig) und den Reason Code in R15.
- Fehlendes Modul: `IEA703I 806-4`, `R1=00000806 R15=00000004`.
- Fetch-I/O-Fehler: `IEA703I 106-F`, `R1=00000106 R15=0000000F`.
- (Für libc370#553: `__link()` wirft beides heute weg.)

## 5. Hercules 4.9.1 (TK5-Bundle): falsche Modulinhalte ohne jeden Fehler

- Unter dem in TK5 gebündelten Hercules `4.9.1.0-SDL` (GCC 13.3, `-O3
  -march=alderlake`) lieferte der LOAD gelegentlich **erfolgreich** ein falsches
  Image: 31 in 400.000 (JOB00898, 00899), auch auf einer Kopie mit allen
  Sätzen auf einer Spur (JOB00904, 9 in 200.000).
- Immer eine von drei Varianten: der Inhalt eines *späteren* Textsatzes von
  IEMRA steht ab Offset 0.
- Derselbe Stand auf 4.10.0 `59d8981c`: 0 in 400.000 (JOB00905).
- Nicht getrennt: 4.9.1 allein oder 4.9.1 zusammen mit TK5s IEWFETCH (MVS/CE
  lief nie unter 4.9.1).
- Folge: ein TK5-System auf dem gebündelten 4.9.1 kann falschen Code ausführen,
  ohne dass etwas meldet. Kandidaten auf m38b am 2026-10-15: ein S0C4 in MVSMF
  beim Start mit einer "DSA" mitten im Modultext und `IEM3856I COMPILER ERROR,
  PROGRAM CHECK TYPE 1 IN PHASE 'OB'` (Deutung, nicht bewiesen).

## 6. Deutung (nicht belegt)

IEWFETCH patcht sein laufendes Kanalprogramm aus der PCI-Appendage (NOP→TIC).
Kommt der Patch zu spät, liest der Kanal weiter: unter 4.9.1 ohne Fehler
(falscher Satz, BAD), unter 4.10.0 seltener und mit Program Check (106-0F). Die
Fehlerklasse beschreibt APAR OZ81870 ("PCI ROUTINE FAILS ON REDRIVE … IEWFETCH PROCESSES DATA FROM
THE CTL (CTL/RLD) RECORD BEFORE THE ENTIRE RECORD HAS BEEN READ"). Ob die Ursache in IEWFETCH
oder in Hercules' Emulation eines laufend geänderten Kanalprogramms liegt, ist
ohne echte Hardware nicht zu trennen.

## Konsequenzen für Sessions

- `106-0F` nicht als Speichermangel lesen; erst `fn=storage` (oder
  Vergleichbares) ansehen.
- `106-0F` nicht automatisch als Link-List-Problem lesen (MVS-LNK-0001): wenn
  der nächste Aufruf desselben Moduls gelingt, ist es eher dieser sporadische
  Fehler.
- Jeder Fetch kann ihn treffen, und jeder Treffer kostet die Modulgröße bis zum
  Ende des Adressraums. Ein Server, der ein Modul pro Request neu holt, sammelt
  das über die Laufzeit an.
