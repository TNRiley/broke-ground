#!/usr/bin/env python3
"""Exploratory pass over the harvest. Answers, before any page is written:
   1. is there a growth wave moving out from DC?
   2. does the Agricultural Reserve show up as a wall in 1980?
   3. did the housing form change (detached -> townhouse -> condo)?
   4. did houses get bigger?
"""
import json, math, statistics, collections, os
D = os.path.join(os.path.dirname(__file__), "..", "data")

# Zero Milestone, Washington DC — the origin every distance on the page is measured from.
DC = (38.8946, -77.0365)
def miles(lat, lon):
    dy = (lat - DC[0]) * 69.055
    dx = (lon - DC[1]) * 69.055 * math.cos(math.radians((lat + DC[0]) / 2))
    return math.hypot(dx, dy)

rows = []
with open(os.path.join(D, "parcels.ndjson")) as fh:
    for line in fh:
        a = json.loads(line)
        y = a.get("YEARBLT")
        try: y = int(y)
        except (TypeError, ValueError): y = None
        if y is not None and not (1700 <= y <= 2026): y = None
        a["_y"] = y
        a["_mi"] = miles(a["y"], a["x"])
        rows.append(a)

built = [r for r in rows if r["_y"]]
print(f"{len(rows):,} parcels · {len(built):,} with a build year · {len(rows)-len(built):,} without\n")

print("=== 1. THE FRONTIER: distance from DC by decade (miles) ===")
print(f"{'decade':>8} {'n':>8} {'median':>8} {'p90':>8} {'max':>7}")
by = collections.defaultdict(list)
for r in built: by[r["_y"] // 10 * 10].append(r["_mi"])
for d in sorted(by):
    if d < 1880: continue
    v = sorted(by[d])
    print(f"{d:>8} {len(v):>8,} {statistics.median(v):>8.1f} {v[int(len(v)*.9)]:>8.1f} {v[-1]:>7.1f}")

print("\n=== 3. HOUSING FORM by decade (share of residential) ===")
def form(r):
    s = (r.get("DESCSTYL") or "").upper()
    lu = (r.get("DESCLU") or "")
    if "CONDOMINIUM" in lu.upper() or "CONDOMINIUM" in s: return "condo"
    if "TOWNHOUSE" in s: return "townhouse"
    if lu == "Apartments" or "APARTMENT" in s: return "apartment"
    if s.startswith("STRY"): return "detached"
    if not s: return "?"
    return "other"
frm = collections.defaultdict(collections.Counter)
for r in built: frm[r["_y"] // 10 * 10][form(r)] += 1
print(f"{'decade':>8} {'detach':>7} {'town':>7} {'condo':>7} {'apt':>6} {'other/?':>8}")
for d in sorted(frm):
    if d < 1930: continue
    c = frm[d]; t = sum(c.values())
    print(f"{d:>8} {c['detached']/t:>6.0%} {c['townhouse']/t:>7.0%} {c['condo']/t:>7.0%} {c['apartment']/t:>6.0%} {(c['other']+c['?'])/t:>8.0%}   (n={t:,})")

print("\n=== 4. SIZE of new detached houses by decade (sq ft) ===")
sz = collections.defaultdict(list)
for r in built:
    if form(r) == "detached" and (r.get("SQFTSTRC") or 0) > 200: sz[r["_y"]//10*10].append(r["SQFTSTRC"])
for d in sorted(sz):
    if d < 1920: continue
    v = sorted(sz[d])
    print(f"{d:>8} median {statistics.median(v):>6,.0f}   n={len(v):,}")
