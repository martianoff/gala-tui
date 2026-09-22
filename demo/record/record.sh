#!/usr/bin/env bash
# Record the mega demo — keys and mouse clicks — into a GIF for the README.
#
#   demo/record/record.sh
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

echo "building the demo…"
gala build ./demo >/dev/null

echo "driving the scripted tour (${COLS}x${ROWS})…"
python3 tools/record/drive.py \
    --script demo/record/tour.txt \
    --cast "$CAST" --cols "$COLS" --rows "$ROWS" \
    -- ./gala-tui

echo "rendering $GIF…"
agg --font-size 16 --fps-cap 20 --theme asciinema "$CAST" "$GIF"

ls -lh "$GIF"
