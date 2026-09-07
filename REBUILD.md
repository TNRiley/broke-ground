# Rebuilding Broke Ground from scratch

You are an LLM with a shell and no other context. This file is enough to rebuild the project.

---

## 1. What this is

One page that draws **every tax parcel in Montgomery County, Maryland — 348,669 of them — coloured
by the year the assessor recorded its building as finished**, with a scrubber that runs 1700 → 2025
so the county assembles itself. A second source, the Maryland Inventory of Historic Properties, is
joined to it by position so a surveyed building shows its scanned survey form beside its tax record.

It exists to show one effect: **the county's building line advanced steadily outward from
Washington for seventy years and then stopped.** The median distance of a decade's new construction
from the Zero Milestone goes 6.6 mi (1920s) → 18.4 mi (1990s) → 17.3 mi (2020s). Everything else on
the page hangs off that.

The whole thing is generated from one four-character column, `YEARBLT`. Nothing on the page is
typed by hand — every number in the prose is computed by `src/build_payload.py` and injected.

---

## 2. Data sources, with the quirks that will bite

### Parcels — Maryland iMAP, MDProperty View "Parcel Points"

```
https://mdgeodata.md.gov/imap/rest/services/PlanningCadastre/MD_PropertyData/MapServer/0
```

ArcGIS REST, no auth. `where=JURSCODE='MONT'` is 348,669 features; ~105 MB of NDJSON once
harvested with geometry, about 3 minutes at `maxRecordCount=2000` and a 0.4 s gap (175 requests).

| trap | what happens | what to do |
|---|---|---|
| **`YEARBLT` is a `STRING(4)`, not a number** | `where=YEARBLT > 0` → HTTP 400, `details: []`, no hint | compare as a string, cast client-side |
| `geodata.md.gov` vs **`mdgeodata.md.gov`** | the first served a "Site Maintenance" page all of 2026-09-07 | use `mdgeodata.md.gov`. A third live host, `mdpgis.mdp.state.md.us`, carries Dept of Planning services |
| paging without `orderByFields` | records repeat or vanish between pages, silently | always pass `orderByFields=OBJECTID` with `resultOffset` |
| `SDATWEBADR` is a 140-char URL × 348k | 48 MB of redundancy | drop it. `ACCTID` = county(2)+district(2)+account(8) rebuilds it exactly |
| `DESCSTYL` is **structural, not architectural** | no Colonial/Rambler/Cape Cod; it is "2 Story With Basement", "Townhouse-Center Unit", "Split Foyer" | still the right typology axis — detached / townhouse / condo / apartment falls out of it |
| ~28,900 parcels have **no** `YEARBLT` | land with no building: parks, road parcels, vacant lots | keep them, sort them last, say so on the page |

### Historic properties — Maryland Inventory of Historic Properties (MHT)

```
https://mdgeodata.md.gov/imap/rest/services/Historic/MD_InventoryHistoricProperties/MapServer/0
```

`where=COUNTY='Montgomery'` → 2,829 polygons with `Nam`, `MIHPNO`, `FULLADDR`, `PDFLINK`.

| trap | what to do |
|---|---|
| **`returnCentroid=true` is accepted and silently ignored** by MapServer — a loop reading `feature.centroid.x` yields **zero records and no error** | request geometry with `maxAllowableOffset=0.0005` and average the outer ring yourself |
| **`PDFLINK` contains a literal space and semicolon**: `.../Montgomery/M; 17-53.pdf` — 404s unencoded | percent-encode the space (`%20`). It then returns a real multi-MB scanned survey form |

### Context layers

- County / municipal boundaries: `.../Boundaries/MD_PoliticalBoundaries/MapServer/1` and `/2`
  (municipalities filter on **`JURSCODE='MONT'`**, field is `MUN_NAME` — `COUNTY='Montgomery'`
  returns 0 features here).
- Hydrography: `.../Hydrology/MD_Waterbodies/MapServer/0` (streams) and `/1` (lakes).
- **Agricultural Reserve**: `https://mcmaps.org/server11/rest/services/Overlays/MCAtlas_Boundaries/MapServer/10`.
  The state's generalized zoning has **no agriculture category for Montgomery** — the Reserve hides
  inside 106,821 acres of "RURAL LOW DENSITY RESIDENTIAL", so use the county's own atlas.
