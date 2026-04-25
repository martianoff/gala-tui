# Getting started with gala-tui

Build three small apps from scratch — counter, input form, async fetcher.
Each one introduces one new concept: `Update`, `Sub`, and `Cmd`.

If you already know Bubble Tea or Elm: same architecture, GALA syntax,
sealed-types-everywhere. Skim part 1, then jump to part 3 (async).

## Prerequisites

- A working `gala` binary on `$PATH`. Build from `martianoff/gala` master:
  ```bash
  bazel build //cmd/gala:gala
  cp bazel-bin/cmd/gala/gala_/gala ~/.local/bin/
  ```
- A terminal that supports the ANSI alt screen (any modern macOS / Linux
  terminal; Windows Terminal works).

## 1. Hello, counter

Create a directory `counter/` with two files:

`counter/gala.mod`:
```
module example.com/counter

gala dev
```

`counter/main.gala`:
```gala
package main

import (
    . "github.com/martianoff/gala-tui"
    . "martianoff/gala/std"
)

// ----- Model + Msg -----------------------------------------------------------

struct Model(N int)

sealed type Msg {
    case Inc()
    case Dec()
    case Quit()
}

// ----- Update ----------------------------------------------------------------

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] {
    return msg match {
        case Inc()  => (m.Copy(N = m.N + 1), NoCmd[Msg]())
        case Dec()  => (m.Copy(N = m.N - 1), NoCmd[Msg]())
        case Quit() => (m, QuitCmd[Msg]())
    }
}

// ----- View ------------------------------------------------------------------

func view(m Model) Widget {
    val title = TextStyled(s"  Counter: ${m.N}  ",
        DefaultStyle().WithBold().WithFg(BrightCyan()))
    val hint = TextStyled("  +/- to change  ·  q to quit  ",
        DefaultStyle().WithDim())
    return Column(ArrayOf[LayoutChild](
        Fixed(1, title),
        Fixed(1, hint),
    ))
}

// ----- Key bindings ----------------------------------------------------------

func keyToMsg(ev KeyEvent) Msg {
    if KeyMatches(ev, "ctrl+c") { return Quit() }
    return ev.Key match {
        case Char(c) => charToMsg(c)
        case Esc()   => Quit()
        case _       => Inc()        // any other key bumps the count
    }
}

func charToMsg(c rune) Msg {
    if c == '+' || c == '=' { return Inc() }   // most keyboards put + on shift
    if c == '-'             { return Dec() }
    if c == 'q'             { return Quit() }
    return Inc()
}

// ----- main ------------------------------------------------------------------

func main() {
    val program = Program[Model, Msg](
        Model(N = 0),
        (m, msg) => update(m, msg),
        (m) => view(m),
    )
    val _ = Run[Model, Msg](program, (ev) => keyToMsg(ev))
}
```

Run it:
```bash
gala build ./counter
./counter
```

`+` and `-` change the number. `q` or `Ctrl-C` quits.

### What's going on

- **`Program[M, T]`** is the Elm Triad: `Initial`, `Update`, `View`. The
  runtime owns the loop; you write three pure functions.
- **`Update`** takes the current model and a message, returns the next
  model and a `Cmd`. Always pure.
- **`Cmd[T]`** is data — `NoCmd`, `QuitCmd`, `MsgCmd(t)`,
  `BatchCmd(...)`, `FutureCmd(...)`. The runtime interprets it.
- **`Run`** is the simple keyboard-only entry point. We'll graduate to
  `RunFull` (mouse + resize) and `RunRich` (futures + timers) later.

## 2. Add an input field

Replace `counter/main.gala` with this expanded version that lets the
user type a name and renders a greeting.

