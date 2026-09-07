#!/usr/bin/env python3
"""
Harvest every parcel point in Montgomery County, MD from Maryland iMAP's
MDProperty View "Parcel Points" layer (SDAT assessment data, refreshed yearly).

  https://mdgeodata.md.gov/imap/rest/services/PlanningCadastre/MD_PropertyData/MapServer/0

Notes for whoever runs this next:
  * YEARBLT is a STRING(4), not a number. `YEARBLT > 0` returns HTTP 400.
  * maxRecordCount is 2000; pagination is supported, but you MUST pass
    orderByFields or the offsets are not stable.
  * SDATWEBADR is a 140-char URL that is fully derivable from ACCTID
    (county[0:2] + district[2:4] + account[4:]), so we don't carry it.
  * /usr/local/bin/python3 on this Mac has no CA bundle -> urllib HTTPS dies.
    Run with /usr/bin/python3, or keep the cert fallback below.
"""
import json, os, ssl, sys, time, urllib.parse, urllib.request

BASE = ("https://mdgeodata.md.gov/imap/rest/services/PlanningCadastre/"
        "MD_PropertyData/MapServer/0/query")
WHERE = "JURSCODE='MONT'"
FIELDS = ("ACCTID,ADDRESS,CITY,ZIPCODE,YEARBLT,DESCSTYL,SQFTSTRC,DESCLU,"
          "DESCSUBD,DESCCNST,NFMTTLVL,BLDG_STORY,ACRES")
PAGE = 2000
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "parcels.ndjson")

def ctx():
    try:
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    except Exception:
        return ssl.create_default_context()

def get(params, tries=5):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "quick-projects/broke-ground (tnriley@gmail.com)"})
            with urllib.request.urlopen(req, timeout=180, context=ctx()) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "error" in d:
                raise RuntimeError(d["error"])
            return d
        except Exception as e:
            if attempt == tries - 1:
                raise
            time.sleep(3 * (attempt + 1))

def main():
    total = get({"where": WHERE, "returnCountOnly": "true", "f": "json"})["count"]
    print(f"{total} parcels", flush=True)
    done = 0
    with open(OUT, "w") as fh:
        offset = 0
        while offset < total:
            d = get({
                "where": WHERE, "outFields": FIELDS, "returnGeometry": "true",
                "outSR": "4326", "orderByFields": "OBJECTID",
                "resultOffset": offset, "resultRecordCount": PAGE, "f": "json",
            })
            feats = d.get("features", [])
            if not feats:
                print(f"  empty page at offset {offset}; stopping", flush=True)
                break
            for f in feats:
                g = f.get("geometry") or {}
                a = f["attributes"]
                if g.get("x") is None:
                    continue
                a["x"], a["y"] = g["x"], g["y"]
                fh.write(json.dumps(a, separators=(",", ":")) + "\n")
                done += 1
            offset += len(feats)
            if offset % 20000 < PAGE:
                print(f"  {offset}/{total}  kept {done}", flush=True)
            time.sleep(0.4)
    print(f"done: {done} rows with geometry -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
