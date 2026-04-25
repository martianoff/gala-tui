# Testing gala-tui apps

Three layers, smallest to largest. Pick the one that gives you the
strongest assertion at the lowest setup cost.

| Layer | What runs | Use when |
|---|---|---|
| **`StepAll`** (core) | Update only | Pure reducer logic, message sequences, "does this state machine accept X?" |
| **`Harness` / `Session`** (`harness/`) | Update + key decoding + render | App-level integration tests, "did pressing Ctrl-S clear the dirty flag?" |
| **`Snapshot`** (root) | Render only | Visual regressions; golden-file fixtures |

## Layer 1 — `StepAll`: drive the reducer

Lives in `core.gala`. Smallest API: takes a `Program`, an array of
messages, returns the final model + every emitted command.

```gala
import . "github.com/martianoff/gala-tui"
import . "martianoff/gala/collection_immutable"
import . "martianoff/gala/test"

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

Limitations: the runtime's key-decoding and render passes don't run.
A typo in your `KeyToMsg` won't fail this test. Use Layer 2 for that.

## Layer 2 — `Harness` + `Session`: drive the whole pipeline

Lives in the `harness/` subpackage. Constructs a "fake terminal" that
runs the same `update + redispatch + render` loop the real runtime
uses, but with no background Futures, no IO, and a buffer you can assert on.

### Building a harness

```gala
import (
    . "github.com/martianoff/gala-tui"
    . "github.com/martianoff/gala-tui/harness"
    . "martianoff/gala/collection_immutable"
    . "martianoff/gala/test"
)

val program = Program[Model, Msg](
    Initial = NewModel(),
    Update  = (m, msg) => MyUpdate(m, msg),
    View    = (m) => MyView(m),
)

// Key-only apps (apps that pass `MyKeyToMsg` to Run / RunRich):
val h = NewHarness[Model, Msg](program, MyKeyToMsg, 80, 24)

// Mouse + resize apps (apps that pass MyInputToMsg to RunFull):
val h = NewHarnessFull[Model, Msg](program, MyInputToMsg, 120, 40)
```

### Driving input

Every input method returns a new `Session` — chainable, immutable.

```gala
val s = h.Start()             // initial Session
    .Press(PlainKey(Char('a')))
    .Type("hello")            // each rune as a key press
    .Click(40, 10)            // SGR mouse click (NewHarnessFull only)
    .Scroll(40, 10, true)     // wheel scroll (NewHarnessFull only)
    .Resize(120, 50)          // window resize
    .Send(MyMsg.SaveAll())    // skip key decoding, send a Msg directly
    .Wait(5)                  // tick the runtime N times (drains tickers)
```

### Asserting on the rendered output

```gala
// Whole-buffer matchers
IsTrue(t, s.Contains("Save File"))
IsTrue(t, s.RowEquals(0, " gala-tui demo "))      // row exactly equals
IsTrue(t, s.RowContains(2, "Quit"))               // row contains substring

// Cell-level matchers
val ch = s.CharAt(5, 3)                            // rune at (5, 3)
val st = s.StyleAt(5, 3)                           // Style at (5, 3)
IsTrue(t, s.HasStyleAt(5, 3, (st) => st.Bold))
IsTrue(t, s.HasStyleAt(5, 3, (st) => ColorEq(st.Fg, BrightYellow())))

// Find-by-content
val pos = s.FindCell('▌')                          // Option[Tuple[int, int]]
val rowOpt = s.FindRow("Quit")                     // Option[int]

// Underlying buffer + text
val buf = s.Buffer()                               // *Buffer
val plainText = s.Text()                           // string (no ANSI)
val styledText = s.StyledText()                    // string (with ANSI)
```

### Multi-step tests with `RunSequence` and `Trace`

When a test scripts a sequence of inputs, build an `Array[HarnessStep[T]]`
and apply it in one go:

```gala
val steps = ArrayOf[HarnessStep[Msg]](
    StepKey(Ev = PlainKey(Char('a'))),
    StepType(Text = "lice"),
    StepKey(Ev = Ctrl(Char('s'))),
    StepWait(N = 3),                               // tick 3 times
    StepResize(W = 100, H = 30),
)

// Final session only:
val finalSession = h.RunSequence(steps)
IsTrue(t, finalSession.Contains("Saved"))

