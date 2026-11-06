# Wally ISPF 2.2: dynamic areas and field attributes, measured

Date: 2026-11-06. System: MVS/CE with ISPF `V2.2.000` (Wally McLaughlin), 3278 model 2 and a larger screen. Found while building an ISPF dialog in C with `AREA(DYNAMIC)`. Measured by decoding the 3270 data stream (`mbt test --tso -v`), not by reading the screen. Colors are visible only in the stream or by eye, a test on the screen text cannot see them.

## An attribute at the end of a line of the panel body is not sent

Panel line, 80 wide, `+` in the last column:

```
%COMMAND INPUT ===>_ISFCMD      / /%SCROLL ===>~ISFS+
```

The stream holds `SF` at 1,0, 1,19, 1,62 and 1,74, and none at 1,79. Same result with the last character defined as `TYPE(DATAOUT)` and as `TYPE(OUTPUT)`.

Consequence when a dynamic area follows on the next line and its rows carry no attribute of their own: the input field of the line above runs on over the rows. Measured: typing past the scroll field landed in the first row of the area. The rows also have that field's high intensity (`SF C8`).

IBM's ISPF on MVS/SP behaves differently with the same panel layout: the cursor stops at the end of the field. That was seen on the screen; its data stream was not read.

## An attribute in the last column of a dynamic area is sent

With the whole command row inside the area, and an attribute byte in the last position of that row of the buffer, the stream holds `SF 60` at 1,79: protected, low intensity. The rows below are then protected and show all 80 columns.

So a line that must end in an attribute belongs into the area. The fields of that row then have to be filled and read back by the program: `TYPE(DATAIN)` bytes come back in the area variable. The cursor is set with `.CURSOR` on the area and `.CSRPOS`.

Not checked: whether ISPF's own commands such as `SPLIT` still work when the panel has no ordinary input field for the command line.

## A row without an attribute gets the color of the last field before the area

ISPF writes `SA` orders at the start of every such row: `SA 41 00`, `SA 42 F2`. The color (`F2`, red) was that of the last field before the area, not that of an attribute byte in an earlier row of the area. An attribute in the first row (`SF 60`, then `SA 42 F1`) changed that row only as to color, the next row came with `F2` again.

`COLOR(BLUE)` on the area attribute replaces it: `# AREA(DYNAMIC) EXTEND(ON) SCROLL(ON) COLOR(BLUE)` gives `SA 42 F1` on every row. `INTENS(LOW)` on the area attribute did not change the stream.

## Two dynamic areas in one panel

A panel with a second, one-line `AREA(DYNAMIC)` in the command row gave `DISPLAY` RC 20 (`ISPF SERVICE ERROR DISPLAY`). One attempt, one panel; the second area may not be what ISPF objected to.

## What works

Measured with a program under `SELECT PGM() NEWAPPL()`, no command table in `ISPTLIB`:

- `AREA(DYNAMIC) EXTEND(ON) SCROLL(ON)` fills the screen. `LVLINE` gave 22 on 24 lines, where the area started on line 3.
- The area works on a larger screen: 40 lines of data on a 43-line terminal.
- PF7, PF8, PF10 and PF11 come back as `ZVERB` `UP`, `DOWN`, `LEFT`, `RIGHT` (`VCOPY`), `ZVERB` is blank after Enter, and PF3 is `DISPLAY` RC 8.
- ISPF does not read the scroll amount of a panel field for a dialog like this: `ZSCROLLA` stayed `PAGE` and `ZSCROLLN` `0024` whatever was typed, so the program reads the field itself.
- `.CURSOR` and `.CSRPOS` return the field and the position, inside the area too.
- `TYPE(DATAIN)` bytes typed in the area come back in the variable, at their positions.
- `VDEFINE` of a buffer of width times rows is enough for the area.

## Source

Probe and panels: project `sdsf`, commits `4989211` (probe branch) and `3929ba4`.