```gala
package main

import (
    . "github.com/martianoff/gala-tui"
    . "martianoff/gala/std"
)

struct Model(Name string)

sealed type Msg {
    case TypeChar(C rune)
    case TypeBackspace()
    case Quit()
}

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] {
    return msg match {
        case TypeChar(c) =>
            (m.Copy(Name = m.Name + string(c)), NoCmd[Msg]())
        case TypeBackspace() => {
            val n = RuneCount(m.Name)
            val next = if (n == 0) "" else stringDropLast(m.Name)
            (m.Copy(Name = next), NoCmd[Msg]())
        }
        case Quit() => (m, QuitCmd[Msg]())
    }
}

func view(m Model) Widget {
    val prompt = TextStyled("  Name: ", DefaultStyle().WithBold())
    val typed = TextStyled(m.Name + "▎", DefaultStyle().WithFg(BrightCyan()))
    val hello = if (m.Name == "")
        Text("  (type to set the name)")
    else
        TextStyled("  Hello, " + m.Name + "!", DefaultStyle().WithBold())
    return Column(ArrayOf[LayoutChild](
        Fixed(1, Row(ArrayOf[LayoutChild](
            Fixed(8, prompt),
            Flex(1, typed),
        ))),
        Fixed(1, Text("")),
        Fixed(1, hello),
        Fixed(1, TextStyled("  Esc / Ctrl-C to quit", DefaultStyle().WithDim())),
    ))
}

func keyToMsg(ev KeyEvent) Msg {
    if KeyMatches(ev, "ctrl+c") { return Quit() }
    return ev.Key match {
        case Esc()       => Quit()
        case Backspace() => TypeBackspace()
        case Char(c)     => TypeChar(C = c)
        case _           => TypeChar(C = ' ')
    }
}

// stringDropLast trims one rune off the end of s.
func stringDropLast(s string) string {
    var out = ""
    var keep = RuneCount(s) - 1
    var i = 0
    for _, c := range s {
        if i < keep { out = out + string(c) }
        i = i + 1
    }
    return out
}

func main() {
    val program = Program[Model, Msg](
        Model(Name = ""),
        (m, msg) => update(m, msg),
        (m) => view(m),
    )
    val _ = Run[Model, Msg](program, (ev) => keyToMsg(ev))
}
```

Notice `RuneCount` — gala-tui ships grapheme-aware text helpers so Unicode
input behaves correctly. `string(c)` round-trips a rune into a single-char
string. The cursor `▎` is just a rendered character — no special cursor
API needed.

## 3. Async — fetch a delayed result

The third app simulates a slow API call. While the request is "in
flight", a spinner pulses; when it returns, we render the result.

This needs three new pieces:
- **`AfterDelay(d, () => msg)`** — a `Cmd` that emits `msg` after `d`
  elapses (the callback shape lets the runtime invoke it lazily)
- **`TickSub(Interval = d, Make = () => msg)`** — a `Sub` that fires a
  message every `d` so the spinner animates
- **`RunRich`** — the async-aware runtime that polls futures and tickers

```gala
package main

import (
    . "github.com/martianoff/gala-tui"
    . "martianoff/gala/collection_immutable"
    . "martianoff/gala/std"
    . "martianoff/gala/time_utils"
)

struct Model(
    Tick    int,
    Loading bool,
    Result  string,
)

sealed type Msg {
    case Tick()
    case StartFetch()
    case FetchDone(Body string)
    case Quit()
}

func update(m Model, msg Msg) Tuple[Model, Cmd[Msg]] {
    return msg match {
        case Tick() => (m.Copy(Tick = m.Tick + 1), NoCmd[Msg]())
        case StartFetch() =>
            (m.Copy(Loading = true, Result = ""),
             AfterDelay[Msg](Seconds(int64(2)),
                 () => FetchDone(Body = "  hello from /api ")))
        case FetchDone(body) =>
            (m.Copy(Loading = false, Result = body), NoCmd[Msg]())
        case Quit() => (m, QuitCmd[Msg]())
    }
}

func view(m Model) Widget {
    val title = TextStyled("  Async demo  ",
        DefaultStyle().WithBold().WithFg(BrightCyan()))
    val status = if (m.Loading)
        Row(ArrayOf[LayoutChild](
            Fixed(2, Spinner(BrailleSpinner(), m.Tick)),
            Flex(1, Text(" loading...")),
        ))
    else if (m.Result == "")
        Text("  press SPACE to fetch")
    else
        TextStyled("  result: " + m.Result, DefaultStyle().WithFg(BrightGreen()))
    return Column(ArrayOf[LayoutChild](
        Fixed(1, title),
        Fixed(1, Text("")),
        Fixed(1, status),
        Fixed(1, Text("")),
        Fixed(1, TextStyled("  q quits", DefaultStyle().WithDim())),
    ))
}

func keyToMsg(ev KeyEvent) Msg {
    if KeyMatches(ev, "ctrl+c") { return Quit() }
    return ev.Key match {
        case Char('q') => Quit()
        case Char(' ') => StartFetch()
        case _         => Tick()       // any key just bumps the tick
    }
}

func main() {
    val program = Program[Model, Msg](
        Model(Tick = 0, Loading = false, Result = ""),
        (m, msg) => update(m, msg),
        (m) => view(m),
    )
    // Tick every 100 ms so the spinner animates while we wait for fetch.
    val sub = TickSub[Msg](
        Interval = Milliseconds(int64(100)),
        Make = () => Tick(),
    )
    val _ = RunRich[Model, Msg](program, (ev) => keyToMsg(ev), sub)
}
```

