#!/usr/bin/env python3
"""Regenerate the coastline data in worldmap.go from Natural Earth.

    python3 tools/worldmap/pack.py        # from the repository root

Downloads the 1:110m and 1:50m coastlines (Natural Earth, public domain),
simplifies the 1:50m set to 0.05° with Douglas-Peucker, and rewrites the
`worldMapLowData` / `worldMapHighData` constants at the end of worldmap.go.

Each point is packed as (round(lon*100), round(lat*100)), two little-endian
int16s; the pair (0x7FFF, 0x7FFF) ends a coastline. The bytes are base64.
"""
import base64, json, math, re, struct, sys, urllib.request

# Pinned, so regenerating gives the same bytes; move it to take newer data.
NATURAL_EARTH = "ca96624a56bd078437bca8184e78163e5039ad19"
SOURCE = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{NATURAL_EARTH}/geojson/"
TARGET = "worldmap.go"
END = 0x7FFF


def coastlines(name):
    with urllib.request.urlopen(SOURCE + name) as r:
        data = json.load(r)
    out = []
    for feature in data["features"]:
        g = feature["geometry"]
        if g["type"] == "LineString":
            out.append(g["coordinates"])
        elif g["type"] == "MultiLineString":
            out.extend(g["coordinates"])
    return out


def simplify(pts, tol):
    """Douglas-Peucker: keep the points further than `tol` from the chord."""
    if tol <= 0 or len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        best, at = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = (math.hypot(px - ax, py - ay) if norm == 0
                 else abs(dy * px - dx * py + bx * ay - by * ax) / norm)
            if d > best:
                best, at = d, i
        if best > tol:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(pts, keep) if k]


def pack(lines, tol):
    buf = bytearray()
    points = 0
    for line in lines:
        pts = simplify([(float(p[0]), float(p[1])) for p in line], tol)
        q = []
        for x, y in pts:
            p = (max(-18000, min(18000, round(x * 100))),
                 max(-9000, min(9000, round(y * 100))))
            if not q or q[-1] != p:
                q.append(p)
        if len(q) < 2:
            continue
        for p in q:
            buf += struct.pack("<hh", *p)
        buf += struct.pack("<hh", END, END)
        points += len(q)
    return base64.b64encode(bytes(buf)).decode(), points


def go_const(name, data):
    chunks = [data[i:i + 96] for i in range(0, len(data), 96)]
    body = " +\n".join('\t"' + c + '"' for c in chunks)
    return f'const {name} = "" +\n{body}\n'


def main():
    low, lp = pack(coastlines("ne_110m_coastline.geojson"), 0)
    high, hp = pack(coastlines("ne_50m_coastline.geojson"), 0.05)
    src = open(TARGET, encoding="utf-8").read()
    head = re.split(r"^const worldMapLowData", src, maxsplit=1, flags=re.M)[0]
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(head + go_const("worldMapLowData", low) + "\n" + go_const("worldMapHighData", high))
    print(f"MapLow {lp} points, MapHigh {hp} points", file=sys.stderr)


if __name__ == "__main__":
    main()