// Time-travel — Session after each step:
val trace = h.Trace(steps)
IsFalse(t, trace.Get(0).Contains("Saved"))         // before save
IsTrue(t,  trace.Get(3).Contains("Saved"))         // after Ctrl-S
```

### Debugging

```gala
PrintHarnessFrame(session)
```

Prints the rendered buffer in a Unicode box to stderr — drops it into
test output via `gala test -v` when you can't tell why an assertion is
failing.

## Layer 3 — `Snapshot`: golden-file visual tests

For "does this view render exactly *this* string?" tests. Lives in
`snapshot.gala`.

```gala
import . "github.com/martianoff/gala-tui"

val out = Snapshot(view(model), 40, 4)             // plain text, no ANSI
val want = "  Counter: 7" + "\n" +
           "  +/- to change  ·  q to quit"
IsTrue(t, SnapshotsEqual(out, want))
```

Variants:
- `Snapshot(w, width, height)` — plain text, one line per row.
- `SnapshotStyled(w, width, height)` — full ANSI string. For tests that
  assert on color too.
- `SnapshotLines(w, width, height)` — `Array[string]`, one per row.
- `SnapshotsEqual(got, want)` — boolean.
- `SnapshotDiff(got, want)` — `Option[string]` with a human-readable
  diff when they don't match. Use inside custom assertions.

## Layer 4 — focus + navigation contract tests

Every interactive widget should have at least these three tests. Helpers
live in `harness/focus_test_helpers.gala`.

```gala
import (
    . "github.com/martianoff/gala-tui"
    . "github.com/martianoff/gala-tui/harness"
    . "martianoff/gala/test"
)

// (1) `focused = true` rendering visibly differs from `focused = false`.
func TestMyWidgetFocusedRendersDifferently(t T) T =
    AssertFocusedRendersDifferently(t,
        MyWidgetView(state, false),
        MyWidgetView(state, true),
        40, 6)

// (2) The framework's bright-yellow cursor convention is honored.
func TestMyWidgetFocusedShowsBrightYellow(t T) T =
    AssertFocusedShowsBrightYellow(t,
        MyWidgetView(state, true),
        40, 6)

// (3) The Update API advances the cursor.
func TestMyWidgetArrowDownAdvances(t T) T =
    AssertNavigationAdvancesCursor[MyState](t,
        initialState,
        (s) => MyWidgetUpdate(s, MyMoveNext()),
        (s) => s.Cursor)
```

Adding a new interactive widget? Three lines and the contract is
enforced — see `harness/widget_focus_test.gala` for examples covering
DataTable, SelectListOf, MenuView, CalendarView, Tabs, TreeFocused, and
Input.

## Cell-level matchers worth knowing

| Function | Returns | Use |
|---|---|---|
| `Buffer.CharAt(x, y)` | `rune` | What's rendered at (x, y)? |
| `Buffer.StyleAt(x, y)` | `Style` | Color / bold / reverse / etc. |
| `BufferText(buf, y)` | `string` | The whole row, no ANSI |
| `ColorEq(a, b)` | `bool` | Compare colors (handles indexed + named) |

Combine with the harness:

```gala
// Assert the focused row uses BrightYellow foreground at (1, 7).
IsTrue(t, ColorEq(session.StyleAt(1, 7).Fg, BrightYellow()))

// Assert the help screen has the title "Key bindings" on row 0.
IsTrue(t, session.RowContains(0, "Key bindings"))

// Assert no error-color cells appear.
IsFalse(t, anyCellMatches(session.Buffer(),
    (st) => ColorEq(st.Fg, BrightRed())))
```

## Picking the right layer

| Question your test answers | Layer |
|---|---|
| "Does this reducer transition correctly?" | StepAll |
| "Does pressing Ctrl-S save?" | Harness — needs key decoding |
| "Does the toast disappear after 3 ticks?" | Harness with `StepWait` |
| "Does the spinner advance?" | Harness with `StepWait` + Trace |
| "Does the cursor row turn yellow when focused?" | Harness or focus helpers |
| "Has the layout changed since the last release?" | Snapshot fixtures |
| "Does pressing Tab move focus through every pane?" | Harness with chained `Press(PlainKey(Tab()))` |

Three rules of thumb:
1. **No background Futures, no terminal IO** — every layer above runs purely.
2. **Round-trip the key decoder** wherever you can. A passing reducer
   test that doesn't go through `KeyToMsg` will not catch typos in your
   shortcut spec.
3. **Test what you'd verify by hand.** "Did Ctrl-S clear the dirty
   flag?" is a Harness test. "Did this widget render in the right
   spot?" is a Snapshot test. Don't write hundreds of trivial tests
   when one expressive Harness chain catches the same regression.