`AfterDelay` returns a `Cmd[Msg]` carrying a `FutureCmd`. The runtime
polls it every loop iteration; when the delay elapses, the future
resolves to `FetchDone(Body = ...)` and the runtime dispatches it
through `update()` like any other message.

`TickSub` returns a `Sub[Msg]` — same idea, but recurring. The runtime
tracks each ticker's next-due time and fires `Make()` on the clock.

## 4. Mouse + resize

For mouse and window-resize support, swap `RunRich` for `RunFull`. The
`makeKeyMsg` parameter becomes `makeInputMsg` and receives an
`InputEvent` (a sealed sum of key/mouse/resize/unknown):

```gala
func inputToMsg(ev InputEvent) Msg = ev match {
    case KeyInput(k)       => keyToMsg(k)
    case MouseInput(m)     => m.Btn match {
        case MouseScrollUp()   => Tick()       // scroll up = bump
        case MouseScrollDown() => StartFetch() // scroll down = fetch
        case _                  => Tick()
    }
    case ResizeInput(_, _) => Tick()
    case UnknownInput()    => Tick()
}

// in main:
val _ = RunFull[Model, Msg](program, (ev) => inputToMsg(ev), sub)
```

That's it — same program, same model, same view; the runtime now also
delivers mouse packets and terminal resize events.

## 5. Testing

You can drive your `Update` with `StepAll` — no terminal involved, no
input parsing — by feeding a list of messages and asserting on the final
model.

```gala
package main

import (
    . "github.com/martianoff/gala-tui"
    . "martianoff/gala/collection_immutable"
    . "martianoff/gala/test"
)

func TestCounterIncrementsTwice(t T) T {
    val program = Program[Model, Msg](
        Model(N = 0),
        (m, msg) => update(m, msg),
        (m) => view(m),
    )
    val (final, _) = StepAll(program, ArrayOf[Msg](Inc(), Inc(), Inc()))
    return Eq(t, final.N, 3)
}
```

For visual regressions, use the `Snapshot` helpers — render to a buffer
and compare against a fixture string:

```gala
val out = Snapshot(view(Model(N = 7)), 40, 4)
// out is a plain text dump, one line per row, no ANSI noise.
val want = "  Counter: 7" + "\n" + "  +/- to change  ·  q to quit"
return IsTrue(t, SnapshotsEqual(out, want))
```

Run all the tests with `gala test ./your-app`.

## Where to go next

- Browse `demo/megademo.gala` — exercises every widget on screen at once
  (palette, datatable, tree, line chart, log drawer, themes, modals,
  toasts).
- Read [STRUCTURE.md](../STRUCTURE.md) for a map of where each piece
  lives in this repo.
- Read the source for the widget you need — every public function has a
  docstring with a usage example.
