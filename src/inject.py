#!/usr/bin/env python3
"""Splice meta + payload into template.html -> index.html.

The payload is 6 MB of base64; it is spliced by this script rather than written out
by hand, so it never passes through the conversation. Same trick as Overhead/Daybook.
"""
import json, os, sys

D = os.path.join(os.path.dirname(__file__), "..", "data")
SRC = os.path.join(os.path.dirname(__file__), "template.html")
OUT = os.path.join(os.path.dirname(__file__), "..", "index.html")

meta = json.load(open(os.path.join(D, "meta.json")))
mihp_raw = json.load(open(os.path.join(D, "mihp.json")))

# the inventory number belongs on the record shown in the page
for m, raw in zip(meta["mihp"], mihp_raw):
    m["no"] = raw["no"]

def rnd(g, p=5):
    if isinstance(g, list): return [rnd(v, p) for v in g]
    if isinstance(g, float): return round(g, p)
    return g

def geoms(name):
    d = json.load(open(os.path.join(D, f"ctx_{name}.geojson")))
    return [{"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}
            for f in d["features"] if f.get("geometry")]

def centroid(g):
    pts = []
    def walk(c):
        if c and isinstance(c[0], (int, float)): pts.append(c)
        else:
            for v in c: walk(v)
    walk(g["coordinates"])
    return [round(sum(p[0] for p in pts) / len(pts), 5), round(sum(p[1] for p in pts) / len(pts), 5)]

muni = json.load(open(os.path.join(D, "ctx_municipalities.geojson")))
metro = json.load(open(os.path.join(D, "ctx_metro.geojson")))
meta["geo"] = {
    "county": geoms("county"),
    "streams": geoms("streams"),
    "lakes": geoms("lakes"),
    "agreserve": geoms("agreserve"),
    "muni": [{"n": (f["properties"].get("MUN_NAME") or "").title(),
              "g": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])},
              "c": centroid(f["geometry"])}
             for f in muni["features"] if f.get("geometry")],
    "metro": [{"n": f["properties"].get("NAME"),
               "x": round(f["geometry"]["coordinates"][0], 5),
               "y": round(f["geometry"]["coordinates"][1], 5)}
              for f in metro["features"] if f.get("geometry")],
    "mihpXY": [[m["x"], m["y"]] for m in mihp_raw],
}

payload = open(os.path.join(D, "payload.b64")).read().strip()
html = open(SRC).read()
assert "__META__" in html and "__PAYLOAD__" in html
html = html.replace("__META__", json.dumps(meta, separators=(",", ":")))
html = html.replace("__PAYLOAD__", payload)
open(OUT, "w").write(html)
print(f"index.html {os.path.getsize(OUT)/1e6:.2f} MB  "
      f"(meta {len(json.dumps(meta))/1e6:.2f} MB + payload {len(payload)/1e6:.2f} MB)")
