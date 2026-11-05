# Deep Time Map

An interactive Mercator map of the fossil record from 4,000 million years ago to today, built in one Claude session on 4 November 2026.

## Folders

- `versions/v1` … `versions/v19`: each published version of the page (`index.html` plus its data files `fossils.json` and `land.json`).
  - v1: icons scaled by abundance, time slider
  - v2: hover tooltips, dominance patches
  - v3: community descriptions with rock formation
  - v4: genus-named faunas, land and sea separated
  - v5: toggles, boundary lines, mass extinctions
  - v6: plants, algae, fungi, cyanobacteria, stromatolites, plankton
  - v7: compressed Precambrian timeline back to 4,000 Ma
  - v8: smoother boundary lines
  - v9: climate: air and sea temperature, CO₂, oxygen, ice caps
  - v10: genus search that jumps to a genus's peak and heartland
  - v11: see-through panels
  - v12: picking one group hides everything else, patches included
  - v13: dinosaurs grouped into 16 clades, with teeth, eggs and tracks placed in their clades
  - v14: icon size compared with the richest site of each kind at that moment
  - v15: minimisable group panel and compact readout
  - v16: Cenozoic “dinosaur” records reclassified as birds; time window stops at mass extinctions
  - v17: stem-and-leaf icon for early land plants
  - v18: continents and fossils where they were at the time (PALEOMAP plate model)
  - v19: "Who lived here" panel overlays the timeline; new default settings (latest)
- `build/`: the Python scripts that build `fossils.json` and the HTML templates (`__ICONS__` is replaced with `icons.json`). The scripts expect the source data at the paths used in the session and will need their paths edited to rerun.
- `build/build_paleo.py` rotates every fossil and today's coastlines to their ancient positions with pygplates and the PALEOMAP model (Scotese 2016), writing `paleo_pts.json` and `land/<age>.json`.
- `build/build_climate.py` builds `climate.json` from PhanDA (Judd et al. 2024) and GEOCARBSULFOR (Krause et al.) outputs.
- `data/`: data downloaded during the session.
  - `pbdb_plants_microbes.gz`: plants, algae, fungi, cyanobacteria and plankton from the Paleobiology Database (packed binary; see `build_data_v6.py` for the format).
  - `dino_clades.json`: each dinosaur genus with its clades, from the Paleobiology Database classification (used by `build_data_v13.py`).
  - `pbdb_precambrian.gz`: Precambrian Paleobiology Database occurrences plus stromatolite-bearing units from Macrostrat (gzipped JSON rows).

## Viewing locally

Browsers block a page opened straight from disk (`file://`) from loading its data files. To view a version locally, run a small web server in its folder, for example:

    cd versions/v19
    python -m http.server 8000

then open http://localhost:8000.

## Sources

Plate model: PALEOMAP (C. R. Scotese 2016), via the public GPlates files. Climate: PhanDA (Judd et al. 2024, Apache 2.0) and GEOCARBSULFOR (Krause et al. 2018, 2022 runs); Precambrian ranges after Catling & Zahnle 2020 and Lyons et al. 2014. Fossils: Paleobiology Database (CC BY 4.0), via exports in the petra, dinotime and naheim/PBDB_Scripts GitHub projects and direct API downloads; PaleoReefs via the palaeoverse R package; Macrostrat; Natural Earth coastlines via world-atlas; game-icons.net silhouettes (CC BY 3.0); mass extinction figures from Barnosky et al. 2011 via Our World in Data.

`build/standalone.py` adds the full HTML header (doctype, character set, phone viewport) to each page in `versions/`, so the pages behave the same on GitHub Pages as they do as Claude artifacts. Run it after copying in a new version.
