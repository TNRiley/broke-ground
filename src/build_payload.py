#!/usr/bin/env python3
"""Turn the harvest into the binary payload baked into index.html.

Layout decisions worth knowing before you change anything:
  * Rows are sorted by YEAR ASCENDING (unknown year last). The year scrubber is then a
    simple prefix of the arrays -- draw [0, upperBound(year)) -- which is what makes the
    time-lapse cheap. Do not re-sort spatially; the render cost goes up, not down.
  * Columns, not rows. One typed array per field concatenated, because gzip finds far more
    redundancy down a column of style codes than across a row of mixed types.
  * The whole blob is gzipped and base64'd; the page inflates it with DecompressionStream.
  * Coordinates are quantised to 1e-5 deg (~1 m) as int32 offsets from the county's SW corner.
"""
import json, math, os, gzip, base64, struct, collections, statistics, re

D = os.path.join(os.path.dirname(__file__), "..", "data")
DC = (38.8946, -77.0365)          # Zero Milestone, Washington DC
Q = 100000.0                      # coordinate quantisation: 1e-5 deg

def miles(lat, lon):
    dy = (lat - DC[0]) * 69.055
    dx = (lon - DC[1]) * 69.055 * math.cos(math.radians((lat + DC[0]) / 2))
    return math.hypot(dx, dy)

# ---------------------------------------------------------------- load
rows = []
for line in open(os.path.join(D, "parcels.ndjson")):
    a = json.loads(line)
    try: y = int(a.get("YEARBLT"))
    except (TypeError, ValueError): y = 0
    if not (1700 <= y <= 2026): y = 0
    a["_y"] = y
    rows.append(a)
print(f"loaded {len(rows):,}")

# ---------------------------------------------------------------- typology
def form(r):
    s = (r.get("DESCSTYL") or "").upper()
    lu = (r.get("DESCLU") or "").upper()
    if "CONDOMINIUM" in lu or "CONDOMINIUM" in s: return 2
    if "TOWNHOUSE" in s: return 1
    if lu == "APARTMENTS" or "APARTMENT" in s: return 3
    if s.startswith("STRY"): return 0                      # detached house
    if lu in ("COMMERCIAL", "INDUSTRIAL", "COMMERCIAL/RESIDENTIAL",
              "RESIDENTIAL/COMMERCIAL", "COUNTRY CLUB"): return 4
    if lu.startswith("EXEMPT"): return 5                   # public / institutional
    if lu == "AGRICULTURAL": return 6
    return 7
FORMS = ["Detached house", "Townhouse", "Condominium", "Apartment building",
         "Commercial / industrial", "Public / institutional", "Farm", "Other / unclassified"]
for r in rows: r["_f"] = form(r)

# ---------------------------------------------------------------- dictionaries
def dictionary(key):
    c = collections.Counter((r.get(key) or "").strip() for r in rows)
    vals = [v for v, _ in c.most_common() if v]
    return vals, {v: i + 1 for i, v in enumerate(vals)}     # 0 = missing

styles, style_ix = dictionary("DESCSTYL")
subs,   sub_ix   = dictionary("DESCSUBD")
cities, city_ix  = dictionary("CITY")
lus,    lu_ix    = dictionary("DESCLU")
cnsts,  cnst_ix  = dictionary("DESCCNST")

streets = collections.Counter(); nums = {}
for i, r in enumerate(rows):
    ad = (r.get("ADDRESS") or "").strip()
    m = re.match(r"^(\d+)\s+(.+)$", ad)
    if m:
        r["_num"] = min(int(m.group(1)), 65535); r["_st"] = m.group(2)
        streets[m.group(2)] += 1
    else:
        r["_num"] = 0; r["_st"] = ad if ad else ""
        if ad: streets[ad] += 1
street_list = [s for s, _ in streets.most_common()]
street_ix = {s: i + 1 for i, s in enumerate(street_list)}
print(f"dicts: {len(styles)} styles, {len(subs)} subdivisions, {len(street_list)} streets, {len(cities)} cities")

