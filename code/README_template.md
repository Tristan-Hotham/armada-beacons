# Fire on the Hills

How fast could fire carry the news of the Armada? Line of sight between {{n_sites|int}} hills in Britain that carry the word "beacon" in their name, the networks they form, the spread of a fire lit at the Lizard, and where the chain breaks.

**Interactive version:** https://tristan-hotham.github.io/armada-beacons/

**Paper:** https://doi.org/10.5281/zenodo.23688581

This repository holds the interactive page, the site and sight-line data and the analysis code for the data study *Fire on the Hills: How Fast Could the Armada Beacons Carry the News?* by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349). Companion study: [Within Sight](https://tristan-hotham.github.io/within-sight/), whose line-of-sight code this reuses.

## Headline results

- {{n_sites|int}} beacon sites from place names: {{n_by_country.England|int}} in England, {{n_by_country.Wales|int}} in Wales and {{n_by_country.Scotland|int}} in Scotland. {{n_beacon_hill|int}} are plain "Beacon Hill".
- Within 50 km, {{main.share_sees_any|pct0}} of sites can see another beacon site's fire, but the sites form {{main.n_components|int}} separate networks. The largest has {{main.giant|int}} sites ({{main.share_giant|pct0}}), across the South West, Wessex and the West Midlands.
- A fire lit at Roskruge Beacon, the beacon site nearest the Lizard, reaches only {{main.reached_from_lizard|int}} sites on beacon names alone, all in Cornwall, within {{main.max_hops|int}} hops. Crossing into Devon would need a {{bridged.malvern.gaps.0.km|f1}} km sight line.
- No chain of beacon names reaches London, York or Berwick, even with sight lines of 150 km.
- With one possible relay hill per 10 km square added (a model, not known sites), the fire reaches London in {{filled.50.targets.london.hops|int}} hops, York in {{filled.50.targets.york.hops|int}}, Beacon Fell (Lancashire) in {{filled.50.targets.beacon_fell.hops|int}} and Berwick in {{filled.50.targets.berwick.hops|int}}. At an assumed 5, 15 or 30 minutes a hop, London is {{filled.50.targets.london.minutes_fast|dur}}, {{filled.50.targets.london.minutes_central|dur}} or {{filled.50.targets.london.minutes_slow|dur}} away.
- Only {{filled.50.targets.london.min_relays|words}} relay hills are needed to join the named beacons from the Lizard to London ({{filled.50.targets.london.min_relay_hops|int}} hops).
- The top chokepoint in the name network is Beacon Batch on the Mendips (betweenness {{chokepoints.0.betweenness|raw}}).

## Files

- `index.html`: the interactive page (Leaflet map with an animated fire, charts).
- `header.png`: social card.
- `data/beacon_sites.csv`: the {{n_sites|int}} beacon sites, with source, original point, the point moved to the highest ground within 250 m, and elevation.
- `data/excluded_candidates.csv`: every candidate left out, with the reason.
- `data/beacon_network.csv`: per site, links, network, hops and minutes from the Lizard (names only, and with gaps filled), betweenness and cut points.
- `data/sightlines.csv`: every ordered pair of beacon sites up to 70 km apart, and every visible pair up to 150 km, with visibility for a 5 m fire, a 10 m fire and from the original name points.
- `data/relay_hills.csv`: the {{filled.n_relays|int}} relay hills (highest ground per 10 km square) and their hops from the Lizard.
- `data/paths.csv`: the routes from the Lizard to each destination.
- `data/results.json`: every number quoted on the page, in the paper and in the blog post.
- `code/`: Python scripts. Run in order: `01_sites.py`, `02_visibility.py`, `03_relays.py`, `04_network.py`, `05_build_site.py`, `06_header.py`. `dem.py` holds the elevation lookup and line-of-sight function (from Within Sight). The elevation tiles are not included (see below); point `DEM_BIN` and `DEM_IDX` at your copy.

## Method in brief

Line of sight from a watcher's eye 2 m above the ground at one site to the top of a fire 5 m above the ground at another, sampling the ground every 45 m with bilinear interpolation, with earth curvature and standard refraction (k = 0.13), up to 50 km (30, 70 and 100 km as sensitivity). A fire passes from A to B when A's fire is visible from B. The fire starts at the beacon site nearest Lizard Point and spreads by fewest hops. Time per hop is an assumption (5, 15 or 30 minutes), not a measured figure.

Caveats: a beacon name is evidence that a fire was lit or planned there at some time, not proof of 1588; many real beacons left no such name; the relay hills are a model; a line of sight is not the same as seeing a fire; the 90 m elevation model smooths summits and has no trees or buildings.

## Sources and licence

- Place names: Ordnance Survey, OS Open Names. Contains OS data © Crown copyright and database right 2026. Open Government Licence v3.0.
- Two beacon sites (Pinhaw Beacon, Penhill Beacon): © OpenStreetMap contributors, Open Database Licence 1.0. Wikidata (CC0) was checked; its beacons are navigation marks and none is used.
- Elevation: AWS Terrain Tiles by Mapzen/Tilezen (terrarium encoding, zoom 10), built from sources including SRTM, GMTED2010, ETOPO1 and national datasets. Full attribution: https://github.com/tilezen/joerd/blob/master/docs/attribution.md
- Sighting date: Royal Museums Greenwich, "Elizabeth I and the Spanish Armada", https://www.rmg.co.uk/stories/topics/elizabeth-i-spanish-armada
- Base map tiles on the page: Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community. Map library: Leaflet.

The derived data and the page text are released under CC BY 4.0, except the rows derived from OpenStreetMap, which remain under the ODbL. Code is MIT (see `LICENSE`).

## Citation

Hotham, T. (2026). *Fire on the Hills: How Fast Could the Armada Beacons Carry the News?* Zenodo. https://doi.org/10.5281/zenodo.23688581

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
