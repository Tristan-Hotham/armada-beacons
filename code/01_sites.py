"""Step 1: candidate beacon sites from place names.

Sources
- OS Open Names (OGL v3): every landform whose name contains "beacon"
  (Hill Or Mountain, Spot Height, plus the headland "Fire Beacon Point").
  Woodland, farmland, water, coastal rocks and settlements are left out, and so
  is the mountain range "Brecon Beacons".
- OpenStreetMap (ODbL), historic=beacon features from the shared UK bundle,
  kept only when named "... Beacon" and not dated to modern times.
- Wikidata items classed as beacons (shared UK bundle) were all checked and are
  navigation marks, harbour lights or unclear, so none is used; they are listed
  in data/excluded_candidates.csv with the reason.

Each kept point is moved to the highest ground within 250 m (OS name points
sit on the label position, not always the summit), using the same elevation
tiles as Within Sight.
Writes data/beacon_sites.csv and data/excluded_candidates.csv.
"""
import os, re, json
import numpy as np, pandas as pd
from dem import DEM, haversine

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
OSN = "/home/claude/hist/osnames_gb.tsv"
BUNDLE = "/home/claude/hist/_data8/uk_bundle_wikidata_osm.json"
SNAP_R = 250.0

o = pd.read_csv(OSN, sep="\t", dtype=str, keep_default_na=False)
hit = o.name1.str.contains("beacon", case=False) | o.name2.str.contains("beacon", case=False)
c = o[hit].copy()
keep_types = {"Hill Or Mountain", "Spot Height"}
c["keep"] = c.local_type.isin(keep_types) | ((c.local_type == "Coastal Headland") & c.name1.str.contains("Fire Beacon"))
c["name"] = np.where(c.name1.str.contains("beacon", case=False), c.name1, c.name2 + " (" + c.name1 + ")")
c["lat"] = c.lat.astype(float); c["lon"] = c.lon.astype(float)
excl = []
for _, r in c[~c.keep].iterrows():
    excl.append(dict(source="OS Open Names", name=r["name"], kind=r.local_type, lat=r.lat, lon=r.lon,
                     reason="not a hill or summit feature (woodland, land cover, water, coastal rock, settlement or range)"))
s = c[c.keep].copy()
s["source"] = "OS Open Names"; s["source_id"] = ""
s["county"] = np.where(s.county != "", s.county, s.district)
s = s[["source", "source_id", "name", "local_type", "lat", "lon", "county", "country"]]

# OpenStreetMap historic=beacon
B = json.load(open(BUNDLE))
osm = {}
for f in B["osm_uk_features"]:
    if f.get("hist") == "beacon":
        osm[f["osm"]] = f
add = []
for k, f in osm.items():
    nm = f["name"]
    modern = bool(f["start"]) and f["start"][:4] >= "1800"
    if nm and re.search(r"beacon", nm, re.I) and not modern:
        add.append(dict(source="OpenStreetMap historic=beacon", source_id=k, name=nm, local_type="historic=beacon",
                        lat=f["lat"], lon=f["lon"], county="", country="England"))
    else:
        excl.append(dict(source="OpenStreetMap historic=beacon", name=nm or "(unnamed)", kind="historic=beacon " + (f["mm"] or ""),
                         lat=f["lat"], lon=f["lon"], reason="modern commemorative beacon (start date " + f["start"] + ")" if modern else
                         ("unnamed, cannot be checked" if not nm else "name does not say beacon")))
# Wikidata beacon classes: all checked by hand, none is a hill fire beacon
for r in B["wd_structures_tsv"].split("\n")[1:]:
    t = r.split("\t")
    if len(t) < 5 or "eacon" not in t[3]: continue
    m = re.search(r"POINT\(([-\d.]+) ([-\d.]+)\)", t[4])
    excl.append(dict(source="Wikidata", name=t[1].split('"')[1], kind=t[3].split('"')[1], lat=float(m.group(2)), lon=float(m.group(1)),
                     reason="navigation mark, harbour light, daymark or unclear; not a hill fire beacon"))
s = pd.concat([s, pd.DataFrame(add)], ignore_index=True)

# de-duplicate points within 1 km (same hill under two names or two sources); keep OS hill names first
pri = {"Hill Or Mountain": 0, "historic=beacon": 1, "Spot Height": 2, "Coastal Headland": 3}
s["pri"] = s.local_type.map(pri)
s = s.sort_values(["pri", "lat"]).reset_index(drop=True)
drop = set()
for i in range(len(s)):
    if i in drop: continue
    d = haversine(s.lat[i], s.lon[i], s.lat.values, s.lon.values)
    for j in np.where((d < 1000) & (np.arange(len(s)) > i))[0]:
        if j not in drop:
            drop.add(j); excl.append(dict(source=s.source[j], name=s.name[j], kind=s.local_type[j], lat=s.lat[j], lon=s.lon[j],
                                          reason=f"duplicate of {s.name[i]} ({d[j]:.0f} m away)"))
            if not s.county[i] and s.county[j]: s.loc[i, "county"] = s.county[j]
s = s.drop(index=list(drop)).reset_index(drop=True)

# fill county for OSM points from nearest OS name
for i in s.index[s.county == ""]:
    d = haversine(s.lat[i], s.lon[i], o.lat.astype(float).values, o.lon.astype(float).values)
    j = int(np.argmin(d)); s.loc[i, "county"] = o.county.iloc[j] or o.district.iloc[j]; s.loc[i, "country"] = o.country.iloc[j]

# snap to highest ground within SNAP_R
dem = DEM()
g = np.arange(-SNAP_R, SNAP_R + 1, 15.0)
ox, oy = [a.ravel() for a in np.meshgrid(g, g)]
inside = ox ** 2 + oy ** 2 <= SNAP_R ** 2
ox, oy = ox[inside], oy[inside]
gx, gy = dem.to_pix(s.lat.values, s.lon.values)
ps = 40075016.686 * np.cos(np.radians(s.lat.values)) / (1024 * 256)
X = gx[:, None] + ox[None] / ps[:, None]; Y = gy[:, None] + oy[None] / ps[:, None]
zz = dem.bilinear(X, Y); k = zz.argmax(1); i = np.arange(len(s))
sl, so = dem.from_pix(X[i, k], Y[i, k])
s["elev_point_m"] = np.round(dem.elev(s.lat.values, s.lon.values), 1)
s["snap_lat"] = np.round(sl, 5); s["snap_lon"] = np.round(so, 5); s["elev_m"] = np.round(zz[i, k], 1)
s["snap_shift_m"] = np.round(haversine(s.lat.values, s.lon.values, sl, so), 0)
s = s.sort_values(["country", "lat"], ascending=[True, True]).reset_index(drop=True)
s.insert(0, "site_id", [f"B{n:03d}" for n in range(1, len(s) + 1)])
s.drop(columns=["pri"]).to_csv(os.path.join(ROOT, "data", "beacon_sites.csv"), index=False)
pd.DataFrame(excl).to_csv(os.path.join(ROOT, "data", "excluded_candidates.csv"), index=False)
print(len(s), "sites;", len(excl), "excluded")
print(s.groupby("country").size()); print(s.source.value_counts()); print(s.local_type.value_counts())
print("median snap shift", s.snap_shift_m.median(), "elev median", s.elev_m.median())
