# gala-tui — Claude Code instructions

## Look at the output before calling a rendering change done

A green suite is not evidence that this library renders correctly. Most tests
here assert on a `Buffer`'s cells or on an escape string, and a rendering
defect can satisfy both: the bytes are right read on their own, and only a
terminal's cursor state makes them land wrong.

So for any change to `buffer.gala`, `widget.gala`, a widget's renderer, or
anything that emits escapes, **record the demo and look at it**:

```bash
demo/record/record.sh          # build → drive the scripted tour → render the GIF
```

Then open `docs/gala-tui-demo.gif`, or pull a frame:

```bash
ffmpeg -i docs/gala-tui-demo.gif -vf "fps=2" /tmp/f/%03d.png
```

For a widget in isolation, regenerate its picture instead — faster, and the
diff is text:

```bash
gala build ./tools/widgetshots
./gala-tui | python3 tools/widgetshots/split.py   # docs/img/*.svg
gala build ./demo                                  # the generator took the name back
```

### Why this is worth the minutes

Three defects were found this way and by nothing else: `Buffer.String`
separating full-width rows with a bare `\n` (which drifted every later row one
column left and read as doubled text), `MultiLineChart` rendering one series
however many it was given, and `Modal` erasing the screen it was asking about.
All three had passing tests over them.

### When a frame looks wrong, emulate before blaming the renderer

Do not read a cast as text. Stripping the escapes and concatenating what is
left shows overlapping repaints as doubled glyphs that no terminal would ever
display — that artefact cost an hour of chasing a bug that was not there.
Replay it instead:

```python
import json, pyte                      # pip install pyte
s = pyte.Screen(120, 36); st = pyte.Stream(s)
for line in open("docs/demo.cast").read().splitlines()[1:]:
    t, kind, data = json.loads(line)
    if kind == "o" and t <= 22.0:      # the moment you care about
        st.feed(data)
print("\n".join(s.display))
```

That is the ground truth for what a terminal would put on screen. If the
emulator disagrees with the GIF, the bug is in the renderer, not the recording.

### Then pin it with a test that could have failed

A test that asserts on the output string cannot catch a cursor-state bug.
Replay the renderer's own output through a terminal model instead — see
`fullwidth_wrap_test.gala`, which models the deferred-wrap flag. Before
committing, revert the fix and confirm the new test actually fails.

## A new widget is not done until it is in the demo and the docs

Adding a widget means three commits' worth of work, not one:

1. **The widget**, with tests.
2. **The demo** — a screen in `demo/megascreens.gala` that uses it, a beat in
   `demo/record/tour.txt` that reaches it, and a re-record
   (`demo/record/record.sh`). A widget the tour never reaches is one nobody can
   watch working, and it is also the only place a rendering defect shows up.
3. **The docs** — an entry in `docs/WIDGETS.md` *and* the example in
   `tools/widgetshots/catalogue.gala` so the section's picture includes it.
   If it is not in the catalogue it has no picture.

Do not merge a widget with any of the three missing. The demo is how the last
release's rendering bugs were found; the catalogue is what keeps the docs'
pictures from going stale.

## Other conventions

- `gala build` names its output after the module, so `./demo` and anything
  under `tools/` both write `./gala-tui`. It is a build artifact and is
  gitignored — never commit it.
- Regenerate Bazel files with `bazel run //:gazelle` after adding a `.gala`
  file. `gala test` globs the directory while Bazel uses explicit `srcs`, so
  CI can pass while Bazel is broken.
- `demo/`, `examples/`, `harness/` and `tools/` are excluded from the Bazel
  build on purpose; the library plus `state/` is the published surface.
