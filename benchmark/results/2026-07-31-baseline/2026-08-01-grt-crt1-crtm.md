# Befund: warum ein Modul seine eigene GRT bekommt — und warum das Absicht ist

Quellenstand: `~/repos/mvs`, gelesen am 2026-08-01. Alle Zeilenangaben aus dem
Working Tree.

Zwei Teile: **A** ist im Quelltext direkt belegt. **B** ist eine Ableitung aus A und
sollte auf einem laufenden System bestätigt werden, bevor jemand danach handelt.

---

## A — Belegt

### A1. Die drei Startfiles unterscheiden sich genau in CRT und GRT

| | `@@CRTSET` | `@@GRTSET` | `@@CRTGET` | `@@CRTRES` |
|---|---|---|---|---|
| `@@crt0.asm` | Z. 73 | **Z. 74** | Z. 81 | Z. 211 |
| `@@crt1.asm` | Z. 75 | **Z. 77** | Z. 81 | Z. 213 |
| `@@crtm.asm` | — | — | Z. 54, 106 | — |

`@@crt1.asm:77-78`:

```
         L     R15,=V(@@GRTSET)
         BALR  R14,R15           Anchor a CLIBGRT area as CRTGRT
```

`@@crtm.asm` enthält keine dieser Zeilen. Es *holt* den vorhandenen CLIBCRT und legt
weder CRT noch GRT an — und räumt beim Exit auch keinen ab. Das ist exakt das, was
`startup.md` mit „reuses the caller's runtime" meint.

### A2. `__grtset()` prüft nicht, ob schon eine GRT existiert

`libc370/src/clib/@@grtset.c`:

```c
CLIBCRT *crt = __crtget();
...
CLIBGRT *grt = calloc(1, sizeof(CLIBGRT));
if (grt) {
    ...
    crt->crtgrt = grt;
    ppa->ppagrt = grt;
```

Bedingungslos. Jeder Aufruf ersetzt den GRT-Zeiger des CRT, den `__crtget()`
zurückgibt.

### A3. Die GRT hängt am CRT, und der CRT hängt an der TCB

`__grtget()` ist wörtlich `crt->crtgrt`. `__CRTGET()` sucht in `ppa->ppacrt[]` nach
`crttcb == aktueller TCB` und liefert den **ersten** Treffer (`break`).

### A4. Warum `startup.md:38` („per process / address space") trotzdem stimmt

`__CRTSET()` erbt beim Thread-Start die GRT der Mutter-TCB:

```c
unsigned *otcb = (unsigned*)tcb[0x84/4];   /* OTCB == TCBOTC */
...
if (ppa->ppacrt[n]->crttcb == (void*)otcb) {
    grt = ocrt->crtgrt;
}
...
crt->crtgrt = grt;
```

Und der CTHREAD-Einstieg in `@@crt1.asm:166` ruft **nur** `@@CRTSET`, nicht `@@GRTSET`.
Ein per ATTACH erzeugter Worker erbt also httpds GRT und legt keine eigene an.

**Damit ist G-3 aufgelöst:** „per address space" beschreibt korrekt den Scope, der aus
dem ATTACH-Vererbungspfad folgt. Der Fall, den die Doku nicht abdeckt, ist der
LINK-Fall — ein per LINK SVC auf derselben TCB geholtes Modul mit vollem Startfile
durchläuft `@@GRTSET` und bekommt eine eigene. Kein Widerspruch, eine Lücke.

### A5. Module werden per LINK auf der Worker-TCB geholt

`httpd/src/httplink.c:38` — `rc = __linkds(pgm, dcb, plist, &prc);`, aufgerufen aus
`serve_client()` im Worker-Thread (`httpd/src/httpd.c:655ff`). Kein ATTACH, keine neue
TCB.

### A6. Die crt1-Wahl ist dokumentierte Absicht, kein Versehen

`httprexx/project.toml:16-17`:

> `startup=crt1` for the threading runtime (`@@CRT1`), same as httplua. **The CGI entry
> calls main(); httpd/httpc come from the GRT (grtapp1/grtapp2).**

`httplua/project.toml:20` sagt dasselbe. Der Grund ist der Threading-Runtime — `crt1`
bringt den CTHREAD-Einstieg mit, `crtm` nicht.

Und `cgistart.c` kompensiert die frische GRT bewusst: es schreibt `grt->grtapp1 =
httpd` (Z. 81, 98) und `grt->grtapp2 = httpc` (Z. 86) aus der Parameterliste in die
**neue** GRT.

**Das ist der Kern:** Die Kompensation ist per Konstruktion unvollständig. Zwei Zeiger
werden nachgesetzt, alles andere, was httpd in seiner GRT-WSA hält, ist aus dem Modul
unsichtbar. #109 (userid), #111 (password) und #113 (credential array) sind drei
Instanzen genau dieser Unvollständigkeit — jede einzeln repariert, indem der Zeiger
über den HTTPD-Kontrollblock durchgereicht wird statt über die GRT.

Der etablierte Fix-Pattern ist also richtig. „Nimm `crtm`" wäre der falsche Schluss.

### A7. `crtm` wird im gesamten Ökosystem nirgends verwendet

