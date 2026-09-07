# 🏘️ Broke Ground

**Every parcel in Montgomery County, placed by the year its building went up — drag the year and watch a county fill in.**

→ **[Open it](https://tnriley.github.io/broke-ground/)**

Maryland's tax roll carries a four-character column called YEARBLT. This page takes all 348,669 Montgomery County parcels, sorts them by it, and draws them: scrub from 1700 to 2025 and the county assembles itself, buildings appearing where and when they actually went up. Click any dot for its address, what the assessor calls it, its floor area and lot, and a link straight through to the state's own record. Where the Maryland Historical Trust has surveyed a building, the page joins its scanned survey form to the parcel. Three findings fall out of it: the building line moved from 6.6 miles out of Washington in the 1920s to 18.4 by the 1990s and then stopped dead; new construction inside what became the Agricultural Reserve fell 62% in the 1980s while the rest of the county had its biggest building decade ever; and the median new detached house went from 1,382 square feet in the 1950s to 3,809 today.

## Running it

One self-contained HTML file. No build step, no server, no network access at runtime — open `index.html` in a browser, or serve the directory with any static host.

```bash
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Rebuilding it from scratch

[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data sources and their quirks, the processing decisions, the page's structure and interactions, and a table of expected values to check the result against.

## Source

The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.

## Data

- **[MDProperty View parcel points (SDAT assessment attributes), Maryland iMAP](https://mdgeodata.md.gov/imap/rest/services/PlanningCadastre/MD_PropertyData/MapServer/0)** — Maryland open data — public record, attribution requested
- **[Maryland Inventory of Historic Properties, Maryland Historical Trust](https://mdgeodata.md.gov/imap/rest/services/Historic/MD_InventoryHistoricProperties/MapServer/0)** — Maryland open data — public record, attribution requested
- **[Agricultural Reserve zone boundary, Montgomery County MC Atlas](https://mcmaps.org/server11/rest/services/Overlays/MCAtlas_Boundaries/MapServer/10)** — Montgomery County open data
- **[County, municipal and hydrography boundaries, Maryland iMAP](https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_PoliticalBoundaries/MapServer)** — Maryland open data
- **[Metro station locations, Montgomery County GIS](https://gis.montgomerycountymd.gov/arcgis/rest/services/General/metro_stations/MapServer/0)** — Montgomery County open data

Every figure on the page is computed from the data shipped with it. Check the page's own methods panel for how each number is derived and where it should not be pushed.

## Built with

vanilla JS, canvas density accumulation buffer, gzipped column store + DecompressionStream, year-sorted prefix scrubbing, hand-built SVG figures, ArcGIS REST paged harvest.

## Licence

Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.

---

Part of [Quick Projects](https://github.com/TNRiley/quick-projects) — one self-contained thing, built in one session. First published 2026-09-07.
