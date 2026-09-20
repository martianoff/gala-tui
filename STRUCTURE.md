# gala-tui — file map

The framework lives in a single `gala_tui` package because the GALA transpiler
currently panics on library-with-subpackage layouts. Files are organized by
concern below; a future transpiler release should let us split this into
real subpackages (`core/`, `widget/`, etc.).

## Core (Elm-architecture types)
- `core.gala` — `Program`, `Cmd[T]` (incl. `FutureCmd`), `IsQuit`, `PendingMsgs`, `PendingFutures`, `PollFutures`, `StepAll`
- `subs.gala` — `Sub[T]` (KeySub / BatchSub / MapSub / TickSub), `DispatchKey`, `CollectTickers`, `DispatchDueTicks`

## Layout & rendering primitives
- `layout.gala` — `Constraint` sealed (Length / Percent / Fill / MinLen /
  MaxLen / Ratio), `Solve`, `FlexMode`, `VAlign`
- `buffer.gala` — `Cell`, `Rect`, `Buffer`, `String()`, `DiffString`,
  `RestyleRegion`
- `style.gala` — `Style` struct + fluent builders, SGR rendering, OSC 8 link
- `color.gala` — `Color` sealed (DefaultColor / NamedColor / Indexed / RGB) + 16 named-color helpers
- `theme.gala` — `Theme` palette + Default/Dark/Light/HighContrast presets + themed widget helpers
- `runewidth.gala` — grapheme-aware cell widths (CJK, emoji, combining, and
  the East-Asian-Ambiguous distinction)
- `text.gala` — `Span` / `Line` / `RichText`: per-run styling within a line

## Widget framework
- `widget.gala` — the `Widget` sealed type, `RenderTo` walker, intrinsic-size helpers, `Tabs` helper
- `fluent.gala` — chainable widget methods (`.Padded`, `.Bordered`, `.Centered`, `.AsFixed`, `.WithFg`, …)
- `interactive.gala` — `ListItem`, spinner kinds, gauge / progress helpers
- `advanced.gala` — `Table`, `Tree`, `BarChart`, `Sparkline`

## High-level widgets
- `canvas.gala` — `Canvas`: shapes in the caller's coordinate space at
  sub-cell resolution (braille 2x4, half-block, dot, block)
- `linechart.gala` — `LineChart`, `MultiLineChart` with sub-cell block resolution
- `markdown.gala` — `MdBlock` / `MdInline` parser + `MarkdownView`
- `palette.gala` — fuzzy-search command palette with `FuzzyScore`
- `datatable.gala` — sort + filter + frozen-header DataTable
- `form.gala` — `FormField` + `FormState` with validators + view
- `menu.gala` — `Menu` / `Dropdown` (vertical + horizontal, disabled rows skip)
- `modal.gala` — `Modal`, `ConfirmDialog`, `AlertDialog`
- `toast.gala` — `Toast` / `ToastQueue` + `StatusBar`
- `logpanel.gala` — bounded `LogPanel` ring + view
- `help.gala` — auto-help screen from `HelpSpec[T]` array

## State helpers
These live in the `state/` subpackage, imported as
`github.com/martianoff/gala-tui/state`.
- `state/router.gala` — `ScreenStack` (Push/Pop/Replace/Reset/Breadcrumb)
- `state/focus.gala` — `FocusManager` (Tab cycle ring with disabled-skip semantics)
- `state/animation.gala` — `Animation`, `Easing` sealed (Linear / cubic / Bounce / Step), tween helpers
- `state/click_region.gala`, `state/focus_router.gala` — click and focus routing

## Input
- `input.gala` — `Key` / `KeyEvent` / `ParseKey` (ANSI/VT100 decoder), plus the
  kitty keyboard protocol's `CSI … u` form
- `mouse.gala` — SGR mouse parser, `InputEvent` sum (Key / Mouse / Resize /
  Paste / Focus / Unknown)
- `keyspec.gala` — string key DSL (`"ctrl+c"` → predicate), `KeyBind`, `KeyMatches`

## Runtime
- `runtime.gala` — `Run`, `RunRich`, `RunFull` (raw mode + alt-screen + diff render + Future polling + tick scheduling + mouse + resize)
- `terminal_ext.gala` — OSC 8 hyperlinks, OSC 52 clipboard, OSC 2 title
- `cmd_helpers.gala` — `AfterDelay`, `Async`, `AsyncTry`, `ReadFileCmd`, `WriteFileCmd`

## Demo apps (callable from main packages)
- `showcase_app.gala` — system-monitor dashboard demo
- `megademo.gala` — build-server dashboard exercising every feature
- `demo/main.gala` — runnable wrapper that calls `RunMegaDemo()`

## Testing utilities
- `snapshot.gala` — `Snapshot`, `SnapshotStyled`, `SnapshotLines`, `SnapshotDiff`

## Test files
Every `*.gala` has a sibling `*_test.gala` (or two — `widget_test.gala` covers widgets,
`render_test.gala` covers `RenderTo`, etc.). 436 tests across 30+ test files.
