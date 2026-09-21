# Widget catalog

Every widget gala-tui exposes, grouped by purpose. Each entry has the
constructor signature and a one-line example. For deeper docs on any
widget, read the source — every public function has a docstring.

## A note on focus

Every interactive widget ships with a `focused bool = false` last
parameter. Pass `true` (or `m.Focus.IsFocused("paneID")`) when the
widget is the keyboard target — the cursor row gets a `BrightYellow +
Bold + Reverse` accent so the user sees at a glance which widget the
keyboard is driving. Default is `false`, so existing call sites are
back-compatible.

For routing arrow keys to the focused pane, see the [Cookbook §
"Route arrow keys to the focused pane"](COOKBOOK.md#route-arrow-keys-to-the-focused-pane).

To avoid threading the boolean through every widget call, use
`NewFocusBuilder(m.Focus)`:

```gala
val ui = NewFocusBuilder(m.Focus)
val table = ui.DataTable("table", m.BuildsTable)        // pane name first
val tree  = ui.Tree("pipelines", m.Pipelines, m.Cursor)
```

`FocusBuilder` has a method per interactive widget — see
[Cookbook § "Cleaner: drop the per-widget boolean with FocusBuilder"](COOKBOOK.md#cleaner-drop-the-per-widget-boolean-with-focusbuilder).

## Primitives

| Widget | Signature | Notes |
|---|---|---|
| `Empty()` | → `Widget` | Renders nothing. Useful as a placeholder. |
| `Text(content)` | `(string) Widget` | Plain text, default style. |
| `TextStyled(content, style)` | `(string, Style) Widget` | Text with explicit style. |
| `FillCh(ch)` | `(rune) Widget` | Fill the area with a single character. |
| `FillChStyled(ch, style)` | `(rune, Style) Widget` | Filled background block. |
| `Paragraph(content)` | `(string) Widget` | Word-wrapped paragraph. |
| `ParagraphStyled(content, style)` | `(string, Style) Widget` | Same with explicit style. |

```gala
TextStyled(s"  Loading… ${pct}%", DefaultStyle().WithBold().WithFg(BrightCyan()))
```

## Layout

| Widget | Signature | Notes |
|---|---|---|
| `Row(children)` | `(Array[LayoutChild]) Widget` | Horizontal layout solved by Constraint. |
| `Column(children)` | `(Array[LayoutChild]) Widget` | Vertical version of `Row`. |
| `Stack(layers)` | `(Array[Widget]) Widget` | Z-stack — back to front. |
| `Overlay(bottom, top)` | `(Widget, Widget) Widget` | Two-layer alias for Stack. |
| `Padding(n, inner)` | `(int, Widget) Widget` | n-cell padding on all sides. |
| `PaddingHV(v, h, inner)` | `(int, int, Widget) Widget` | Asymmetric padding. |
| `Border(inner)` | `(Widget) Widget` | Default single-line border. |
| `BorderOf(inner, kind)` | `(Widget, BorderKind) Widget` | Pick: `SingleBorder()`, `DoubleBorder()`, `ThickBorder()`, `RoundedBorder()`, `AsciiBorder()`. |
| `Titled(inner, title)` | `(Widget, string) Widget` | Single-line box with a top-left caption. |
| `BorderStyled(inner, kind, style)` | `(Widget, BorderKind, Style) Widget` | Colour the frame itself, independent of its contents. |
| `Block(inner, kind, sides, style, titles)` | `(Widget, BorderKind, BorderSides, Style, Array[BlockTitle]) Widget` | Full form. `AllSides()` / `NoSides()` / `SidesOf(t, r, b, l)` pick edges — a lone left rule is how two panes share one column instead of butting two walls together. Several titles per edge, bucketed by position and alignment. |
| `RowFlex(children, flex, spacing)` | `(Array[LayoutChild], FlexMode, int) Widget` | Distribute slack: `FlexStart` / `FlexEnd` / `FlexCenter` / `FlexSpaceBetween` / `FlexSpaceAround` / `FlexSpaceEvenly`. `FlexLegacy` is the default and matches pre-0.12 behaviour. `ColumnFlex` is the vertical twin. |
| `RowSpaced(children, n)` | `(Array[LayoutChild], int) Widget` | n cells between adjacent children; gaps come out of the axis before the solver runs. |
| `AutoScroll(rows, selected)` | `(Array[Widget], int) Widget` | Stack composed row widgets and scroll so `selected` stays visible. What `SelectList` does, for rows that are more than a label. |

### Rich text

`TextWidget` carries one style for its whole string. `Span` / `Line` /
`RichText` is the three-level model for styling runs within a line.

| Widget | Signature | Notes |
|---|---|---|
| `SpansLine(spans…)` | `(Span…) Widget` | One row of differently-styled runs. |
| `RichTextView(text)` | `(RichText) Widget` | A block of `Line`s, each with its own alignment. |
| `Restyled(inner, f)` | `(Widget, func(Style) Style) Widget` | Render, then rewrite every cell's style in the area — keeps glyphs. This is how a region carries a style. |
| `Highlighted(inner, style)` | `(Widget, Style) Widget` | Flattens the area to `style`. Wins over an outer `.With*`. |
| `Backdrop(inner, bg)` | `(Widget, Color) Widget` | Fills a background only where a cell has not claimed one. |

```gala
SpansLine(
    SpanOf("build "),
    SpanStyled("failed", DefaultStyle().WithFg(BrightRed()).WithBold()),
    SpanOf(" in 2m13s"),
)
```

```gala
Column(ArrayOf[LayoutChild](
    Fixed(3, Border(Text(" header "))),
    Flex(1, Row(ArrayOf[LayoutChild](
        Fixed(20, sidebar),
        Flex(1, body),
    ))),
    Fixed(1, statusBar),
))
```

`LayoutChild` is built with `Fixed(n, w)`, `Flex(weight, w)`, or
`Pct(n, w)`.

## Canvas

Shapes in your own coordinate space, at sub-cell resolution. Braille packs
2×4 dots per cell, so a 40×10 pane addresses 80×40 points.

| Widget | Signature | Notes |
|---|---|---|
| `Canvas(x, y, marker, shapes)` | `(Bounds, Bounds, CanvasMarker, Array[Shape]) Widget` | Full form. Markers: `BrailleMarker` (2×4), `HalfBlockMarker` (1×2), `DotMarker`, `BlockMarker`. |
| `CanvasOf(x, y, shapes)` | `(Bounds, Bounds, Array[Shape]) Widget` | Braille, the usual choice. |
| `XBounds(min, max)` / `YBounds(min, max)` | `(float64, float64) Bounds` | The caller's coordinate range per axis. |
| `PointsOf(xs, ys, style)` | `(Array[float64], Array[float64], Style) Shape` | Build a series from parallel arrays. |

Shapes: `ShapeLine`, `ShapeRect` (outline), `ShapeCircle`, `ShapePoints`,
`ShapeLabel`. Each carries its own `Style`, so one canvas holds a dim grid, a
bright series and a labelled axis. Only lit cells are written, so a canvas
composes over whatever is beneath it.

```gala
CanvasOf(XBounds(-1.0, 1.0), YBounds(-1.0, 1.0), ArrayOf[Shape](
    ShapeCircle(X = 0.0, Y = 0.0, Radius = 0.8, Style = accent),
    ShapeLine(X1 = -1.0, Y1 = 0.0, X2 = 1.0, Y2 = 0.0, Style = dim),
    ShapeLabel(X = -0.9, Y = 0.9, Text = "orbit", Style = dim),
))
```

Y grows **up**, as a plot's does — `Y = 0.0` on `YBounds(0.0, 1.0)` is the
bottom row. Shapes outside the bounds clip; they do not wrap.

## Charts

| Widget | Signature | Notes |
|---|---|---|
| `Sparkline(values)` | `(Array[int]) Widget` | One-row bar density. A value at the series minimum floors to the smallest visible block; an *empty* series still renders blank. |
| `SparklineStyled(values, style)` | `(Array[int], Style) Widget` | …with custom fg/bg. |
| `BarChart(data)` | `(Array[BarChartDatum]) Widget` | Labeled horizontal bars. |
| `LineChart(values)` | `(Array[int]) Widget` | Auto-bounded, sub-cell resolution. |
| `LineChartStyled(values, style)` | `(Array[int], Style) Widget` | Default bounds, explicit style. |
| `LineChartBounded(values, style, bounds)` | `(Array[int], Style, LineChartBounds) Widget` | Explicit `LineChartBounds(Min, Max)`. |
| `LineChartAtHeight(values, style, bounds, rows)` | `(Array[int], Style, LineChartBounds, int) Widget` | Pin the chart to exactly `rows` rows. |
| `MultiLineChart(series, styles)` | `(Array[Array[int]], Array[Style]) Widget` | Overlapping series sharing one Y-axis. |
| `MultiLineChartAtHeight(series, styles, rows)` | `(Array[Array[int]], Array[Style], int) Widget` | Pinned-row variant. |
| `Gauge(percent)` | `(int) Widget` | Horizontal fill bar. Sub-cell precision via partial blocks. |
| `Progress(percent)` | `(int) Widget` | Cell-precise progress bar. |
| `LineGauge(percent)` | `(int) Widget` | One-row gauge captioned with its own percentage: ` 42% ━━━━━━╾──────`. Heavy `━` against light `─` so the split reads without colour, with `╾` where the fill ends mid-cell. Caption is right-aligned in a fixed 4 columns, so the rule's origin holds still as the number grows a digit. |
| `LineGaugeLabeled(label, percent)` | `(string, int) Widget` | Caption of your choosing; `""` gives a bare rule across the row (down to one cell). Too narrow for the caption? The rule takes the row — a clipped caption can read as the wrong number. |
| `LineGaugeStyled(label, percent, filled, unfilled)` | `(string, int, Style, Style) Widget` | Explicit filled/track styles. The caption takes the filled style — it is the value, not chrome. |

```gala
BarChart(ArrayOf[BarChartDatum](
    BarChartDatum(Label = "alice", Value = 12),
    BarChartDatum(Label = "bob",   Value = 7),
))
```

Stacking several `LineGaugeLabeled`s? Captions of different lengths give
every rule a different origin *and* a different length, which is precisely
what stops a column of gauges being comparable by eye. Give the captions a
fixed column of their own instead:

```gala
Row(ArrayOf[LayoutChild](
    Fixed(12, Text("Downloading")),
    Flex(1, LineGaugeLabeled("", pct)),
))
```

**Narrow slots.** Squeezed below its intrinsic width, a widget keeps the part
that still carries information and drops the rest: `ProgressLabeled` drops its
number and keeps the bar, `LineGauge` drops its rule and keeps the caption —
and drops the caption for the rule when the caption would have to be cut. A
*clip* is always signalled (`StringCellEllipsis`'s `…`, `OverflowRow`'s `›`),
because a clipped value can be misread as a shorter one; a *drop* needs no
marker, because an absent rule cannot be mistaken for a short rule.

## Lists & tables

| Widget | Signature | Notes |
|---|---|---|
| `SelectList(items, selected)` | `(Array[ListItem], int) Widget` | Vertical list. Each item carries label + optional hint via `NewListItem(label)`. |
| `SelectListOf(labels, selected)` | `(Array[string], int) Widget` | Convenience over `SelectList` when you only need labels. |
| `Table(data)` | `(TableData) Widget` | Fixed grid; pre-sized columns. |
| `DataTableView(dt)` | `(DataTable) Widget` | Sortable + filterable. State in `DataTable` model — drive with `DataTableUpdate`. |
| `Tree(root)` | `(TreeNode) Widget` | Static collapsible tree. Build with `NewTreeBranch`/`NewTreeBranchExpanded`/`NewTreeLeaf`. |
| `TreeFocused(root, cursor, focused = false)` | `(TreeNode, int, bool) Widget` | Interactive variant — cursor highlight + focus accent. Pair with `TreeFlatRowCount` for clamping and `TreeToggleAt` for expand/collapse. |

```gala
val initial = NewDataTable(
    ArrayOf[string]("Name", "Status"),
    ArrayOf[Constraint](Fill(2), Length(10)),
    ArrayOf[Array[string]](
        ArrayOf[string]("alice", "online"),
        ArrayOf[string]("bob",   "away"),
    ),
)
val dt2 = DataTableUpdate(initial, DTSortBy(0))
RenderTo(DataTableView(dt2), area, buf)
```

## Forms & input

| Widget | Signature | Notes |
|---|---|---|
| `Input(value, cursor, placeholder)` | `(string, int, string) Widget` | Single-line text field; cursor is the byte offset for the caret glyph. |
| `Button(label, focused)` | `(string, bool) Widget` | Reverse style when focused. |
| `FormView(f)` | `(FormState) Widget` | Multi-field form. State in `FormState`. |
| `Spinner(kind, frame)` | `(SpinnerKind, int) Widget` | Pick: `BrailleSpinner()`, `DotsSpinner()`, `PipeSpinner()`, `ArrowSpinner()`. Increment `frame` each tick. |

```gala
val form = NewForm(ArrayOf[FormField](
    FormField(Name = "email", Label = "Email", Required = true),
    FormField(Name = "age",   Label = "Age",   Validator = isNumeric),
))
RenderTo(FormView(form), area, buf)
```

## Modals & overlays

| Widget | Signature | Notes |
|---|---|---|
| `Modal(w, h, body)` | `(int, int, Widget) Widget` | Centered panel with dimmed backdrop. |
| `ModalStyled(w, h, body, backdrop, border)` | | Theme-friendly variant. |
| `ConfirmDialog(title, message, yesFocused)` | `(string, string, bool) Widget` | Yes/No prompt. |
| `AlertDialog(title, message)` | `(string, string) Widget` | OK-only prompt. |
| `Dropdown(d)` | `(Dropdown) Widget` | Trigger + open menu. |

```gala
Stack(ArrayOf[Widget](
    background,
    Modal(40, 8, ConfirmDialog("Deploy?", "This pushes to prod.", true)),
))
```

## Status & notifications

| Widget | Signature | Notes |
|---|---|---|
| `StatusBarView(bar)` | `(StatusBar) Widget` | 3-slot status row (left/center/right). |
| `ToastView(q)` | `(ToastQueue) Widget` | Single toast — most-recent. |
| `ToastStackView(q)` | `(ToastQueue) Widget` | Stack of all queued toasts. |
| `LogPanelView(p)` | `(LogPanel) Widget` | Scrollable log buffer. |
| `LogPanelViewTail(p, n)` | `(LogPanel, int) Widget` | Last n lines only. |

`ToastQueue` and `LogPanel` are pure values — push messages through their
methods, render the result. Both prune on a clock you control.

```gala
val toasts0 = NewToastQueue(5)
val toasts1 = toasts0.PushSuccess("saved", Now(), Seconds(int64(3)))
RenderTo(ToastView(toasts1), area, buf)
```

## Navigation

| Widget | Signature | Notes |
|---|---|---|
| `MenuView(m)` | `(Menu) Widget` | Vertical or horizontal menu — set `Menu.Orientation`. |
| `DropdownView(d)` | `(Dropdown) Widget` | Closed = trigger; open = menu below. |
| `Tabs(titles, bodies, selected)` | `(Array[string], Array[Widget], int) Widget` | Tabbed pane — bodies parallel to titles. |
| `Scrollbar(total, visible, offset)` | `(int, int, int) Widget` | Vertical scroll-thumb track on the right edge. Pass `visible = 0` to derive the viewport from the bar's own area. With nothing to scroll it draws track only, not a full thumb. |
| `ScrollbarStyled(total, visible, offset, style)` | `(int, int, int, Style) Widget` | …with explicit fg/bg. |
| `ScrollbarAt(total, visible, offset, style, orientation)` | `(int, int, int, Style, ScrollbarOrientation) Widget` | Pick the edge: `ScrollbarVerticalRight` / `…Left` / `ScrollbarHorizontalBottom` / `…Top`. |
| `ScrollableViewport(inner, offset, contentHeight)` | `(Widget, int, int) Widget` | Vertically scroll a tall widget; clip to the area. |

## Markdown & code

| Widget | Signature | Notes |
|---|---|---|
| `MarkdownView(source)` | `(string) Widget` | Headings, bold/italic/code, lists, links, fenced blocks. |
| `HighlightLine(line, lang)` | `(string, string) Widget` | Single-line syntax highlight. Supports gala / go / rust / python / shell. |
| `Link(label, url)` | `(string, string) Widget` | OSC 8 hyperlink — clickable in modern terminals. The url rides on the cell's `Style`; the escape is emitted by the buffer writer at the run's boundaries, so the widget's width is the label's width. |
| `HyperlinkText(label, url)` | `(string, string) Widget` | Same as `Link` with a blue default. Prefer `Link` in new code. |
| `Linked(inner, url)` | `(Widget, string) Widget` | Makes a whole composed widget one clickable target — a bordered card, a table row — not just a string. |

```gala
MarkdownView("# Quick start\n\nRun `gala build .` then **enjoy**.")
```

## Compact chrome widgets

Small composable building blocks for headers / footers / status rows.
Each is a thin wrapper over `Text`/`Row` primitives, pulled out so apps
don't re-derive the formatting every time.

| Widget | Signature | Notes |
|---|---|---|
| `Breadcrumb(parts, separator = " › ")` | `(Array[string], string) Widget` | Segment trail. Last segment bright-cyan + bold; earlier segments dim. Empty input → `Empty()`. |
| `BreadcrumbStyled(parts, separator, inactive, active)` | `(..., Style, Style) Widget` | Caller-picked styles per segment. |
| `Tag(label, color)` | `(string, Color) Widget` | Reverse-styled `[label]` status pill. |
| `TagPlain(label, color)` | `(string, Color) Widget` | Flat `[label]` without reverse — for contexts where reverse would clash with row highlight. |
| `KeyHint(spec, description)` | `(string, string) Widget` | Inline `Ctrl+P palette` keybind label — bright-cyan spec, dim description. |
| `KeyHintRow(pairs)` | `(Array[string]) Widget` | Joins `(spec, description)` pairs with ` · ` separators — the canonical bottom-of-screen shortcut strip. |

```gala
val footer = KeyHintRow(ArrayOf[string](
    "Ctrl+P", "palette",
    "Tab",    "cycle focus",
    "q",      "quit",
))
val crumbs = Breadcrumb(ArrayOf[string]("App", "Builds", "#4211"))
val beta = Tag("Beta", BrightYellow())
```

## Status indicators

Transient app state widgets — pair with a `TickSub` so the animation
phases advance.

| Widget | Signature | Notes |
|---|---|---|
| `Loader(text, frame)` | `(string, int) Widget` | "⠋ Loading…" — bright spinner + dim label. |
| `LoaderStyled(text, frame, kind, spinStyle, textStyle)` | | Caller-picked spinner kind + colours. |
| `EmptyState(icon, text)` | `(string, string) Widget` | "📭 No items yet" placeholder; bright icon + dim text. |
| `EmptyStateHinted(icon, text, hint)` | `(string, string, string) Widget` | …plus a dimmed italic hint line below. |
| `Pulse(frame, color)` | `(int, Color) Widget` | " ● " dot pulsing on a 2-phase clock. |
| `PulseFrames(frame, color)` | `(int, Color) Widget` | " ● " dot with a 4-phase fade — smoother. |

```gala
val sub = TickSub[Msg](Interval = Milliseconds(int64(120)),
                       Make = () => Tick())
// ...
val view = Column(ArrayOf[LayoutChild](
    Fixed(1, Loader("Fetching builds…", m.Tick)),
    Fixed(1, Pulse(m.Tick, BrightGreen())),    // "live" indicator
    Fixed(2, EmptyStateHinted("📭", "No matches", "Press / to filter")),
))
```

## Search + diff

| Widget | Signature | Notes |
|---|---|---|
| `SearchInput(query, matched, total)` | `(string, int, int) Widget` | `/  query… (12/45)` — icon + input + result-count badge. Empty query collapses the badge. |
| `SearchInputStyled(query, matched, total, iconStyle, textStyle, badgeStyle)` | | …with caller-picked styles. |
| `MatchSubstring(haystack, needle)` | `(string, string) bool` | Case-insensitive substring predicate, the canonical SearchInput filter. |
| `DiffView(lines)` | `(Array[DiffLine]) Widget` | Line-by-line diff: green `+` for added, red `-` for removed, dim ` ` for context. Empty input → "(no changes)". |
| `DiffViewStats(lines)` | `(Array[DiffLine]) Widget` | DiffView prefixed with a `+N -M ~K` summary row. |

```gala
sealed type DiffLine {
    case DiffContext(Text string)
    case DiffAdded(Text string)
    case DiffRemoved(Text string)
}

val hits = items.Filter((s) => MatchSubstring(s, m.Query))
val view = Column(ArrayOf[LayoutChild](
    Fixed(1, SearchInput(m.Query, hits.Length(), items.Length())),
    Flex(1, SelectListOf(hits, m.Sel)),
))
```

## Themed helpers

These pick fg/bg/border from a `Theme` so you don't have to wire each
widget by hand.

| Widget | Signature |
|---|---|
| `HeadingT(theme, content)` | `(Theme, string) Widget` |
| `AccentT(theme, content)` | `(Theme, string) Widget` |
| `SuccessT(theme, content)` | `(Theme, string) Widget` |
| `WarningT(theme, content)` | `(Theme, string) Widget` |
| `ErrorT(theme, content)` | `(Theme, string) Widget` |
| `MutedT(theme, content)` | `(Theme, string) Widget` |
| `BorderT(theme, inner)` | `(Theme, Widget) Widget` |
| `BackgroundT(theme, inner)` | `(Theme, Widget) Widget` |

Built-in themes: `DefaultTheme()`, `DarkTheme()`, `LightTheme()`,
`HighContrastTheme()`. Roll your own with the `Theme` struct directly.

## Hit-testing & domain helpers

| Widget | Signature | Notes |
|---|---|---|
| `CalendarView(c)` | `(Calendar) Widget` | One-month grid + cursor. |
| `FileBrowserView(b)` | `(FileBrowser) Widget` | Directory listing + breadcrumb. |
| `HelpView(entries)` | `(Array[HelpSpec[T]]) Widget` | Auto-formatted shortcut sheet. |
| `HelpModalView(entries, w, h)` | `(Array[HelpSpec[T]], int, int) Widget` | Centered modal version. |
| `PaletteView(p)` | `(Palette[T]) Widget` | Command-palette body. |
| `PaletteViewAtHeight(p, max)` | `(Palette[T], int) Widget` | Same, capped. |

## Snapshots

For tests, use `Snapshot(widget, w, h)` to render to a plain string and
compare against a fixture. See [GETTING_STARTED.md](GETTING_STARTED.md)
§ 5 for an example.

| Function | Returns |
|---|---|
| `Snapshot(w, w, h)` | `string` (no ANSI) |
| `SnapshotStyled(w, w, h)` | `string` (full ANSI for color assertions) |
| `SnapshotLines(w, w, h)` | `Array[string]` (one line per row) |
| `SnapshotsEqual(got, want)` | `bool` |
| `SnapshotDiff(got, want)` | `Option[string]` (human-readable diff) |

## Inline viewport

By default an app owns the whole terminal on the alternate screen. That is
wrong for a TUI that is part of a command rather than the whole session — a
progress view, a picker, a confirmation — because leaving the alternate
screen erases everything the app displayed.

`InlineBackend(height)` renders into `height` rows directly below the shell
prompt and leaves the final frame on screen when the program exits:

```gala
val _ = RunWithSub[Model, Msg](program, keyToMsg, sub, InlineBackend(5))
```

The viewport is positioned relatively throughout, so the app coexists with
whatever is already on screen and never writes above its own block.

| | `TerminalBackend()` (default) | `InlineBackend(n)` |
|---|---|---|
| Screen | alternate | normal, `n` rows below the prompt |
| Size | whole terminal | terminal width × `n` |
| Repaint | diffed against the previous frame | full |
| On exit | screen restored, output gone | final frame stays in scrollback |

Repaints are full rather than diffed: an inline viewport is a handful of
rows, so the bandwidth argument for diffing does not apply, and a diff in
relative cursor moves is much easier to get wrong than to make fast.

### Printing above the viewport

`PrintAbove(lines…)` is a `Cmd` that puts lines into the scrollback *above*
the viewport, where they stay after the app exits — one line per finished
target while a live progress block stays pinned below it:

```gala
func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] = msg match {
    case TargetDone(name, ms) =>
        (m.Advance(), PrintAbove[Msg](s"✓ ${name} in ${ms}ms"))
    ...
}

// …and it needs the inline backend — the default is the alternate screen.
val _ = RunWithSub[Model, Msg](program, keyToMsg, sub, InlineBackend(3))
```

Writing to stdout yourself cannot do this: the viewport is drawn relative to
the cursor, so a stray write lands inside the frame and the next paint
overwrites it. Going through a `Cmd` also keeps `update()` pure, so a test
asserts the lines with `NewTestBackend` instead of a terminal.

A line printed alongside `QuitCmd` in the same `Batch` still lands — an app
whose last act is to print a summary and exit means both, and the viewport is
repainted on the way out so the final frame survives in the scrollback below
it. On the full-screen backend the lines are dropped: the alternate screen has
no scrollback to insert into, which is the same limitation ratatui's
`insert_before` has.

Each element is one row. A string carrying its own `\n` is split, because in
raw mode a bare newline moves down without returning to column 0 and the text
after it would land mid-row. A line wider than the terminal soft-wraps, which
costs it an extra row but nothing else — the viewport's rows are blanked
before the lines land on them, so a wrapped line cannot weld the old frame's
tail onto its continuation row.

## Testing a run loop without a terminal

`NewTestBackend(width, height, input)` scripts stdin and records everything
written, so the whole loop — parsing, carry-over, click resolution, quit
handling, teardown — can be driven from a test:

```gala
val (backend, st) = NewTestBackend(40, 3, "abc")
val final = Run[Model, Msg](program, keyToMsg, backend)
IsTrue(t, st.Wrote("keys=a,b,c"))
```

`Read` reports end-of-input once the script runs out, so a scripted run
terminates on its own instead of needing a Quit in every fixture.

Use `NewTestBackendChunks(width, height, chunks)` when the split between
reads matters — an escape sequence torn across two reads cannot be expressed
as a single string, because one string always arrives in one read.