# ---------------------------------------------------------------- sort by year
rows.sort(key=lambda r: (r["_y"] == 0, r["_y"]))
n = len(rows)
n_built = sum(1 for r in rows if r["_y"])

# ---------------------------------------------------------------- MIHP spatial join
mihp = json.load(open(os.path.join(D, "mihp.json")))
grid = collections.defaultdict(list)
for i, r in enumerate(rows):
    grid[(int(r["x"] * 2000), int(r["y"] * 2000))].append(i)
links = {}
JOIN_M = 60.0
for mi, h in enumerate(mihp):
    gx, gy = int(h["x"] * 2000), int(h["y"] * 2000)
    best, bestd = None, JOIN_M
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for i in grid.get((gx + dx, gy + dy), ()):
                r = rows[i]
                dlat = (r["y"] - h["y"]) * 111320.0
                dlon = (r["x"] - h["x"]) * 111320.0 * math.cos(math.radians(h["y"]))
                d = math.hypot(dlat, dlon)
                if d < bestd and i not in links: best, bestd = i, d
    if best is not None: links[best] = mi
print(f"MIHP: {len(links):,} of {len(mihp):,} historic properties matched to a parcel "
      f"within {JOIN_M:.0f} m")

# ---------------------------------------------------------------- columns
minx = min(r["x"] for r in rows); miny = min(r["y"] for r in rows)
def col(fmt, vals): return struct.pack(f"<{len(vals)}{fmt}", *vals)

cols = {
  "x":     col("i", [int(round((r["x"] - minx) * Q)) for r in rows]),
  "y":     col("i", [int(round((r["y"] - miny) * Q)) for r in rows]),
  "year":  col("H", [r["_y"] for r in rows]),
  "form":  col("B", [r["_f"] for r in rows]),
  "style": col("B", [style_ix.get((r.get("DESCSTYL") or "").strip(), 0) for r in rows]),
  "lu":    col("B", [lu_ix.get((r.get("DESCLU") or "").strip(), 0) for r in rows]),
  "cnst":  col("B", [cnst_ix.get((r.get("DESCCNST") or "").strip(), 0) for r in rows]),
  "city":  col("B", [city_ix.get((r.get("CITY") or "").strip(), 0) for r in rows]),
  "sub":   col("H", [sub_ix.get((r.get("DESCSUBD") or "").strip(), 0) for r in rows]),
  "st":    col("H", [street_ix.get(r["_st"], 0) for r in rows]),
  "num":   col("H", [r["_num"] for r in rows]),
  "sqft":  col("I", [min(r.get("SQFTSTRC") or 0, 4294967295) for r in rows]),
  "val":   col("I", [min(r.get("NFMTTLVL") or 0, 4294967295) for r in rows]),
  "acres": col("I", [min(int(round((r.get("ACRES") or 0) * 100)), 4294967295) for r in rows]),
  # ACCTID is county(2) + district(2) + account(8); county is always 16 in this county,
  # so store district as a byte and the account as an int -- 5 bytes instead of 12 chars
  # of incompressible digits. The SDAT URL is rebuilt from these in the page.
  "dist":  col("B", [int(((r.get("ACCTID") or "0000").strip() + "0000")[2:4] or 0) for r in rows]),
  "acct":  col("I", [int((((r.get("ACCTID") or "").strip() + " " * 12)[4:12]).strip() or 0) for r in rows]),
  "mihpP": col("I", sorted(links.keys())),
  "mihpH": col("I", [links[k] for k in sorted(links.keys())]),
}
blob = b"".join(cols[k] for k in cols)
offsets, o = {}, 0
for k in cols:
    offsets[k] = [o, len(cols[k])]; o += len(cols[k])
gz = gzip.compress(blob, 9)
print(f"blob {len(blob)/1e6:.1f} MB -> gzip {len(gz)/1e6:.1f} MB -> b64 {len(gz)*4/3/1e6:.1f} MB")

