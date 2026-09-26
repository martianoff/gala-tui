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

// Key-only apps (apps that pass `MyKeyToMsg` to Run / RunWithSub):
val h = NewHarness[Model, Msg](program, MyKeyToMsg, 80, 24)

// Mouse + resize apps (apps that pass MyInputToMsg to RunWithMouse):
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
and apply it in one go. Every harness step is a sealed-type case —
keys, mouse, resize, and direct messages all live in the same script.

```gala
val steps = ArrayOf[harness.HarnessStep[Msg]](
    harness.StepKey(Ev = PlainKey(Char('a'))),
    harness.StepType(Text = "lice"),
    harness.StepKey(Ev = Ctrl(Char('s'))),
    harness.StepClick(X = 40, Y = 10),            // mouse press at (40,10)
    harness.StepScroll(X = 40, Y = 10, Up = false),  // wheel down
    harness.StepResize(W = 100, H = 30),          // window resize
    harness.StepWait(N = 3),                      // tick 3 times
    harness.StepMsg(Msg = SaveAll()),             // skip key decoding,
                                                  //   send a Msg directly
)

// Final session only:
val finalSession = h.RunSequence(steps)
IsTrue(t, finalSession.Contains("Saved"))

// Time-travel — Session after each step:
val trace = h.Trace(steps)
IsFalse(t, trace.Get(0).Contains("Saved"))         // before save
IsTrue(t,  trace.Get(3).Contains("Saved"))         // after Ctrl-S
```

### `RunSequence` + `Snapshot`: the golden-file test pattern

`Snapshot` only makes sense at the *end* of a test script — it's the
"freeze-frame" assertion that goes on the rendered output. Combine it
with `RunSequence` to drive a sequence of inputs and assert the final
buffer matches a fixture string.

```gala
import (
    . "github.com/martianoff/gala-tui"
    "github.com/martianoff/gala-tui/harness"
    . "martianoff/gala/collection_immutable"
    . "martianoff/gala/test"
)

func TestCounterAfterThreePlusses(t T) T {
    val program = Program[CounterModel, CounterMsg](
        Initial = CounterModel(N = 0),
        Update  = (m, msg) => counterUpdate(m, msg),
        View    = (m) => counterView(m),
    )
    val h = harness.NewHarness[CounterModel, CounterMsg](
        program, (ev) => counterKey(ev), 25, 2,
    )
    val final = h.RunSequence(ArrayOf[harness.HarnessStep[CounterMsg]](
        harness.StepType[CounterMsg](Text = "+++"),
    ))
    val want = " Count: 3                " + "\n" +
               " + / - to change         "
    return IsTrue(t, SnapshotsEqual(final.Text(), want))
}
```

When the assertion fails, `SnapshotDiff` produces an actionable
row-level diff:

```gala
val diff = SnapshotDiff(final.Text(), want)
diff match {
    case Some(report) => Println(report)   // human-readable diff
    case None()       => Println("snapshots match")
}
```

`Snapshot` always sees the *post-script* state. To snapshot intermediate
frames, pair `Trace(steps)` with `SnapshotsEqual` per step.

### Mouse + resize via `RunSequence`

Mouse interactions go through the same harness API, but `StepClick` /
`StepScroll` only fire when the harness was built via `NewHarnessFull`
(apps wired to `RunWithMouse`). On a `NewHarness` (key-only) harness they're
silently ignored.

```gala
val final = h.RunSequence(ArrayOf[harness.HarnessStep[Msg]](
    harness.StepKey[Msg](Ev = PlainKey(Tab())),       // shift focus to table
    harness.StepScroll[Msg](X = 0, Y = 0, Up = false), // wheel-down
))
IsTrue(t, final.Model.Cursor > 0)
```

Or chained on the `Session` directly without building an Array:

```gala
val final = h.Start()
    .Press(PlainKey(Tab()))
    .Scroll(0, 0, false)
    .Click(40, 10)
    .Resize(120, 40)
IsTrue(t, final.Model.Cursor > 0)
```

Both forms are equivalent. Use `RunSequence` when the script is
parameterised or driven from a fixture; chain methods when the test is
short and reads better that way.

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

---

# Renderer tests — the house standard

A reducer test proves the model is right. A **renderer test** proves the user
can see it. Every change to a widget's appearance ships at least one.

This section exists because an audit of the library's own suite found the
opposite of what the numbers suggested: 71% of tests never touched a Buffer,
and two widgets with green tests were visibly broken — the tests sampled a
single cell for a whole-row claim, and the sampled cell happened to be one of
the few the bug did not touch.

## Pick the right instrument

