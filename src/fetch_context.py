#!/usr/bin/env python3
"""Map-context layers for Broke Ground: county outline, municipalities, water,
the Agricultural Reserve boundary, and Metro stations. All generalized server-side
with maxAllowableOffset so the baked payload stays small.

Run with /usr/bin/python3 (see harvest.py note on the missing CA bundle)."""
import json, os, ssl, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data")

def ctx():
    try: return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    except Exception: return ssl.create_default_context()

def q(base, **params):
    params.setdefault("f", "geojson")
    params.setdefault("outSR", "4326")
    url = base + "/query?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "quick-projects/broke-ground"})
    with urllib.request.urlopen(req, timeout=180, context=ctx()) as r:
        return json.loads(r.read().decode("utf-8"))

IMAP = "https://mdgeodata.md.gov/imap/rest/services"
JOBS = [
    ("county", f"{IMAP}/Boundaries/MD_PoliticalBoundaries/MapServer/1",
     dict(where="COUNTY='Montgomery'", outFields="COUNTY", maxAllowableOffset=0.0002)),
    ("municipalities", f"{IMAP}/Boundaries/MD_PoliticalBoundaries/MapServer/2",
     dict(where="JURSCODE='MONT'", outFields="MUN_NAME", maxAllowableOffset=0.0002)),
    ("streams", f"{IMAP}/Hydrology/MD_Waterbodies/MapServer/0",
     dict(geometry="-77.55,38.90,-76.90,39.36", geometryType="esriGeometryEnvelope",
          inSR="4326", spatialRel="esriSpatialRelIntersects", outFields="",
          maxAllowableOffset=0.0004)),
    ("lakes", f"{IMAP}/Hydrology/MD_Waterbodies/MapServer/1",
     dict(geometry="-77.55,38.90,-76.90,39.36", geometryType="esriGeometryEnvelope",
          inSR="4326", spatialRel="esriSpatialRelIntersects", outFields="",
          maxAllowableOffset=0.0004)),
    ("agreserve", "https://mcmaps.org/server11/rest/services/Overlays/MCAtlas_Boundaries/MapServer/10",
     dict(where="1=1", outFields="*", maxAllowableOffset=0.0004)),
    ("metro", "https://gis.montgomerycountymd.gov/arcgis/rest/services/General/metro_stations/MapServer/0",
     dict(where="1=1", outFields="*")),
]

for name, base, params in JOBS:
    try:
        d = q(base, **params)
        n = len(d.get("features", []))
        path = os.path.join(OUT, f"ctx_{name}.geojson")
        with open(path, "w") as fh:
            json.dump(d, fh, separators=(",", ":"))
        print(f"{name:16s} {n:>6} features  {os.path.getsize(path)/1024:.0f} KB")
    except Exception as e:
        print(f"{name:16s} FAILED: {e}")
