# 2026-10-17 — ECO-0004 (Cross-AS-POST): drei Lesungen aus IEAVSY50, Messung ausstehend

Rest des Items `2026-10-17-oftpsvc-review-vier-beobachtungen.md`. Die anderen
drei Beobachtungen sind am 2026-10-18 eingepflegt (`MVS-PROT-0001`, `ECO-0009`,
ein Abschnitt in `ECO-0008`); dieser Punkt bleibt liegen.

**Status 2026-10-18, Entscheidung der libc370-Sitzung (Mikes Ruf):** `ECO-0004`
wird **nicht** geändert, bevor das auf MVS gemessen ist. Was unten steht, ist
IBMs Kommentarblock in `IEAVSY50` (Input- und Exit-Notizen) plus Codelesung,
keine Messung. Die libc370-Sitzung baut eine autorisierte Probe, die R0-R15 mit
Markern lädt, den Branch-Entry-XMPOST absetzt und berichtet, welche Register
zurückkommen; danach kommen Jobnummern und Ergebnis hierher. Eine einmal
eingetragene Fassung dieser Sätze stand kurz in `ECO-0004` und ist
zurückgenommen worden (Commit am selben Tag) — nicht erneut eintragen, solange
die Messung aussteht.

Berührt in `ECO-0004` den Satz „Only R13 is preserved across the call" (dort
`status: source`, belegt aus `@@xmpost.c`, also aus dem Aufrufer).

---

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

