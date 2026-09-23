#!/usr/bin/env python3
"""Drive a gala-tui app through a scripted session, mouse clicks included.

Recording tools replay keystrokes and have no notion of a click. But gala-tui
speaks SGR mouse mode (see mouse.gala), so a click is just bytes: `ESC [ < btn ; col ; row M` to press and `... m` to release. That
makes a fully scripted, reproducible session possible with no one at the
mouse, which is the whole point: the demo can be re-recorded after a UI change
instead of being a 10 MB artifact nobody knows how to reproduce.

This opens a pty for the app, replays a script against it, and writes the
session as an asciicast v2 file — timestamped output chunks, which is plain
text, so the recording is reviewable in a diff and re-renderable to GIF at any
size or speed without re-running the app.

    python3 tools/record/drive.py --script demo/record/tour.txt \
        --cast docs/demo.cast --cols 100 --rows 30 -- ./gala-tui
    agg docs/demo.cast docs/gala-tui-demo.gif

Script lines, one action each, `#` for comments:

    wait 0.8            seconds to let the frame settle
    key q               a literal keystroke ("space" and "enter" are spelled)
    keys Ctrl+P         a chord: Ctrl+<letter>
    click 24 7          left click at column 24, row 7 (1-based, as a terminal counts)
    move 30 9           motion with the button held — drag
    scroll up 40 12     wheel up at a position (`down` too)
    text hello          type a run of characters
"""

import argparse
import codecs
import fcntl
import json
import os
import pty
import select
import shlex
import signal
import struct
import sys
import termios
import time

# SGR button codes (mouse.gala decodes these).
BTN_LEFT = 0
BTN_MOTION = 32          # motion-while-held adds 32
WHEEL_UP = 64
WHEEL_DOWN = 65


def sgr(button: int, col: int, row: int, press: bool = True) -> bytes:
    """One SGR mouse packet. `M` is press/scroll, `m` is release."""
    return f"\x1b[<{button};{col};{row}{'M' if press else 'm'}".encode()


def terminal_size(fd: int) -> tuple[int, int]:
    """(rows, cols) of the recording terminal, with a sane fallback.

    The child must match: a pty with no TIOCSWINSZ is 0x0, and a TUI asked to
    paint into nothing emits an enter sequence and not one frame — which looks
    exactly like a hung app.
    """
    try:
        packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\0" * 8)
        rows, cols, _, _ = struct.unpack("HHHH", packed)
        if rows and cols:
            return rows, cols
    except OSError:
        pass
    return 30, 100


def parse_action(line: str):
    parts = shlex.split(line)
    verb, args = parts[0], parts[1:]
    if verb == "wait":
        return ("wait", float(args[0]))
    if verb == "key":
        named = {"enter": b"\r", "space": b" ", "tab": b"\t", "esc": b"\x1b",
                 "backspace": b"\x7f", "up": b"\x1b[A", "down": b"\x1b[B",
                 "left": b"\x1b[D", "right": b"\x1b[C",
                 "home": b"\x1b[H", "end": b"\x1b[F",
                 "pageup": b"\x1b[5~", "pagedown": b"\x1b[6~"}
        name = args[0]
        if len(name) > 1 and name not in named:
            # A one-character key is a literal; a word is a name, and a name
            # that isn't in the table is a typo. Sending it as text instead
            # would type "pageup" into whatever has focus and record that as
            # if it were the tour working.
            raise SystemExit(
                f"drive: unknown key {name!r}; known names: "
                + ", ".join(sorted(named)))
        return ("send", named.get(name, name.encode()))
    if verb == "keys":
        chord = args[0]
        if chord.startswith("Ctrl+") and len(chord) == 6:
            return ("send", bytes([ord(chord[5].upper()) - 64]))
        raise SystemExit(f"drive: unsupported chord {chord!r}")
    if verb == "text":
        return ("send", " ".join(args).encode())
    if verb == "click":
        col, row = int(args[0]), int(args[1])
        return ("send", sgr(BTN_LEFT, col, row) + sgr(BTN_LEFT, col, row, press=False))
    if verb == "move":
        col, row = int(args[0]), int(args[1])
        return ("send", sgr(BTN_LEFT + BTN_MOTION, col, row))
    if verb == "scroll":
        button = WHEEL_UP if args[0] == "up" else WHEEL_DOWN
        return ("send", sgr(button, int(args[1]), int(args[2])))
    raise SystemExit(f"drive: unknown action {verb!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--settle", type=float, default=1.0,
                    help="seconds to wait for the first frame before scripting")
    ap.add_argument("--cast", help="write an asciicast v2 file here")
    ap.add_argument("--cols", type=int, default=100)
    ap.add_argument("--rows", type=int, default=30)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    opts = ap.parse_args()
    # argparse.REMAINDER keeps the `--` separator, and execvp would try to
    # run it.
    command = opts.command[1:] if opts.command[:1] == ["--"] else opts.command
    if not command:
        raise SystemExit("drive: give me a command to run")

    with open(opts.script) as fh:
        actions = [parse_action(ln.strip()) for ln in fh
                   if ln.strip() and not ln.strip().startswith("#")]

    # An explicit size when recording to a cast: the output must not depend
    # on whatever terminal happened to run the driver.
    rows, cols = (opts.rows, opts.cols) if opts.cast else terminal_size(sys.stdout.fileno())
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.setdefault("TERM", "xterm-256color")
        os.execvp(command[0], command)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    cast = open(opts.cast, "w") if opts.cast else None
    if cast:
        json.dump({"version": 2, "width": cols, "height": rows,
                   "env": {"TERM": "xterm-256color"}}, cast)
        cast.write("\n")
    started = time.time()
    # One decoder for the whole session, not one per read. A pty read splits
    # wherever the kernel had bytes ready, which lands mid-glyph often enough
    # to matter: decoding each chunk on its own turns every straddled box-
    # drawing or braille character into U+FFFD, and those replacement glyphs
    # are then baked into the cast. An incremental decoder holds the partial
    # sequence back until the rest of it arrives.
    decoder = codecs.getincrementaldecoder("utf-8")("replace")

    def pump(seconds: float) -> None:
        """Forward the app's output for `seconds` — to the cast, or onward."""
        end = time.time() + seconds
        while True:
            left = end - time.time()
            if left <= 0:
                return
            ready, _, _ = select.select([fd], [], [], min(0.02, left))
            if not ready:
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                return
            if not chunk:
                return
            if cast:
                text = decoder.decode(chunk)
                if not text:
                    continue
                cast.write(json.dumps([round(time.time() - started, 6), "o",
                                       text]) + "\n")
            else:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()

    pump(opts.settle)
    for index, (kind, payload) in enumerate(actions):
        if kind == "wait":
            pump(payload)
            continue
        try:
            os.write(fd, payload)
        except OSError:
            # The app is gone. That is a script bug — an action quit it
            # early — and saying which one beats a traceback from the pty.
            print(f"drive: app exited before action {index + 1} "
                  f"({payload!r}); recording stops here", file=sys.stderr)
            break
        pump(0.12)          # let the frame land before the next action
    pump(0.4)

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    os.waitpid(pid, 0)
    if cast:
        cast.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
