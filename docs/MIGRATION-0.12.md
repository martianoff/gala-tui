# Migrating from 0.11 to 0.12

0.12 is a breaking release. Six types gained cases or fields.

**The good news about the breakage**: GALA verifies exhaustive matches and
requires every field at construction, so **all six break at compile time**.
There is no silent behaviour change hiding in this list — if your code
compiles against 0.12, you have handled them. Work through whatever the
compiler names.

There is a separate list of *behaviour* changes further down, and those do
not announce themselves. Read that section even if your build is green.

---

## Breaking: types that gained cases or fields

### 1. `Widget` — new cases, and existing cases gained fields

New cases: `RichTextW`, `RestyleW`, `AutoScrollW`, `CanvasW`, `CellTextW`.

Existing cases whose arity changed:

| case | was | now |
|---|---|---|
| `BorderWidget` | `(Inner, Kind)` | `(Inner, Kind, Sides, Style, Titles)` |
| `AlignWidget` | `(Inner, Horiz, ChildW, ChildH)` | `(Inner, Horiz, Vert, ChildW, ChildH)` |
| `RowWidget` / `ColumnWidget` | `(Children)` | `(Children, Flex, Spacing)` |
| `ListW` | `(Items, Selected, SelStyle)` | `(Items, Selected, SelStyle, Offset, Direction)` |
| `ScrollbarW` | `(Total, Visible, Offset, Style)` | `(…, Orientation)` |
| `InputW` | `(Value, Cursor, Placeholder, Style, PlaceholderStyle)` | `(…, Focused)` |

If you only ever *built* widgets through the constructors (`Border`, `Row`,
`SelectList`, `Input`, …) rather than the cases directly, most of this costs
you nothing — the constructors kept their signatures and fill the new fields
with the previous behaviour.

You are affected if you pattern-match on `Widget`, which is mainly custom
render walkers and widget-tree transformers.

### 2. `Constraint` — new cases

`MaxLen(n)` and `Ratio(num, den)` joined `Length` / `Percent` / `Fill` /
`MinLen`. Any exhaustive match over `Constraint` needs two more arms.

### 3. `Style` — new field

`Link Option[string]` carries an OSC 8 hyperlink target. If you construct
`Style` directly rather than deriving from `DefaultStyle()`, add it — but
prefer `DefaultStyle().WithLink(url)`.

`StyleEqual` now compares it, so two styles differing only in link target
are no longer equal. That is deliberate: it is what makes the buffer writers
emit the escape at the right boundaries.

### 4. `InputEvent` — new cases

`PasteInput(Content)` and `FocusInput(Gained)` joined `KeyInput` /
`MouseInput` / `ResizeInput` / `UnknownInput`. An app's `func(InputEvent) T`
adapter needs both arms.

They only arrive if you enable the corresponding terminal modes, so an app
that does not can return its no-op message for both.

### 5. `Align` gained a companion, not a case

Vertical alignment is the separate `VAlign` type (`VAlignTop` /
`VAlignMiddle` / `VAlignBottom`), not new cases on `Align`. Existing matches
over `Align` still compile.

### 6. `DataTable.Offset` changed meaning

`0` used to mean "top". It now follows `ListW.Offset`: **`-1` means "track
the cursor"**, and any other value is an explicit first-visible row.

`NewDataTable` sets `-1`, and the sort/filter events reset to `-1`. You are
affected only if you construct `DataTable` literally or set `Offset`
yourself — and if you do, `0` now pins the view to the top instead of
following the selection.

---

## Behaviour changes — these do NOT break the build

Your code will compile and then render differently.

### `.Centered(w, h)` now centres vertically

It never did, despite its name and its doc comment claiming both axes.
Anything relying on the old top-pinning moves down. `AlignedLeft` /
`AlignedRight` are explicitly top-pinned and unaffected; use
`.AlignedAt(horiz, vert, w, h)` for explicit control.

### `.WithDim()` and friends now reach border frames and titles

`restyleLeaves` treats a border's own style, and its titles' spans, as
leaves. Dimming a subtree now dims its frame and caption rather than only
its text.

### A scrollbar with nothing to scroll draws track only

It used to draw a solid full-height thumb — maximum visual weight for the
absence of content, and indistinguishable from a full-length thumb meaning
"you can see all of a scrollable document".

`ScrollPaneView` callers: pass `Visible = 0` to have the renderer derive the
viewport from the bar's own area. Passing `Visible = Total`, which
`ScrollPaneView` itself used to do, means "nothing to scroll".

### `✓ ✕ ⚠ ★ ☑` and friends now measure one cell, not two

Most of the Miscellaneous Symbols and Dingbats blocks are East Asian
*Ambiguous*, which is one column in every Western terminal. Layout
arithmetic around these glyphs shifts by a column — in the right direction.
Genuinely Wide symbols (`✅ ❌ ✨ ⚡ ❗ ⚽`) are unchanged, and six Wide
codepoints just below the blocks (`⌚ ⌛ ⏰ ⏳ ◽ ◾`) now correctly measure two.

### Inputs always draw a caret when focused, and scroll horizontally

An empty focused field used to render its placeholder and nothing else, so a
fresh form showed no indication of which field had the keyboard. Long values
used to freeze at the first visible characters with the caret gone.

Both are fixed, and `TextAreaView` inherits the scrolling.

### `LiftKeysToInput` / `LiftKeysToInputScroll` take a paste handler

Both gained a `pasteToMsg func(string) T` parameter, second in the list:

```gala
LiftKeysToInput[Msg](keyToMsg, (s) => Paste(Text = s), NoOp(), NoOp())
LiftKeysToInputScroll[Msg](keyToMsg, (s) => Paste(Text = s),
                           ScrollUp(), ScrollDown(), NoOp(), NoOp())
```

