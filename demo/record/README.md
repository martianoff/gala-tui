# Recording the demo

`record.sh` produces the README's GIF from a **scripted** session — no one at
the keyboard, and no one at the mouse.

The mouse is the interesting part. No recorder has click primitives: VHS types
keys, asciinema records whatever a human does. But gala-tui speaks SGR mouse
mode, so a click is just bytes on stdin —
`ESC [ < 0 ; col ; row M` to press, `… m` to release. `tools/record/drive.py`
writes those into the app's pty on a schedule, which makes a click as
reproducible as a keystroke.

```
demo/record/record.sh              # build → drive → render
COLS=100 ROWS=30 demo/record/record.sh
```

Two artifacts, and the split matters: `docs/demo.cast` is the session as
timestamped text, so it is reviewable in a diff and re-renderable to any size,
speed or theme; `docs/gala-tui-demo.gif` is what the README shows.

## Editing the tour

`tour.txt` is one action per line — `wait`, `key`, `keys Ctrl+P`, `text`,
`click COL ROW`, `move`, `scroll up|down COL ROW`. Coordinates are 1-based and
were read off a recorded frame at 120x36; if the layout changes, re-check them
rather than guessing. The driver reports which action was in flight if the app
exits early, which is how a wrong coordinate usually announces itself.

## Tooling

`brew install agg` — a single binary, no browser. VHS is the better-known
option and was tried first; it renders through headless Chrome and fails
silently when there isn't one.