| You are asserting | Use | Why |
|---|---|---|
| A **whole frame's** layout — a composition, a modal, a full app view | `Snapshot(w, width, height)` against a literal golden | Catches a column shift anywhere, including cells you weren't thinking about |
| **One row's** content, where the rest of the frame is noise | `SnapshotLines(...).Get(y)` + `Eq` | Stays stable when unrelated rows change |
| **Presence** of a label whose exact column genuinely isn't part of the contract | `RowContains` | The weakest form — see "what makes a bad renderer test" |
| **Colour / attributes** | `SnapshotStyled` for a fixture, or `StyleAt(x, y)` **swept across the region** | Glyph assertions are blind to style, and style is half the UI |
| **Behaviour over time** — keys, clicks, resize, async msgs | `NewHarness(...).Start()` then `.Press` / `.Type` / `.Click` / `.Wait`, then `.Row` / `.Text` / `.Buffer().StyleAt` | The only path that runs `KeyToMsg` and `Cmd` redispatch |

## Sweep the region you make a claim about

This is the rule that matters most, and it is not stylistic.

```gala
// BAD — the comment claims the row, the assertion checks one cell.
// This shape passed for months while the widget was visibly broken.
func TestStatusBarIsCyan(t T) T {
    // Whole row has the cyan background
    return IsTrue(t, ColorEq(buf.StyleAt(10, 0).Bg, BrightCyan()))
}

// GOOD — the claim is "the whole row", so assert the whole row.
func TestStatusBarPaintsEveryCell(t T) T {
    var acc = t
    var x = 0
    for x < 28 {
        acc = IsTrue(acc, ColorEq(buf.StyleAt(x, 0).Bg, BrightCyan()))
        x = x + 1
    }
    return acc
}
```

A single sample is how a fragmented highlight, a background that only reached
the gaps, and a scrollbar thumb that never moved all shipped green.

## Verify the test fails for the right reason

Before calling a behavioural fix done, **reintroduce the bug and watch the
test fail.** A test written against already-fixed code can pass for reasons
that have nothing to do with the fix.

A real example from this repo: a test guarding a scrollbar fix compared whole
rows between two scroll offsets. Those rows always differ — the body text
scrolls — so the assertion passed with the bug fully reintroduced. It had to
assert the bar *column* specifically.

## Keeping golden strings readable

- One `+`-joined literal per row, one row per source line, aligned so the
  literal is a picture of the frame:
  ```gala
  val want = "┌──────────┐" + "\n" +
             "│ Build 12 │" + "\n" +
             "└──────────┘"
  ```
- **Choose the smallest size that exercises the case.** `4x3` and `25x2` are
  right; nobody re-reads an 80x24 golden.
- Trailing padding is real and belongs in the literal. If that makes the
  fixture unreadable, use `SnapshotLines` + a trim helper and say in a comment
  that trailing space is deliberately not asserted.
- Put the `Snapshot` call and the `want` literal adjacent, `got` first, so a
  diff of the test file reads as a diff of the UI.
- Don't write another `rowContains` helper. Use `Session.RowContains` or
  `RowText` from `snapshot.gala`.

## Wide glyphs: `RowText` is not what the terminal shows

`renderText` reserves the trailing cell of a double-width glyph with a space,
and `RowText` reads that cell back literally:

```
│日 本 語 の テ キ ス ト   │      ← what RowText returns
│日本語のテキスト        │      ← what the terminal draws
```

So `RowContains(y, "日本語")` **fails on correctly-rendered output**. For wide
text, assert cells:

```gala
val t2 = Eq(t1, buf.CharAt(1, 0), rune(0x4E2D))
val t3 = Eq(t2, buf.CharAt(2, 0), ' ')          // reserved trail
return Eq(t3, buf.CharAt(3, 0), 'b')
```

## What makes a bad renderer test here

A test is rejected in review if it:

1. **Asserts only that output is non-empty**, or that a length is `> 0`. That
   proves the render didn't crash, nothing more.
2. **Samples one cell for a claim about a span.** See above.
3. **Inspects the Widget AST instead of the Buffer.** A test that
   pattern-matched a `TextWidget`'s content and asserted it contained an OSC-8
   escape passed — while the rendered output showed the escape bytes as
   visible text, because `renderText` drops control characters. Assertions
   must run on a Buffer.
4. **Asserts a tautology.** `Eq(Snapshot(w, width, 1).Size(), width)` cannot
   fail: `Snapshot` walks `0..buf.Width` by construction.
5. **Is one-sided.** `HasSuffix(out, "cccc")` for a "fills the width" claim
   also passes for a layout that dumps everything on the leading edge. Assert
   both ends.
6. **Uses a degenerate fixture** — one-character segments, one-row lists, a
   1x1 buffer — such that the interesting arithmetic is never exercised.
7. **Pins the one input where the arithmetic happens to be exact.** If a
   remainder can be distributed, sweep a range of widths; a single
   hand-picked width lies.
8. **Renders a view that reads the wall clock.** Inject the clock, or assert
   only the cells that don't depend on it, and say so.
9. **Collapses a diff into a boolean.** Prefer `Eq(t, got, want)` over
   `IsTrue(t, SnapshotsEqual(got, want))` — the latter throws away the report
   the helper exists to produce.
