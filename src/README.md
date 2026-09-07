# Rebuilding Broke Ground

Run these in order, from the project root, **with `/usr/bin/python3`** — the python.org build at
`/usr/local/bin/python3` has no CA bundle on this Mac and every `urllib` HTTPS call dies with
`CERTIFICATE_VERIFY_FAILED`. Stdlib only, no pip.

```bash
/usr/bin/python3 src/harvest.py         # ~3 min · 348,669 parcels → data/parcels.ndjson (105 MB, gitignored)
/usr/bin/python3 src/fetch_context.py   # county, towns, water, Agricultural Reserve, Metro → data/ctx_*.geojson
/usr/bin/python3 src/fetch_mihp.py      # 2,829 historic properties → data/mihp.json
/usr/bin/python3 src/build_payload.py   # → data/meta.json + data/payload.b64 (and prints every figure on the page)
/usr/bin/python3 src/inject.py          # template.html + the two above → ../index.html
```

`src/explore.py` and `src/explore2.py` are the exploratory passes that decided what the page would
say. They are kept because they are the audit trail for the four findings — run them to check the
numbers rather than trusting the page.

## Notes for whoever changes this

- **`YEARBLT` is a `STRING(4)`.** `where=YEARBLT > 0` returns HTTP 400 with an empty `details`.
- **Page with `orderByFields`.** `resultOffset` alone gives unstable pages.
- **`data/` files are inputs, not outputs to trust.** `build_payload.py` recomputes every number the
  page prints; nothing on the page is typed by hand.
- **The row order is load-bearing.** `build_payload.py` sorts by year ascending so the year scrubber
  is a prefix (`draw [0, upperBound(year))`). Re-sorting spatially makes the time-lapse slower, not
  faster.
- **Columns, not rows.** The blob is one typed array per field concatenated; gzip finds far more
  redundancy down a column of style codes than across a row of mixed types.
- **Byte alignment.** Column offsets are usually not multiples of 4, so a `new Int32Array(blob.buffer, o)`
  view throws. `inject.py`'s consumer slices the bytes first (`Uint8Array.slice` starts a fresh buffer).
- **`index.html` is wrapped for GitHub Pages.** Run
  `python3 ../../catalog/tools/wrap_for_pages.py --unwrap index.html` before republishing it as an
  Artifact, and wrap it again afterwards. See `catalog/PUBLISHING.md`.

The two data sources are catalogued in `projects/headwaters/sources/` as `md-imap` and
`montgomery-county-gis`, with their gotchas and runnable probes.
