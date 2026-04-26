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

## Charts

| Widget | Signature | Notes |
|---|---|---|
| `Sparkline(values)` | `(Array[int]) Widget` | One-row bar density. |
| `SparklineStyled(values, style)` | `(Array[int], Style) Widget` | …with custom fg/bg. |
| `BarChart(data)` | `(Array[BarChartDatum]) Widget` | Labeled horizontal bars. |
| `LineChart(values)` | `(Array[int]) Widget` | Auto-bounded, sub-cell resolution. |
| `LineChartStyled(values, style)` | `(Array[int], Style) Widget` | Default bounds, explicit style. |
| `LineChartBounded(values, style, bounds)` | `(Array[int], Style, LineChartBounds) Widget` | Explicit `LineChartBounds(Min, Max)`. |
| `LineChartAtHeight(values, style, bounds, rows)` | `(Array[int], Style, LineChartBounds, int) Widget` | Pin the chart to exactly `rows` rows. |
| `MultiLineChart(series, styles)` | `(Array[Array[int]], Array[Style]) Widget` | Overlapping series sharing one Y-axis. |
| `MultiLineChartAtHeight(series, styles, rows)` | `(Array[Array[int]], Array[Style], int) Widget` | Pinned-row variant. |
| `Gauge(percent)` | `(int) Widget` | Horizontal fill bar. |
| `Progress(percent)` | `(int) Widget` | Cell-precise progress bar. |

```gala
BarChart(ArrayOf[BarChartDatum](
    BarChartDatum(Label = "alice", Value = 12),
    BarChartDatum(Label = "bob",   Value = 7),
))
```

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
| `Scrollbar(total, visible, offset)` | `(int, int, int) Widget` | Vertical scroll-thumb track. |
| `ScrollbarStyled(total, visible, offset, style)` | `(int, int, int, Style) Widget` | …with explicit fg/bg. |
| `ScrollableViewport(inner, offset, contentHeight)` | `(Widget, int, int) Widget` | Vertically scroll a tall widget; clip to the area. |

## Markdown & code

| Widget | Signature | Notes |
|---|---|---|
| `MarkdownView(source)` | `(string) Widget` | Headings, bold/italic/code, lists, links, fenced blocks. |
| `HighlightLine(line, lang)` | `(string, string) Widget` | Single-line syntax highlight. Supports gala / go / rust / python / shell. |
| `HyperlinkText(label, url)` | `(string, string) Widget` | OSC 8 hyperlink — clickable in modern terminals. |

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