# ---------------------------------------------------------------- findings (computed, never typed)
built = [r for r in rows if r["_y"]]
def decade_stats():
    by = collections.defaultdict(list)
    for r in built: by[r["_y"] // 10 * 10].append(miles(r["y"], r["x"]))
    out = []
    for d in sorted(by):
        v = sorted(by[d])
        out.append({"decade": d, "n": len(v), "median_mi": round(statistics.median(v), 2),
                    "p90_mi": round(v[int(len(v) * .9)], 2)})
    return out

def form_shares():
    by = collections.defaultdict(collections.Counter)
    for r in built: by[r["_y"] // 10 * 10][r["_f"]] += 1
    return [{"decade": d, "n": sum(by[d].values()),
             "counts": {str(k): v for k, v in sorted(by[d].items())}} for d in sorted(by)]

def house_size():
    by = collections.defaultdict(list)
    for r in built:
        if r["_f"] == 0 and (r.get("SQFTSTRC") or 0) > 200: by[r["_y"] // 10 * 10].append(r["SQFTSTRC"])
    return [{"decade": d, "median": int(statistics.median(v)), "n": len(v)}
            for d, v in sorted(by.items()) if len(v) > 50]

# Agricultural Reserve, point in polygon
ar = json.load(open(os.path.join(D, "ctx_agreserve.geojson")))
rings = []
for f in ar["features"]:
    g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for part in parts:
        ring = part[0]; xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        rings.append((min(xs), min(ys), max(xs), max(ys), ring))
def in_ar(x, y):
    for x0, y0, x1, y1, ring in rings:
        if not (x0 <= x <= x1 and y0 <= y <= y1): continue
        inside = False; nn = len(ring); j = nn - 1
        for i in range(nn):
            xi, yi = ring[i]; xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: inside = not inside
            j = i
        if inside: return True
    return False
ar_by = collections.defaultdict(lambda: [0, 0])
ar_flags = bytearray(n)
for i, r in enumerate(rows):
    f = in_ar(r["x"], r["y"]); ar_flags[i] = 1 if f else 0
    if r["_y"]: ar_by[r["_y"] // 10 * 10][0 if f else 1] += 1
cols["ar"] = bytes(ar_flags)
offsets["ar"] = [o, len(cols["ar"])]; o += len(cols["ar"])
blob = blob + bytes(ar_flags)
gz = gzip.compress(blob, 9)
print(f"with AR flags: blob {len(blob)/1e6:.1f} MB -> gzip {len(gz)/1e6:.1f} MB -> b64 {len(gz)*4/3/1e6:.1f} MB")

findings = {
  "frontier": decade_stats(),
  "forms": form_shares(),
  "house_size": house_size(),
  "ag_reserve": [{"decade": d, "inside": v[0], "outside": v[1]} for d, v in sorted(ar_by.items())],
  "ar_parcels": int(sum(ar_flags)),
  "year_hist": sorted(collections.Counter(r["_y"] for r in built).items()),
}

meta = {
  "n": n, "n_built": n_built, "n_unbuilt": n - n_built,
  "minx": minx, "miny": miny, "q": Q, "dc": DC,
  "forms": FORMS, "styles": styles, "subs": subs, "cities": cities,
  "lus": lus, "cnsts": cnsts, "streets": street_list,
  "mihp": [{"n": h["name"], "a": h["addr"], "t": h["town"], "p": h["pdf"]} for h in mihp],
  "offsets": offsets, "findings": findings,
}
json.dump(meta, open(os.path.join(D, "meta.json"), "w"), separators=(",", ":"))
open(os.path.join(D, "payload.b64"), "w").write(base64.b64encode(gz).decode())
print(f"meta.json {os.path.getsize(os.path.join(D,'meta.json'))/1e6:.2f} MB · "
      f"payload.b64 {os.path.getsize(os.path.join(D,'payload.b64'))/1e6:.2f} MB")
