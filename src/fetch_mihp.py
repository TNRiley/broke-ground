#!/usr/bin/env python3
"""The Maryland Inventory of Historic Properties for Montgomery County (2,829 records).

The second source on this page: the tax roll knows a building's year, this knows its
NAME and carries a link to the scanned MHT survey form. Join is spatial (nearest parcel).

GOTCHA: PDFLINK contains a literal space and semicolon ("M; 17-53.pdf"). The URL only
resolves with the space percent-encoded (%20); handed to a browser raw it 404s.
"""
import json, ssl, urllib.parse, urllib.request, os
B = ("https://mdgeodata.md.gov/imap/rest/services/Historic/"
     "MD_InventoryHistoricProperties/MapServer/0/query")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "mihp.json")
def ctx():
    try: return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    except Exception: return ssl.create_default_context()
def get(p):
    req = urllib.request.Request(B + "?" + urllib.parse.urlencode(p),
                                 headers={"User-Agent": "quick-projects/broke-ground"})
    with urllib.request.urlopen(req, timeout=180, context=ctx()) as r:
        return json.loads(r.read().decode("utf-8"))

def centroid(g):
    rings = g.get("rings") or []
    pts = [p for ring in rings for p in ring]
    if not pts: return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

out, offset = [], 0
while True:
    d = get({"where": "COUNTY='Montgomery'",
             "outFields": "MIHPNO,FULLADDR,TOWN,Nam,PDFLINK,DOErecord",
             "returnGeometry": "true", "maxAllowableOffset": "0.0005",
             "outSR": "4326", "orderByFields": "OBJECTID",
             "resultOffset": offset, "resultRecordCount": 1000, "f": "json"})
    fs = d.get("features", [])
    if not fs: break
    for f in fs:
        a = f["attributes"]
        # MapServer ignores returnCentroid, so average the polygon's outer ring instead.
        c = centroid(f.get("geometry") or {})
        if c is None: continue
        out.append({
            "no": (a.get("MIHPNO") or "").strip(),
            "name": (a.get("Nam") or "").strip(),
            "addr": (a.get("FULLADDR") or "").strip(),
            "town": (a.get("TOWN") or "").strip(),
            "pdf": (a.get("PDFLINK") or "").strip(),
            "x": round(c[0], 6), "y": round(c[1], 6),
        })
    offset += len(fs)
    print(f"  {offset}", flush=True)
json.dump(out, open(OUT, "w"), separators=(",", ":"))
print(f"{len(out)} historic properties with a centroid -> {OUT}")