- Metro stations: `https://gis.montgomerycountymd.gov/arcgis/rest/services/General/metro_stations/MapServer/0`.

### Machine note

`python3` here resolves to `/usr/local/bin/python3` (python.org), whose OpenSSL has **no CA
bundle** — every `urllib` HTTPS call dies with `CERTIFICATE_VERIFY_FAILED` while `curl` works.
Run everything with **`/usr/bin/python3`**, or load `/etc/ssl/cert.pem` explicitly.

---

## 3. Processing decisions, and why

- **Distance origin is the Zero Milestone**, 38.8946 N, −77.0365 W — the point US road distances to
  Washington have been reckoned from since 1923. Equirectangular approximation with a
  `cos(lat)` correction on longitude; crow-flies, not driving distance. Say so on the page.
- **Rows are sorted by year ascending, unknown last.** This is load-bearing: it makes the year
  scrubber a *prefix* (`draw [0, upperBound(year))`) rather than a filter over 348k rows every
  frame. It also means the newest building naturally wins a shared pixel. Do not re-sort spatially.
- **Columns, not rows.** One typed array per field, concatenated, then gzipped. gzip finds far more
  redundancy down a column of style codes than across a row of mixed types.
  13.6 MB raw → **4.7 MB gzip → 6.2 MB base64**, inflated in-browser with `DecompressionStream`.
- **`ACCTID` repacked** to district(`u8`) + account(`u32`) — 5 bytes instead of 12 chars of
  incompressible digits, saving 2.4 MB. The SDAT URL is rebuilt from the parts in the page.
- **Byte alignment:** column offsets are usually not multiples of 4, so `new Int32Array(blob.buffer, o)`
  throws. Slice the bytes first — `Uint8Array.slice()` returns a fresh buffer starting at 0.
- **Year → colour is quantile-anchored, not linear.** A linear 1700–2025 ramp puts almost every
  building in the top three stops. Anchors are computed from the built stock's own distribution
  (`buildRampAnchors`), and the legend prints the anchor years so the nonlinearity is visible.
- **MHT join:** nearest parcel within **60 m**, at most one parcel each. The threshold is a
  judgement — tighter and a survey pinned to a driveway misses its house, looser and a farmstead
  claims its neighbour. 2,041 of 2,829 join; the rest are districts, parks and canal segments with
  no single lot, and are drawn as markers only.

---

## 4. The page

Surveyor's-plat treatment. **Public Sans** for body (the US Web Design System's typeface — the page
is made entirely of government records), **Saira Condensed** display, **IBM Plex Mono** for figures.
Cool drafting-linen neutrals; a single-hue ochre ramp for year (tax-map convention); teal accent for
interaction and historic markers. Categorical palette for the charts is validated in both themes
(`#B4741C,#006E96,#B3243B,#7B3BA8,#3C7A2B` light / `#BC821F,#2C93BE,#D14E60,#A473D4,#54A03B` dark).
Full-bleed: map + 356 px right rail, scrubber beneath, findings below in a wide grid.

Interactions that matter: the **year scrubber is the completions histogram** (drag across the bars);
play runs the time-lapse; eight typology facets where the first click *isolates*; search over 10,951
streets / 1,837 subdivisions / 2,829 historic names; click-to-select with a full detail card and two
link-outs. In-page Auto/Light/Dark applied pre-paint, and a Plain English toggle.

The map renders by **accumulating parcels into a pixel buffer** (count + newest-year per pixel) and
then colourising only the touched pixels, so density is honest instead of last-dot-wins. The vector
base layer is rasterised once and cached, keyed on view + layers + theme.

**The base map is the finding.** Drawing only where buildings are draws the county outline, and the
Agricultural Reserve appears as a void in the upper county before any overlay is switched on.

---

## 5. Verification table — real expected values

If your rebuild disagrees with these, you have a parse error.

