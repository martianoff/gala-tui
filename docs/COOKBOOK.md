# gala-tui cookbook

Patterns that come up often. Each recipe shows the smallest code that
solves the problem; copy, adapt, ship.

If you haven't read [GETTING_STARTED.md](GETTING_STARTED.md) yet, do
that first — these recipes assume you know what `Program`, `Cmd`, `Sub`,
and `Update` are.

## Recipes

1. [Confirm before quit](#confirm-before-quit)
2. [Debounced search](#debounced-search)
3. [A scrollable, virtualized list](#a-scrollable-virtualized-list)
4. [A clock](#a-clock)
5. [Run multiple async tasks in parallel](#run-multiple-async-tasks-in-parallel)
6. [Catch a panic from a background task](#catch-a-panic-from-a-background-task)
7. [Fan a single key into multiple submodules](#fan-a-single-key-into-multiple-submodules)
8. [Save / restore window state on quit](#save--restore-window-state-on-quit)
9. [A draggable horizontal splitter](#a-draggable-horizontal-splitter)
10. [Test an Update without booting a terminal](#test-an-update-without-booting-a-terminal)
11. [Route arrow keys to the focused pane](#route-arrow-keys-to-the-focused-pane)
12. [Visible focus on every interactive widget](#visible-focus-on-every-interactive-widget)

---

## Confirm before quit

Catch the quit message, show a modal, and only really quit on the
second confirmation.

```gala
sealed type Msg {
    case TryQuit()
    case ConfirmQuit()
    case CancelQuit()
    case ...
}

struct Model(Confirming bool, /* ... */)

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] = msg match {
    case TryQuit() =>
        if (m.Confirming) (m, QuitCmd[Msg]())
        else (m.Copy(Confirming = true), NoCmd[Msg]())
    case ConfirmQuit() => (m, QuitCmd[Msg]())
    case CancelQuit()  => (m.Copy(Confirming = false), NoCmd[Msg]())
    // ...
}

func view(m Model) Widget {
    val base = mainView(m)
    if m.Confirming {
        return Stack(ArrayOf[Widget](
            base,
            Modal(40, 6, ConfirmDialog("Quit?", "Unsaved changes will be lost.", true)),
        ))
    }
    return base
}
```

Bind `q` and `Ctrl-C` both to `TryQuit()` so neither one bypasses the
confirm prompt. `Esc` while `Confirming` returns `CancelQuit()`.

## Debounced search

Don't fire a query on every keystroke. Instead, after each keystroke
schedule a `Cmd` for 300 ms in the future and only fire the query if no
newer keystroke arrives by then. The simplest way is to remember the
keystroke's "generation" — increment on each `TypeChar`, then ignore
late-firing search messages whose generation is stale.

```gala
struct Model(
    Query string,
    Gen   int,            // increments on every keystroke
    Hits  Array[string],
)

sealed type Msg {
    case TypeChar(C rune)
    case TypeBackspace()
    case Search(Gen int)  // fires from AfterDelay; gen lets us drop stale
    case GotResults(Gen int, Hits Array[string])
}

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] = msg match {
    case TypeChar(c) => {
        val q   = m.Query + string(c)
        val gen = m.Gen + 1
        (m.Copy(Query = q, Gen = gen),
         AfterDelay[Msg](Milliseconds(int64(300)), () => Search(Gen = gen)))
    }
    case TypeBackspace() => /* same shape as above */
    case Search(g) =>
        if (g != m.Gen) (m, NoCmd[Msg]())               // stale — drop
        else (m, runQuery(m.Query, g))
    case GotResults(g, hits) =>
        if (g != m.Gen) (m, NoCmd[Msg]())
        else (m.Copy(Hits = hits), NoCmd[Msg]())
}

func runQuery(q string, gen int) Cmd[Msg] =
    Async[Msg](
        () => doSearch(q),
        (hits) => GotResults(Gen = gen, Hits = hits),
    )
```

Generation-based debounce composes with any async backend; the same
trick works for live-validation forms, autocomplete, and "save on stop
typing".

## A scrollable, virtualized list

Wrap a tall widget in `ScrollableViewport(inner, offset, contentHeight)`.
Drive `offset` from your model — clamp on update, paint on view.

```gala
struct Model(Items Array[string], Sel int, Top int)

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] = msg match {
    case Down() => {
        val sel = clampInt(m.Sel + 1, 0, m.Items.Length() - 1)
        val top = scrollToShow(sel, m.Top, viewportRows)
        (m.Copy(Sel = sel, Top = top), NoCmd[Msg]())
    }
    case Up() => /* same, with -1 */
    // ...
}

func view(m Model) Widget {
    val full = SelectListOf(m.Items, m.Sel)
    return ScrollableViewport(full, m.Top, m.Items.Length())
}

func scrollToShow(sel int, top int, rows int) int =
    if (sel < top) sel
    else if (sel >= top + rows) sel - rows + 1
    else top
```

For very large lists (>10k items), don't pass them all into
`SelectListOf` — slice your model into a window of `viewportRows` items
yourself and pass that. The runtime won't render rows outside the
viewport, but it does walk the array building the widget.

## A clock

Use a `TickSub` to fire a message once per second. The `View` reads
the time from the model and renders.

```gala
sealed type Msg {
    case Tick(Now Instant)
    // ...
}

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] = msg match {
    case Tick(now) => (m.Copy(Now = now), NoCmd[Msg]())
    // ...
}

func main() {
    val sub = TickSub[Msg](
        Interval = Seconds(int64(1)),
        Make = () => Tick(Now = Now()),
    )
    val _ = RunWithSub[Model, Msg](program, (ev) => keyToMsg(ev), sub)
}
```

`Now()` is from `martianoff/gala/time_utils`. The runtime polls the
ticker between stdin reads, so the clock advances even while the user
isn't typing.

## Run multiple async tasks in parallel

Emit a `BatchCmd` containing several `FutureCmd`s (or use the
`Async`/`AsyncTry` helpers, which produce one). The runtime polls all
pending futures every loop iteration; whichever resolves first is
dispatched first.

```gala
case StartFanOut() => (m.Copy(Loading = true), Batch[Msg](
    Async[Msg](() => fetchUsers(),    (xs) => GotUsers(Users = xs)),
    Async[Msg](() => fetchProjects(), (xs) => GotProjects(Projects = xs)),
    Async[Msg](() => fetchHealth(),   (h)  => GotHealth(H = h)),
))
```

The `Got*` arms each update one chunk of the model. When all three
have arrived, you can flip `Loading = false` — track a counter or
inspect the model fields.

## Catch a panic from a background task

Use `AsyncTry` instead of `Async`. It takes both an "ok" and an "err"
callback and routes panics through the err path automatically.

```gala
case StartImport() =>
    (m.Copy(Importing = true),
     AsyncTry[Msg, ImportResult](
        () => parseHugeCsv(m.Path),
        (result) => ImportOk(R = result),
        (errMsg) => ImportFailed(Msg = errMsg),
    ))
```

The `() => parseHugeCsv(...)` runs as a background `Future[T]` on the
runtime's `ExecutionContext`; if it panics, the recovered message becomes
the `errMsg` argument to your err callback. Your `Update` handles
`ImportFailed` like any normal message.

## Fan a single key into multiple submodules

Use `BatchSubs` to compose subs and `MapSubs` to lift child messages
into parent messages.

```gala
sealed type Msg {
    case AppKey(K KeyEvent)
    case ChildA(C ChildAMsg)
    case ChildB(C ChildBMsg)
}

func main() {
    val subA = MapSubs(
        OnKey[ChildAMsg]((ev) => childAKey(ev)),
        (ca) => ChildA(C = ca),
    )
    val subB = MapSubs(
        OnKey[ChildBMsg]((ev) => childBKey(ev)),
        (cb) => ChildB(C = cb),
    )
    val sub = BatchSubs(ArrayOf[Sub[Msg]](subA, subB))
    // ...
}
```

Each keystroke becomes both a `ChildA(...)` and a `ChildB(...)` —
useful when you want a global keymap to coexist with a focused-pane
keymap, both seeing every key.

## Save / restore window state on quit

You don't get a teardown hook from the runtime, but `Update` is the
only place state changes — so persist on every meaningful change. To
avoid file IO on every keystroke, debounce as in the search recipe.

```gala
case Resize(w, h) =>
    (m.Copy(Width = w, Height = h),
     WriteFileCmd[Msg]("~/.myapp/state.json",
         marshalState(m), 0644,
         (_) => SavedState(),
         (e) => SaveFailed(Msg = e)))
```

To restore at startup, do the read in `main` before constructing the
program:

```gala
val savedJson = readFileOrEmpty("~/.myapp/state.json")
val initialModel = unmarshalStateOr(savedJson, defaultModel())
val program = Program[Model, Msg](initialModel, /* ... */)
```

`readFileOrEmpty` is yours to write; `os.ReadFile` from the Go stdlib
works fine.

## A draggable horizontal splitter

Track the split column in the model. On left-mouse-press inside the
splitter row, enter a "dragging" state; on mouse motion, update the
split position; on release, leave dragging.

```gala
struct Model(SplitCol int, Dragging bool)

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] = msg match {
    case MouseDown(x, y) =>
        if (y == splitRowY(m)) (m.Copy(Dragging = true), NoCmd[Msg]())
        else (m, NoCmd[Msg]())
    case MouseMove(x, _) =>
        if (m.Dragging) (m.Copy(SplitCol = clampInt(x, 10, 80)), NoCmd[Msg]())
        else (m, NoCmd[Msg]())
    case MouseUp() => (m.Copy(Dragging = false), NoCmd[Msg]())
}

func view(m Model) Widget = Row(ArrayOf[LayoutChild](
    Fixed(m.SplitCol, leftPane),
    Fixed(1, FillCh('│')),
    Flex(1, rightPane),
))
```

Drive these messages from your `MegaInputToMsg`-style adapter — match
on `MouseInput(m)` and emit `MouseDown(m.X, m.Y)` / `MouseMove(...)` /
`MouseUp()` based on `m.Pressed` and `m.Btn`.

## Test an Update without booting a terminal

`StepAll` drives a `Program` through a list of messages and returns
the final model + commands emitted. No stdin, no background Futures.

```gala
func TestIncrementsThenQuits(t T) T {
    val program = Program[Model, Msg](
        Model(N = 0),
        (m, msg) => update(m, msg),
        (m) => view(m),
    )
    val (final, cmds) = StepAll(program, ArrayOf[Msg](Inc(), Inc(), Quit()))
    val t1 = Eq(t, final.N, 2)
    return IsTrue(t1, cmds.Exists((c) => IsQuit(c)))
}
```

For visual regressions: render `view(model)` to a string with `Snapshot`
and compare against a fixture. See [GETTING_STARTED.md § 5](GETTING_STARTED.md#5-testing).

## Route arrow keys to the focused pane

Apps with multiple focusable panes (sidebar / data table / log drawer /
modal buttons / ...) all face the same problem: an arrow key means
something different to each pane. Hand-rolling the switch on every
update is error-prone — and makes it easy to leave a pane with no
handler at all (the bug that made arrow keys "do nothing" on the
demo's table view for one whole release).

Use `FocusManager.Route[T]` instead. Pass an array of `(paneID, handler)`
cases and a fallback. The first case whose pane matches the
FocusManager's current pane fires; the fallback runs if nothing matches.

```gala
import . "github.com/martianoff/gala-tui"
import "github.com/martianoff/gala-tui/state"

func arrowDown(m AppModel) AppModel =
    m.Focus.Route[AppModel](ArrayOf[state.FocusedCase[AppModel]](
        state.OnPane[AppModel]("sidebar", () => moveSidebar(m, +1)),
        state.OnPane[AppModel]("table",   () => moveTableCursor(m, +1)),
        state.OnPane[AppModel]("drawer",  () => scrollDrawer(m, +1)),
    ), m)   // fallback: unchanged model when no pane matches
```

Each handler is a thunk so closures capture whatever they need. The
result type `T` is whatever the caller wants — `AppModel`, `AppMsg`,
`Tuple[AppModel, Cmd[AppMsg]]`, etc.

For the simpler "is THIS one pane focused?" case, use
`FocusManager.When[T]` instead:

```gala
val onEsc = m.Focus.When[AppModel](
    "drawer",
    () => m.Copy(ShowDrawer = false),
    m,
)
```

The naming convention (`Pane = "sidebar"`) is just a string — it must
match the pane IDs you registered with `state.NewFocusManager(...)`.

## Visible focus on every interactive widget

Every interactive widget ships with a `focused bool = false` parameter
that brightens the cursor row when keyboard focus is on that widget:

```gala
val isFocused = m.Focus.IsFocused("table")

val table = DataTableView(m.BuildsTable, isFocused)
val list  = SelectListOf(m.Items, m.Sel, isFocused)
val tree  = TreeFocused(m.Pipelines, m.Cursor, isFocused)
val menu  = MenuView(m.Menu, isFocused)
val cal   = CalendarView(m.Cal, isFocused)
val files = FileBrowserView(m.Browser, isFocused)
val form  = FormView(m.Form, isFocused)
val tabs  = Tabs(titles, bodies, m.Tab, isFocused)
val input = Input(m.Value, m.Cursor, "type here", isFocused)
val drop  = DropdownView(m.Drop, isFocused)
val pal   = PaletteView(m.Palette, isFocused)   // defaults to true — palette is modal
```

Default `false` keeps existing call sites working. When `focused = true`,
the cursor row uses `BrightYellow + Bold + Reverse` so the user sees at
a glance which widget the keyboard is driving.

### Cleaner: drop the per-widget boolean with `FocusBuilder`

Threading `m.Focus.IsFocused("...")` through every widget call is
repetitive — and gets the pane name wrong silently if you typo. Use
`NewFocusBuilder(m.Focus)` to fold the lookup into each widget call.
The pane name moves to the front, the boolean disappears:

```gala
val ui = NewFocusBuilder(m.Focus)
return Row(ArrayOf[LayoutChild](
    Fixed(20, ui.SelectListOf("sidebar", m.NavItems, m.NavSel)),
    Flex(1,  ui.DataTable("table", m.Table)),
))
```

Methods on `FocusBuilder` mirror every interactive widget — pane name
first, then the widget's own arguments:

| FocusBuilder | Equivalent raw call |
|---|---|
| `ui.DataTable("table", dt)` | `DataTableView(dt, ui.IsFocused("table"))` |
| `ui.SelectListOf("nav", labels, sel)` | `SelectListOf(labels, sel, ui.IsFocused("nav"))` |
| `ui.Tree("pipelines", root, cursor)` | `TreeFocused(root, cursor, ui.IsFocused("pipelines"))` |
| `ui.Menu("file-menu", m)` | `MenuView(m, ui.IsFocused("file-menu"))` |
| `ui.Tabs("tabs", titles, bodies, sel)` | `Tabs(titles, bodies, sel, ui.IsFocused("tabs"))` |
| `ui.Calendar("date", c)` | `CalendarView(c, ui.IsFocused("date"))` |
| `ui.FileBrowser("files", b)` | `FileBrowserView(b, ui.IsFocused("files"))` |
| `ui.Form("form", f)` | `FormView(f, ui.IsFocused("form"))` |
| `ui.Input("query", v, cursor, "type…")` | `Input(v, cursor, "type…", ui.IsFocused("query"))` |
| `ui.Dropdown("dd", d)` | `DropdownView(d, ui.IsFocused("dd"))` |

For widgets without a dedicated method (`PaletteView[T]` because it's
generic), fall back to `ui.IsFocused(pane)` and call the bare
constructor:

```gala
val pal = PaletteView[AppMsg](m.Palette, ui.IsFocused("palette"))
```

### Combine with `m.Focus.Route` for the full pattern

```gala
// Update side — arrows route to the focused pane.
func arrowDown(m AppModel) AppModel =
    m.Focus.Route[AppModel](ArrayOf[state.FocusedCase[AppModel]](
        state.OnPane[AppModel]("sidebar", () => moveSidebar(m, +1)),
        state.OnPane[AppModel]("table",   () => moveTable(m, +1)),
    ), m)

// View side — every interactive widget reflects current focus.
func view(m AppModel) Widget {
    val ui = NewFocusBuilder(m.Focus)
    return Row(ArrayOf[LayoutChild](
        Fixed(20, ui.SelectListOf("sidebar", m.NavItems, m.NavSel)),
        Flex(1,  ui.DataTable("table", m.Table)),
    ))
}
```

That's the entire keyboard-and-visual focus contract: `m.Focus.Route(...)`
in update, `NewFocusBuilder(m.Focus)` + a method per widget in view.

## Click any list / menu / table row

Most apps want every row of a list-shaped widget to be clickable —
"click row 3 = navigate to row 3 + Enter on it". The framework
bakes this contract into each interactive widget's click-aware
sibling constructor:

```gala
val nav = ui.SelectListOfPick[Msg](
    "sidebar", labels, sel,
    (i) => OnRowClicked(Idx = i),
)
```

`SelectListOfPick` (and its siblings `SelectListPick`,
`DataTableViewClick`, `TreeFocusedClick`, `MenuViewClick`,
`TabsClick`, `ButtonClick`, `DropdownViewClick`) wrap the widget
internally with `ClickableRows[T]` / `Clickable[T]` so each row
registers its actual rendered rectangle with the runtime's
`HitRegistry`. On a left-click the runtime queries the registry
*first* and dispatches the matching row's payload before the
user's `inputToMsg` ever runs.

Pair it with the "click = select + Enter" pattern from the demo:

```gala
case OnRowClicked(idx) =>
    (jumpToRow(m.Copy(Sel = idx)), NoCmd[Msg]())   // select first, then jump
```

Visibility is automatic: widgets that aren't part of the current
view tree don't register hits. Clicking the y-coordinates where a
sidebar would render — while a different screen is active — is
inert by construction. No manual gating required.

For widgets the framework doesn't ship (or for click contracts the
built-in `*Click` siblings don't cover) reach for the underlying
`Clickable[T]` and `ClickableRows[T]` primitives directly. See the
next section for the full author-your-own-widget recipe.

## Author your own widget with its own events

The framework's interactive widgets — `Button`, `SelectList`, `Tabs`,
`DataTableView`, `MenuView`, `Tree`, `Dropdown` — each have a
click-aware sibling (`ButtonClick`, `SelectListPick`, `TabsClick`,
`DataTableViewClick`, `MenuViewClick`, `TreeFocusedClick`,
`DropdownViewClick`) that bakes the click contract into the
constructor. Same pattern works for widgets you author yourself: pass
a typed callback and wrap internally with `Clickable[T]` /
`ClickableRows[T]`. Users of your widget never see the wrap.

Example — a "rating" widget that exposes a single `OnSet(score)`
event. Each star is a clickable cell; clicking the third star
dispatches `OnSet(3)`.

```gala
struct Rating(Score int, Max int)

func RatingView[T any](
    r Rating,
    OnSet func(int) T,                 // user defines the event vocab
) Widget {
    val cells = arrayRange(1, r.Max + 1).Map((score) => {
        val glyph = if (score <= r.Score) "★" else "☆"
        val cell  = TextStyled(" " + glyph + " ", DefaultStyle())
        // Bake the per-star click into the widget itself — caller
        // never wraps with Clickable.
        return Fixed(3, Clickable[T](cell, OnSet(score)))
    })
    return Row(cells)
}
```

Call site:

```gala
val stars = RatingView[Msg](
    m.Rating,
    OnSet = (score) => RateMovie(Score = score),
)
```

Same pattern for any number of events:

```gala
func KanbanView[T any](
    board Kanban,
    focused bool = false,
    OnCardClick   func(int, int) T,        // (col, row)
    OnColumnDrop  func(int, int) T,        // (fromCol, toCol)
    OnAddCard     func(int) T,
    OnCardDelete  func(int, int) T,
) Widget = ...
```

Each event becomes a constructor parameter, the widget assembles its
inner tree with `Clickable*` wraps where appropriate, and every call
site stays a single non-nested expression.

### When to reach for `Custom`

If your widget can't be expressed by composing existing primitives —
e.g., a pixel-level chart, a custom border, anything that wants to
write directly into the `Buffer` — use `Custom(minW, minH, render)`.
The `render` closure receives the rendered area, the `Buffer`, and
the live `HitRegistry`, so you can paint anything *and* register
your own click hits with `hits.Register(rect, payload)`:

```gala
func HistogramView[T any](
    buckets Array[int],
    OnBarClick func(int) T,
) Widget = Custom(40, 8, (area, buf, hits) => {
    val barWidth = area.Width / buckets.Length()
    var i = 0
    val n = buckets.Length()
    for i < n {
        val barRect = Rect(
            X = area.X + i * barWidth,
            Y = area.Y,
            Width = barWidth,
            Height = area.Height,
        )
        drawBar(buckets.Get(i), barRect, buf)
        if hits != nil {
            hits.Register(barRect, OnBarClick(i))
        }
        i = i + 1
    }
})
```

Same payload-erasure rule as the built-ins: the `OnBarClick(i)` value
is type `T`, the registry stores it as `any`, the runtime restores
the type when it dispatches the click. You never see `any` at the
call site.
