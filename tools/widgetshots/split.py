#!/usr/bin/env python3
"""Split widgetshots' stdout into docs/img/<name>.svg.

The generator writes every image to one stream with `===FILE name===` markers
rather than opening files itself: it keeps the GALA side to rendering, and
makes the whole catalogue reviewable with a pipe to `less` before anything
touches the repository.
"""
import os, sys

OUT = os.path.join("docs", "img")

def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    name, body, written = None, [], []
    def flush():
        if name is None:
            return
        path = os.path.join(OUT, name + ".svg")
        with open(path, "w") as f:
            f.write("\n".join(body).rstrip() + "\n")
        written.append(path)
    for line in sys.stdin.read().splitlines():
        if line.startswith("===FILE ") and line.endswith("==="):
            flush()
            name, body = line[len("===FILE "):-len("===")], []
        else:
            body.append(line)
    flush()
    for p in written:
        print(f"{p} ({os.path.getsize(p)} bytes)")
    if not written:
        print("no images: the generator produced no ===FILE markers", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
