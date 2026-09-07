#!/usr/bin/env python3
"""Second pass: the Agricultural Reserve wall, the fold-back, Kensington, oldest stock."""
import json, math, collections, statistics, os
D = os.path.join(os.path.dirname(__file__), "..", "data")
DC = (38.8946, -77.0365)
def miles(lat, lon):
    dy = (lat - DC[0]) * 69.055
    dx = (lon - DC[1]) * 69.055 * math.cos(math.radians((lat + DC[0]) / 2))
    return math.hypot(dx, dy)

# --- Agricultural Reserve polygons (AR zone, MC Atlas) ---
ar = json.load(open(os.path.join(D, "ctx_agreserve.geojson")))
polys = []
for f in ar["features"]:
    g = f["geometry"]
    parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for part in parts:
        ring = part[0]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        polys.append((min(xs), min(ys), max(xs), max(ys), ring))
print(f"{len(polys)} AR rings")

def in_ar(x, y):
    for x0, y0, x1, y1, ring in polys:
        if not (x0 <= x <= x1 and y0 <= y <= y1): continue
        inside = False; n = len(ring); j = n - 1
        for i in range(n):
            xi, yi = ring[i]; xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
        if inside: return True
    return False

rows = []
for line in open(os.path.join(D, "parcels.ndjson")):
    a = json.loads(line)
    try: y = int(a.get("YEARBLT"))
    except (TypeError, ValueError): y = None
    if y is not None and not (1700 <= y <= 2026): y = None
    a["_y"] = y; a["_mi"] = miles(a["y"], a["x"])
    rows.append(a)

print("\n=== 2. THE WALL: building inside vs outside the Agricultural Reserve ===")
inside = collections.Counter(); outside = collections.Counter()
n_in = 0
for r in rows:
    isin = in_ar(r["x"], r["y"])
    n_in += isin
    if r["_y"]:
        (inside if isin else outside)[r["_y"] // 10 * 10] += 1
print(f"{n_in:,} of {len(rows):,} parcels fall inside the AR zone")
print(f"{'decade':>8} {'inside AR':>10} {'outside':>9} {'AR share':>9}")
for d in sorted(outside):
    if d < 1940: continue
    i, o = inside[d], outside[d]
    print(f"{d:>8} {i:>10,} {o:>9,} {i/(i+o):>8.1%}")

print("\n=== the fold-back: share of each decade built INSIDE the 1970 frontier ===")
# the 1970 build line: p90 distance of everything standing in 1970
pre70 = sorted(r["_mi"] for r in rows if r["_y"] and r["_y"] <= 1970)
line70 = pre70[int(len(pre70) * .9)]
print(f"1970 build line (p90 of everything standing then) = {line70:.1f} mi from the Zero Milestone")
for d in range(1970, 2030, 10):
    v = [r for r in rows if r["_y"] and r["_y"]//10*10 == d]
    if not v: continue
    inf = sum(1 for r in v if r["_mi"] <= line70)
    print(f"  {d}s  {inf/len(v):>5.0%} of {len(v):,} new buildings went up inside it")

print("\n=== KENSINGTON (the town, 20895 + city name) ===")
k = [r for r in rows if (r.get("CITY") or "").upper() == "KENSINGTON" and r["_y"]]
kb = collections.Counter(r["_y"]//10*10 for r in k)
print(f"{len(k):,} buildings")
for d in sorted(kb): print(f"  {d}s {kb[d]:>5,}  {'#'*min(60,kb[d]//15)}")

print("\n=== OLDEST SURVIVING (pre-1830, with an address) ===")
old = sorted((r for r in rows if r["_y"] and r["_y"] < 1830 and r.get("ADDRESS")), key=lambda r: r["_y"])
for r in old[:18]:
    print(f"  {r['_y']}  {r['ADDRESS']:<32} {(r.get('CITY') or ''):<16} {r.get('DESCSTYL') or ''}")
print(f"  ...{len(old)} total pre-1830 with an address")
