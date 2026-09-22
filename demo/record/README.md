# Recording the demo

The README's GIF is produced from a **scripted** session — nobody at the
keyboard, nobody at the mouse. The script is committed, so the demo can be
re-recorded after a UI change instead of being an artifact nobody knows how to
reproduce.

```bash
brew install agg          # once
demo/record/record.sh     # build → drive → render
```

Two files come out, and the split is deliberate:

| File | What it is | Why keep it |
|---|---|---|
| `docs/demo.cast` | the session as timestamped text (asciicast v2) | reviewable in a diff, and re-renderable at any size, speed or theme **without running the app again** |
| `docs/gala-tui-demo.gif` | what the README shows | the picture |

Knobs: `COLS=100 ROWS=30 demo/record/record.sh`, or `GIF=docs/other.gif`.

---

## How a click gets recorded

This is the part that needs explaining, because recording tools replay
keystrokes and have no notion of a click.

gala-tui speaks SGR mouse mode (`mouse.gala`), so a click is **just bytes on
stdin**:

```
ESC [ < 0 ; col ; row M     press   left button at (col, row)
ESC [ < 0 ; col ; row m     release
ESC [ < 32 ; col ; row M    motion with the button held — a drag
ESC [ < 64 ; col ; row M    wheel up      (65 = wheel down)
```

`tools/record/drive.py` opens a pty, runs the app inside it, and writes those
bytes on a schedule — which makes a click exactly as reproducible as a
keystroke. The app cannot tell the difference, because there isn't one: this is
what a terminal sends when you click.

```
drive.py ──► pty ──► ./gala-tui
    │                    │
    │  scripted bytes    │  frames
    │  (keys + mouse)    ▼
    └──────────────► docs/demo.cast ──► agg ──► GIF
```

---

## Editing the tour

`tour.txt` is one action per line; `#` starts a comment.

| Action | Meaning |
|---|---|
| `wait 0.8` | seconds — let the frame settle, and let a viewer read it |
| `key q` | one keystroke. `enter`, `space`, `tab`, `esc`, `backspace`, `up`, `down`, `left`, `right` are spelled out |
| `keys Ctrl+P` | a chord |
| `text hello` | a run of characters |
| `click 52 9` | left click at column 52, row 9 |
| `move 60 11` | motion with the button held (drag) |
| `scroll down 60 11` | wheel at a position (`up` too) |

**Coordinates are 1-based**, the way a terminal reports them, and they are tied
to the layout at a given size — the committed tour was written against 120×36.
If the layout changes, re-check them rather than guessing.

### Finding a coordinate

Record once, pull a frame out, and read the columns off it:

```bash
python3 tools/record/drive.py --script demo/record/tour.txt \
    --cast /tmp/probe.cast --cols 120 --rows 36 -- ./gala-tui
agg /tmp/probe.cast /tmp/probe.gif
ffmpeg -ss 3 -i /tmp/probe.gif -vframes 1 /tmp/frame.png   # a frame at t=3s
```

A click that lands nowhere is silent — the app simply doesn't repaint. The
quickest signal that the tour is hitting something is the byte count: a run
whose clicks land emits several times the output of one whose clicks miss
(212 KB vs 37 KB, when this tour was written).

---

## Troubleshooting

**The app paints nothing and looks hung.** A pty with no `TIOCSWINSZ` is 0×0,
and a TUI asked to paint into nothing emits its enter sequence and not one
frame. `drive.py` always sets the size; anything else driving a TUI must too.

**"app exited before action N".** The driver says which action was in flight
when the app went away. Usually the tour quit it early — a stray `q`, or an
`enter` on a palette entry that turned out to be *Quit*.

**Nothing in the GIF but a shell prompt.** The app probably failed to start;
the cast holds its stderr, so read it: `head -c 400 docs/demo.cast`.

**The GIF looks garbled.** Check whether the *app* is garbled before blaming
the renderer: `agg` replays the byte stream faithfully, so a rendering bug in
the library shows up in the GIF exactly as it would on a terminal. Recording
this demo is how the wide-glyph drift in `Buffer.String` was found.

---

## What the tour deliberately does not show

`PrintAbove` cannot appear in this demo. It writes into the terminal's
scrollback above an inline viewport, and the mega demo is full-screen on the
alternate screen — which has no scrollback. Showing it needs its own short
clip against `InlineBackend`, not a scene in this one.
