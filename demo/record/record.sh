#!/usr/bin/env bash
# Record the mega demo — keys and mouse clicks — into a GIF for the README.
#
#   demo/record/record.sh
#
# Needs a POSIX pty, so on Windows it runs under WSL: demo/record/record.ps1.
#
# Two steps, deliberately separate:
#
#   1. tools/record/drive.py runs the demo under a pty, replays tour.txt
#      (including SGR mouse clicks) and writes an asciicast — plain text,
#      diffable, committed.
#   2. agg renders that cast to a GIF. Re-render at any size, speed or theme
#      without running the app again.
set -euo pipefail

cd "$(dirname "$0")/../.."

COLS=${COLS:-120}
ROWS=${ROWS:-36}
CAST=${CAST:-docs/demo.cast}
GIF=${GIF:-docs/gala-tui-demo.gif}

BIN=./gala-tui

echo "building the demo…"
# Name the output explicitly. Without -o, gala build names the binary after
# the checkout directory, so a clone called anything but gala-tui (a worktree,
# a Windows checkout called gala_tui) leaves ./gala-tui stale or missing.
gala build -o "$BIN" ./demo >/dev/null
if [ ! -x "$BIN" ]; then
    # Otherwise drive.py records the exec failure as the whole demo and agg
    # happily renders it.
    echo "record: $BIN was not built" >&2
    exit 1
fi

echo "driving the scripted tour (${COLS}x${ROWS})…"
python3 tools/record/drive.py \
    --script demo/record/tour.txt \
    --cast "$CAST" --cols "$COLS" --rows "$ROWS" \
    -- "$BIN"

echo "rendering ${GIF}…"
agg --font-size 16 --fps-cap 20 --theme asciinema "$CAST" "$GIF"

ls -lh "$GIF"
