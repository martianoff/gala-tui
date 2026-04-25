# gala-tui

A functional, Elm-architecture TUI framework written in **GALA** (which transpiles to Go).

Built ground-up around immutability, exhaustive sealed types, and pure-data widgets.
Includes everything you'd expect from a serious TUI library — and several things you wouldn't.

## Features

**Core architecture**
- `Program[M, T]` — Elm-style Model / Update / View triple
- `Cmd[T]` — pure data side effects (NoCmd / QuitCmd / MsgCmd / BatchCmd / **FutureCmd**)
- `Sub[T]` — subscriptions: KeySub / BatchSub / MapSub / **TickSub** (timer)
- `RunRich` / `RunFull` — async-aware runtimes (futures + tickers + mouse + resize + diff render)

**Layout & rendering**
- Constraint solver (Length, Fill, Percent)
- Row, Column, Stack, Overlay, Padding, Align, Border (5 glyph kinds)
- Differential renderer (`Buffer.DiffString`) — only changed cells go on the wire
- Grapheme-aware cell widths (CJK, emoji, combining marks)

**Widgets**
- Text · Paragraph (word-wrap) · Input · Button · Spinner
- List · Table · **DataTable** (sort + filter + frozen header) · Tree
- Progress · Gauge · Sparkline · BarChart · **LineChart** (sub-cell resolution)
- **Tabs** · **Menu** · **Dropdown** · **Modal** (ConfirmDialog / AlertDialog) · **Scrollbar** · **Viewport**
- **Toast** · **StatusBar** · **LogPanel** · **Form** (multi-field with validators)
- **Markdown** rendering (headings, bold, italic, code spans, links, lists, rules)
- **Command palette** with fuzzy search (à la VS Code Cmd-Shift-P)
- Auto-generated **help screen** from key-binding declarations

**Modern terminal integration**
- SGR mouse mode (`\x1b[?1006h`) — clicks, scroll, drag
- OSC 8 hyperlinks · OSC 52 clipboard · OSC 2 terminal title

**State helpers**
- `ScreenStack` — multi-screen routing with breadcrumbs
- `FocusManager` — pane-cycle ring with Tab/Shift-Tab semantics
- `Animation` — interpolated tweens with 5 easings (Linear, EaseInCubic, EaseOutCubic, EaseInOutCubic, Bounce, StepEasing)
- `Snapshot` testing utilities — render a Widget to a string for golden-file assertions

**Themes**
- Default · Dark · Light · HighContrast (palette + border kind + style overrides)

**Cmd helpers**
- `AfterDelay(d, msg)` · `Async(compute, onResult)` · `AsyncTry(compute, onOk, onErr)`
- `ReadFileCmd(path, …)` · `WriteFileCmd(path, content, …)`

**Key spec DSL**
- `KeyBind[T]("ctrl+c", Quit())` — human-readable shortcut strings, no boilerplate

## Quick demo

```bash
gala build ./demo
./gala_tui.exe
```

The bundled demo is a build-server dashboard that exercises every widget on
screen at once. Keys:

| Key | Action |
|---|---|
| `Ctrl-P` | command palette (fuzzy search) |
| `↑ / ↓` | move selection / cycle screens |
| `Tab` | cycle focus pane |
| `Enter` | confirm |
| `Esc` | close overlay / go back |
| `?` | toggle help (markdown overlay) |
| `F12` / `/` | toggle log drawer |
| `t` | cycle theme |
| `q` / `Ctrl-C` | quit |

## Status

- 430+ tests passing
- Builds against GALA 0.33.0+

Source-code contributions and bug reports welcome.

## License

MIT
