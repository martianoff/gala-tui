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

### On Windows: through WSL

The driver needs a POSIX pty (`pty.fork`, `TIOCSWINSZ`), which Windows does
not have, so the whole pipeline runs inside WSL against the checkout under
`/mnt/c`. One-time setup inside WSL (Ubuntu 22.04 shown):

```bash
mkdir -p ~/.local/bin          # ~/.profile puts it on PATH for login shells
# gala: the same version as gala.mod asks for
curl -sSLo ~/.local/bin/gala \
  https://github.com/martianoff/gala/releases/download/0.80.0/gala-linux-amd64
# Go, which gala build drives: the version in go.mod
curl -sSL https://go.dev/dl/go1.25.5.linux-amd64.tar.gz | tar -C ~/.local -xz
ln -sf ~/.local/go/bin/go ~/.local/bin/go
# agg: the musl build — the gnu one needs glibc 2.38, newer than 22.04 ships
curl -sSLo ~/.local/bin/agg \
  https://github.com/asciinema/agg/releases/download/v1.9.0/agg-x86_64-unknown-linux-musl
chmod +x ~/.local/bin/gala ~/.local/bin/agg
# python3 is already there; pyte for replaying casts, ffmpeg for frames
sudo apt-get install -y python3-pyte ffmpeg
```

Then, from PowerShell in the repo:

```powershell
powershell -File demo/record/record.ps1                  # 120x36
powershell -File demo/record/record.ps1 -Cols 100 -Rows 30
```

`record.ps1` is `wsl --cd <repo> bash -lc demo/record/record.sh` with the knobs
passed through. It builds a Linux `./gala-tui` in the checkout (gitignored,
next to any `gala_tui.exe`). The first build downloads Go modules into WSL and
takes a couple of minutes; after that a recording is about a minute and a half.

The `.sh` and `.py` files are pinned to LF in `.gitattributes`: with
`core.autocrlf=true` they would otherwise check out as CRLF, and bash inside
WSL fails on `set -euo pipefail\r`.

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

### Order is part of the script

The tour visits every screen, because a widget it never reaches is a widget
nobody can see working. That constrains the order: a sidebar click navigates,
and the sidebar is only rendered on the screens that include it (overview,
charts, forms, data, review). Builds and pipelines hand the main pane the whole
width, so the tour reaches them through the command palette and leaves with
`esc`. Clicking where the nav *would* be on those screens does nothing at all,
which is the hit registry working as designed — and a silent way for a tour to
go wrong, since the app just keeps painting the screen it was already on.

The other ordering constraint is the forms screen. A letter typed there is
text, not a shortcut, so `t`, `/`, `?` and `q` only do their global jobs
elsewhere. The tour therefore does its theme/log/help/quit run after it has
left the form.

### Finding a coordinate

Record once, pull a frame out, and read the columns off it (on Windows, in a
`wsl` shell):

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

To check *what* a frame actually showed rather than how many bytes it took,
replay the cast through a terminal emulator instead of looking at the GIF:

```python
import json, pyte                      # pip install pyte
s = pyte.Screen(120, 36); st = pyte.Stream(s)
for line in open("docs/demo.cast").read().splitlines()[1:]:
    t, kind, data = json.loads(line)
    if kind == "o" and t <= 22.0:      # the moment you care about
        st.feed(data)
print("\n".join(s.display))
```

That is the ground truth for what a terminal would put on screen, and it is how
the deferred-wrap bug in `Buffer.String` was pinned down: the bytes were right
read on their own, and only an emulator that models the cursor showed them
landing in the wrong column.

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