Über alle `project.toml` in `~/repos/mvs`:

```
    120  startup = "crt1"
      1  startup = "crt0"
      0  startup = "crtm"
```

`crtm.o` wird gebaut (`libc370/build/sdk/crtm.o`), in `startup.md` als *die* richtige
Wahl für LINK/XCTL/LOAD+BALR dokumentiert — und von keinem einzigen Modul gelinkt.

---

## B — Abgeleitet, nicht beobachtet

Aus A1–A5 folgt eine Sequenz, die ich statisch hergeleitet, aber **nicht auf einem
laufenden System nachgewiesen** habe. Sie hängt an drei Details, die belegt sind:
`arrayadd` hängt hinten an (`(*carray)[array->count++] = vitem`, `@@aradd.c`),
`__CRTGET` nimmt den **ersten** Treffer, `__CRTRES` löscht den **ersten** Treffer.

Während ein Modul läuft, hat die Worker-TCB **zwei** CRTs in `ppa->ppacrt[]`:

1. **Thread-Start (ATTACH).** `@@CRTSET` legt CRT_A an, `crttcb` = Worker-TCB,
   `crtgrt` = httpds GRT (via TCBOTC geerbt). Kein `@@GRTSET`.
2. **Modul-LINK, `crt1` Programmeinstieg.** `@@CRTSET` legt CRT_B an — ebenfalls
   `crttcb` = Worker-TCB, ebenfalls `crtgrt` = httpds GRT geerbt — und hängt es
   **hinten** an.
3. **`@@GRTSET` direkt danach.** Es ruft `__crtget()`, das den **ersten** Treffer
   liefert — also **CRT_A**, nicht das gerade angelegte CRT_B. Die frische GRT landet
   damit auf dem **CRT des Workers**. Ab hier liefert `__grtget()` auf dieser TCB die
   Modul-GRT — für Modulcode *und* für httpd-Kernfunktionen, die über die
   HTTPX-Vektortabelle gerufen werden. Das ist die Symptomatik von #109/#111/#113.
4. **Modul-Exit, `@@EXITA` → `@@CRTRES` (`@@crt1.asm:213`).** Gelöscht wird wieder der
   **erste** Treffer — CRT_A — und `free()`d. CRT_B bleibt stehen, mit der in Schritt 2
   geerbten httpd-GRT.
5. **Nach dem Rücksprung** liefert `__crtget()` also CRT_B und damit wieder httpds
   echte GRT.

Wenn das stimmt, folgt daraus dreierlei:

- Der GRT-Zustand erholt sich nach dem Modulaufruf — aber durch Reihenfolgenzufall,
  nicht durch Design.
- Die in Schritt 3 angelegte Modul-GRT wird nie freigegeben, und `ppa->ppagrt` zeigt
  danach weiter auf sie.
- In Schritt 4 wird der CRT freigegeben, den der Worker-Thread bei seinem Start
  angelegt hat, samt `crtsave` und allem, was sonst daran hängt.

**Wie man das in fünf Minuten prüft:** ein `wtof` von `__crtget()` und `__grtget()` an
drei Stellen — im Worker vor `httplink()`, in `cgistart.c` nach `__grtget()`, und im
Worker nach der Rückkehr aus `httplink()` — plus ein `wtodumpf(ppa->ppacrt, …)` an
denselben drei Punkten. Wenn die CRT-Adresse vorher und nachher verschieden ist,
stimmt die Ableitung.

---

## Was daraus für den Benchmark folgt

**G-3 kann geschlossen werden.** Die Auflösung steht in A4 und ist vollständig
quellenbelegt.

**`M1` in Q-06 lässt sich jetzt ohne Behauptung schärfen:**

> The loaded module does not share httpd's writable static area because it is a
> separately linked load module built with a full startfile (`crt0`/`crt1`), which
> calls `__grtset()` and establishes a fresh CLIBGRT. This follows from how the module
> is built, not from a link-line mistake — re-linking it against httpd's objects does
> not merge the two static areas. `cgistart.c` re-seeds only `grtapp1`/`grtapp2` into
> that fresh GRT; everything else httpd holds in its own GRT stays invisible.

**Q-07 steht anders da, als es aussieht.** Es benotet `crtm` als richtige Wahl für ein
per LINK auf derselben TCB geholtes C-Modul. `startup.md` sagt das auch so. Aber
**kein einziges Modul im Ökosystem ist so gebaut** (A7), und für httpds Module wäre es
sogar falsch, weil `crtm` den CTHREAD-Einstieg nicht mitbringt (A6). Die Frage benotet
damit dokumentierte Regel, nicht gelebte Praxis — beides legitim, aber die
Unterscheidung gehört in die KB, sonst schreibt jemand ein Dokument, das der
Codebasis widerspricht.

**Eine neue Frage bietet sich an** (besser als Q-06 in seiner jetzigen Form): warum
sieht ein per HTTPX-Vektor gerufener httpd-Kern eine leere WSA, obwohl Modul und
Server im selben Adressraum *und* auf derselben TCB laufen? Knackige Antwort, und die
Falle („gleiche TCB ⇒ gleiche Runtime") ist die, in die `crtm`s eigene Doku ein
Modell hineinführt.