| check | expected |
|---|---|
| Parcels returned for `JURSCODE='MONT'` | **348,669** |
| Parcels with a usable `YEARBLT` (1700–2026) | **319,767** |
| Parcels with no building recorded | **28,902** |
| Distinct styles / subdivisions / streets / cities | **133 / 1,837 / 10,951 / 33** |
| Buildings completed, 1980s (the peak decade) | **69,426** |
| Buildings completed, 2020s (partial) | **7,595** |
| Median distance from Zero Milestone, 1920s | **6.6 mi** |
| Median distance, 1990s (the peak) | **18.41 mi** |
| Median distance, 2020s | **17.28 mi** |
| New buildings inside the AR zone, 1970s → 1980s | **1,745 → 660** (−62%) |
| Outside the AR zone, same two decades | **42,794 → 68,766** (+61%) |
| Parcels inside the AR zone | **7,974** |
| Median new detached house, 1950s | **1,382 sq ft** |
| Median new detached house, 2020s | **3,809 sq ft** |
| Detached share of new buildings, 1930s → 2020s | **95% → 39%** |
| Townhouse share, 2020s | **48%** |
| Kensington postal area, total / 1950s | **7,043 / 3,416** |
| Historic properties in the county / joined to a parcel | **2,829 / 2,041** |
| Oldest record with an address | **1700, 15818 Seneca Run Ct, Germantown** |
| `YEARBLT == 1900` count (the placeholder spike) | **544**, ~10× its neighbouring years |
| Payload | 13.6 MB raw → 4.7 MB gzip → 6.2 MB base64; `index.html` ≈ 7.1 MB |

Sanity landmarks: 4215 Knowles Ave, Kensington resolves to subdivision **"Kensington (Warners Add)"**,
the town's original 1890s plat. `KNOWLES AVE` has **49** parcels.

---

## 6. The methodological trap, with the wrong answer and the right one

**I expected the 1980 Agricultural Reserve to show up as a collapse in the Reserve's *share* of new
construction. It does not, and reporting that share would have said the Reserve did nothing.**
AR parcels are ~1% of the county's stock before 1980 and ~1–2% after — because the denominator is
the whole county, and the Reserve is a small, already-rural part of it. The intervention is only
legible in **absolute counts set against the county's own boom**: 1,745 → 660 inside (−62%) while
everywhere else went 42,794 → 68,766 (+61%) during the largest building decade the county has ever
had.

**Generalise it: a share-of-total can hide a real policy effect completely. Choose the denominator
the decision actually acted on.**

A second guess also failed and is worth not re-making: I expected construction to visibly "fold
back" inside the old frontier once land ran out. The share of new buildings inside the 1970 build
line goes 50% → 39% → 41% — no fold. The page reports the *stall* in the median distance, which is
what the data supports.

---

## 7. What the page must say about itself

Non-negotiable, all present in the Methods section:

- **The year is an administrative record, not a construction record.** It clusters on placeholders —
  1900 alone carries 544 buildings, ~10× its neighbours. Treat anything before ~1920 as an estimate.
  A major renovation can reset the year, so the oldest stock is *under*-counted.
- **A dot is a tax account, not a building.** A 200-unit condominium contributes 200 dots at one
  point; a tower reads as one dot while a street of houses reads as fifty. "Buildings" is shorthand.
- **Condominium describes ownership today, not construction.** 1960s garden apartments converted in
  the 1970s carry a 1960s year and a condominium code — that is most of the 1960s condo block.
- **The AR boundary is today's zone applied backwards.** It answers "what is inside the line now",
  not "what was legal then"; the 1980 RDT boundary was redrawn on its way to today's AR.
- **This is a census of what still stands and is still assessed.** It cannot see demolitions, so the
  thinness of the early decades is partly survival, not history.
- **Nothing here is about people.** It counts structures, not households, and says nothing about who
  was permitted to buy them — the racial covenants that shaped which of these subdivisions sold to
  whom are in the deeds, not in this file.

---

## 8. Commands

See `src/README.md`. In short:

```bash
/usr/bin/python3 src/harvest.py && /usr/bin/python3 src/fetch_context.py \
  && /usr/bin/python3 src/fetch_mihp.py && /usr/bin/python3 src/build_payload.py \
  && /usr/bin/python3 src/inject.py
```

`src/explore.py` and `src/explore2.py` are the exploratory passes behind §5 and §6 — run them to
check the numbers rather than trusting the page. The two sources are catalogued in
`projects/headwaters/sources/` as `md-imap` and `montgomery-county-gis`, with runnable probes.
