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
screen at once. Below: five frames captured directly from `MegaView` via
the `Snapshot` helper. The actual demo is in color and animates; these
are plaintext-only so they fit in a README.

### Overview screen

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⛩   gala-tui build server    overview             ⠋  active: 2  tick: 0  #4211 0%               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
╭──────────────────────────╮╭──────────────────────────────────────────────────────────────────────╮
│  Nav                     ││ Build Duration (last 40)                                             │
│   Overview               ││▂█▇▇▇▇▇▇▇▇▇▇▇▆▆▆▆▆▆▆▆▆▆▆▅▅▅▅▅▅▅▅▅▅▅▄▄▄▄▄                              │
│   Builds                 │╰──────────────────────────────────────────────────────────────────────╯
│   Pipelines              │╭──────────────────────────────────────────────────────────────────────╮
│   Logs                   ││ Load Average (5-min ticks)                                           │
│   Help                   ││ ▁   ▆    ▂   ▇    ▂   █    ▃                                         │
│                          ││ █   █▄   █   █▅   █▁  █▆   █▂                                        │
│  Throughput (7d)         ││ █▇  ██▃  ██  ██▄  ██  ██▅  ██                                        │
│ backend  ███████████████ ││ ██▆ ███▂ ██▇ ███▃ ███ ███▃ ██                                        │
│ frontend █████████▊      ││ ███▅████ ███▅████▁███▆████▂██                                        │
│ infra    █████▎          ││                                                                      │
│                          │╰──────────────────────────────────────────────────────────────────────╯
│                          │╭──────────────────────────────────────────────────────────────────────╮
│                          ││ Recent Builds                                                        │
│ ▼ Pipelines              ││ #4211  feat/async  Running  00:02:14                                 │
│   ▼ backend              ││ #4210  fix/race  Succeeded  00:01:47                                 │
│     • unit-tests         ││ #4209  main  Succeeded  00:03:22                                     │
│     • integration-tests  ││ #4208  feat/mega-dashboard  Running  00:00:43                        │
╰──────────────────────────╯╰──────────────────────────────────────────────────────────────────────╯
 focus: sidebar   theme: dark                 ^P palette   ^/ logs   ?  help   Tab cycle   q quit
```

### Builds screen — sortable, filterable DataTable with tabs

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⛩   gala-tui build server    overview › builds    ⠋  active: 2  tick: 0  #4211 0%               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
╭──────────────────────────────────────────────────────────────────────────────────────────────────╮
│  Running  Succeeded  Failed                                                                      │
│ #      Branch                            Status     Duration  Author                             │
│ ──────────────────────────────────────────────────────────────────────────────────────────────── │
│ #4211  feat/async                        Running    00:02:14  alice                              │
│ #4208  feat/mega-dashboard               Running    00:00:43  max                                │
│                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
 focus: sidebar   theme: dark                 ^P palette   ^/ logs   ?  help   Tab cycle   q quit
```

### Pipelines — collapsible Tree

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⛩   gala-tui build server    overview › pipelines ⠋  active: 2  tick: 0  #4211 0%               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
╭──────────────────────────────────────────────────────────────────────────────────────────────────╮
│ ▼ Pipelines                                                                                      │
│   ▼ backend                                                                                      │
│     • unit-tests                                                                                 │
│     • integration-tests                                                                          │
│     • lint                                                                                       │
│   ▶ frontend                                                                                     │
│   ▼ deploy                                                                                       │
│     • staging                                                                                    │
│     • prod                                                                                       │
│                                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
 focus: sidebar   theme: dark                 ^P palette   ^/ logs   ?  help   Tab cycle   q quit
```

### Command palette (Ctrl-P) — fuzzy search

```
                    ┌──────────────────────────────────────────────────────────┐
                    │ > Type a command…                                        │
                    │──────────────────────────────────────────────────────────│
                    │ Go to Overview                                       Nav │
                    │ Go to Builds                                         Nav │
                    │ Go to Pipelines                                      Nav │
                    │ Show Help                                           View │
                    │ Toggle Log Drawer                                   View │
                    │ Cycle Theme                                         View │
                    │ Deploy to Staging                                 Deploy │
                    │ Deploy to Prod                                    Deploy │
                    └──────────────────────────────────────────────────────────┘
```

### Confirm dialog (`d` key) — Tab toggles Yes / No

```
                         ┌────────────────────────────────────────────────┐
                         │  Confirm action                                │
                         │                                                │
                         │ Deploy to Prod? Tab to switch, Enter to        │
                         │ commit, Esc to cancel.                         │
                         │                [ Yes ]  [ No ]                 │
                         └────────────────────────────────────────────────┘
```

### Keys

| Key | Action |
|---|---|
| `Ctrl-P` | command palette (fuzzy search) |
| `↑ / ↓` | cycle screens (overview ↔ builds ↔ pipelines ↔ logs); on builds screen, moves the row cursor |
| `PgUp / PgDn` | scroll the log drawer when it's open |
| `End` | jump to the latest log entry |
| `Tab` | cycle focus pane; in the confirm modal, flips Yes ↔ No |
| `Enter` | confirm; in the confirm modal, picks the focused button |
| `Esc` | close overlay / go back |
| `?` | toggle help (markdown overlay) |
| `/` | toggle log drawer |
| `t` | cycle theme (default → dark → light → high-contrast) |
| `c` | copy the selected build row to clipboard |
| `d` | open the deploy-to-prod confirm dialog |
| `q` / `Ctrl-C` | quit |
| Mouse wheel | scroll up/down in the focused list/table |

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) — build a counter, an input form, and a fetcher app from scratch
- [Widget catalog](docs/WIDGETS.md) — every widget the framework ships, grouped by purpose
- [Cookbook](docs/COOKBOOK.md) — confirm-on-quit, debounced search, virtualized lists, draggable splitters, async fan-out
- [Testing](docs/TESTING.md) — `StepAll` / `Harness` / `Snapshot` and the focus-contract helpers
- [Project structure](STRUCTURE.md) — where each file lives in this repo

## Examples

Small, focused, single-file apps that show one feature without the noise of
the full demo:

- [`examples/counter/`](examples/counter/main.gala) — the smallest possible
  gala-tui app. One field, three messages, `+`/`-` to mutate, `q` quits.
  Read end-to-end in 30 seconds.
- [`examples/clickable_list/`](examples/clickable_list/main.gala) — mouse +
  keyboard on a 4-item nav list. Click any row OR press `↑`/`↓`+Enter; both
  paths produce the same model. Demonstrates `RunSimpleWithMouse`,
  `SelectListOfPick`, and `KeyMatchesAny` in <90 lines.
- [`examples/custom_widget/`](examples/custom_widget/main.gala) — author
  your own widget (a clickable star-rating row) with its own event
  vocabulary. Shows the recommended composition pattern: take typed
  callbacks, wrap internally with `Clickable[T]`, callers never see the
  wrap.

## Status

- 564 tests passing
- Builds against GALA 0.34.1+

Source-code contributions and bug reports welcome.

## License

APACHE 2.0