`LiftKeysToInputPaste` is gone — it is now just `LiftKeysToInput`.

This breaks at compile time, which is the point. Bracketed paste is on by
default, on the argument that GALA's exhaustiveness check makes a swallowed
paste impossible: every match on `InputEvent` has to name `PasteInput`.
These lifts *are* such a match, and they answered `fallback` on the app's
behalf — so an app built on the documented lift silently stopped receiving
pasted text the moment the mode went on, with nothing at compile time to
say so. The handler is required so the decision sits where the default's
reasoning assumes it does.

### A filtered `DataTable` says so, on its rule row

A table with an active filter used to be pixel-identical to one without:
same header, same rule, fewer rows and nothing to say why. Scroll away
from the row you were looking at and the pane reads as "this is the
dataset" — the one reading that is false.

The horizontal rule under the header now carries `─ 2 of 4 · query` while
a filter is active, and is drawn unbroken otherwise. It goes on the rule
rather than on a row of its own so turning a filter on never changes the
table's height or pushes a row out of view.

The count leads the query deliberately: on a table too narrow for the
whole label, the part that survives is the part that says a filter is on
and how much is hidden.

### `Alt+[` and `Alt+O` no longer swallow the next keystroke

A bare `ESC [` or `ESC O` decodes as `Esc` consuming one byte, not as a
truncated sequence waiting for more.

Those two byte pairs are exactly what an xterm-family terminal sends for
Alt+[ and Alt+O under `metaSendsEscape`. Treating them as incomplete waits
for a completion that never arrives, and the *next* keystroke is absorbed
into the pending sequence — Alt+O then `k` decoded as the single SS3
sequence `ESC O k`, and the `k` was gone.

A CSI whose body has started (`ESC [ 1 5`) still waits, so split sequences
are unaffected. That is the right line because a terminal emits a sequence
in one write: it can only be torn across two reads when it is longer than
the read buffer, and at 8 KiB the only thing that long is a paste.

### Table columns are separated by a blank column, charged to the row

`Table` and `DataTable` rows are now laid out with one column of row
`Spacing` between cells. Previously each cell reserved its own separator
internally, which quietly shortened every declared width: a `Length(5)`
column showed four characters, so `"Alice"` rendered as `"Ali…"` in a
column sized to hold it.

Charging the row instead takes the gap from the slack the layout solver
was going to distribute anyway. Declared widths are honoured in full, and
two columns whose values exactly fill them still get separated — that pair
used to collide into one token (`Alice` + `Bobby` → `AliceBobby`).

Practical consequence: a table needs `columns + (columns - 1)` cells of
width to show every column at its declared size. In a pane too narrow for
that, `Fill` columns shrink first and `Length` columns hold — the same
order as before, one column later. Values that no longer fit are cut with
a `…` rather than clipped, so a truncated cell is visible as truncated.

### Selection highlights span the whole row

Menu, Palette, Table, DataTable and Tree highlights used to fragment into
chips wherever a layout left a gap. They now cover the row, including
inter-column padding and the tail past the last column.

Practical consequence: a focused and an unfocused selection are now equally
heavy, differing only in foreground. If your app renders two selectable
panes side by side, consider giving the unfocused one a lighter style.

### `StatusBarView` and `BackgroundT` actually paint their area

Both used `Overlay(fill, content)`, so their colour survived only on cells
no text touched. They now restyle after drawing. `BackgroundT` fills only
where a cell has not claimed its own background, so a coloured child keeps
its colour.

### `DataTable` scrolls, and its click payloads are bound to rows

`Offset` was never read; the body emitted every row and let the renderer
clip, so a cursor past the bottom vanished.

**The one that can break working code**: chaining
`.OnDoublePickRow(n, …)` onto a table slices the table's *whole* area from
its top, so region 0 landed on the header and every dispatched index came
out **offset by the header and rule**. If your app compensated for that
shift, it is now wrong in the opposite direction. Use
`DataTableViewInteractive` (or `FocusBuilder.DataTableInteractive`), which
binds all three contracts per row.

Also: `OnPickRow(dt.Rows.Length(), …)` counted *unfiltered* rows. Use
`VisibleRowCount(dt)` if you still need a count of your own.

### Hyperlinks are real now

`Link(label, url)` used to concatenate OSC 8 escapes into the widget's
content string. The renderer dropped the zero-width ESC and painted the rest
as visible text, so the label came out as
`]8;;https://example.com\label]8;;\`, the terminal never received a
hyperlink, and the widget claimed 42 columns for a 10-column label.

`HyperlinkText(label, url)` discarded its `url` entirely.

Both now work. If you worked around the old behaviour — laying out around
the inflated width, or avoiding `Link` — you can stop.

### `Gauge` draws a track; chart minima are visible

`Gauge(0)` rendered nothing at all. A series minimum rendered as a blank
cell, so a flat series was an empty panel and a dip punched a hole in a
line. An *empty* series still renders blank — that distinction is the one
that matters.

### `Progress` does not render a percentage, and now says so

Two doc comments promised `[████░░░░]  pct%`; the renderer never emitted a
number. `Progress` stays a bar and its doc is corrected. Use
`ProgressLabeled` for the labelled form — it is a separate widget because a
bar's width is load-bearing and spending five columns on text would resize
every `Progress` already in a `Row`.

---

## What did not change

The Elm core — `Program`, `Cmd`, `Sub`, `Run` / `RunRich` / `RunFull` — is
untouched, as are the `state/` helpers, the `harness/` testing API, and
every widget constructor's signature.
