"""Step 3: an idealised "filled" network of possible relay hills.

The beacon names on the modern map are only the beacons whose name survived
and that OS Open Names happens to carry. To ask how many beacons are missing,
I add one candidate relay point per 10 km square of the British National Grid:
the highest ground in that square on the elevation tiles (sampled every 100 m).
Squares whose highest point is below 5 m are treated as sea and dropped. The
grid covers Great Britain south of northing 700 km (roughly the Forth); the
beacon sites further north keep only their name-based links.

Then line of sight for every ordered pair of nodes (beacon sites and relay
hills) up to 50 km apart, with the same rule as step 2 (2 m watcher, 5 m fire,
curvature and refraction).
Writes data/relay_hills.csv and work/filled_pairs.npz.
"""
import os, time
import numpy as np, pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from dem import DEM, los, haversine, R_EARTH

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
WORK = os.path.join(ROOT, "work")
CELL, STEP, NMAX, MAXD = 10000, 100, 700000, 50000.0
EYE, FIRE = 2.0, 5.0

t0 = time.time()
dem = DEM()
to_ll = Transformer.from_crs(27700, 4326, always_xy=True)
xs = np.arange(0, 700000, CELL); ys = np.arange(0, NMAX, CELL)
off = np.arange(STEP / 2, CELL, STEP)
ox, oy = [a.ravel() for a in np.meshgrid(off, off)]
rows = []
for y0 in ys:
    X = (xs[:, None] + ox[None]).ravel(); Y = (y0 + oy[None] + 0 * xs[:, None]).ravel()
    lon, lat = to_ll.transform(X, Y)
    z = dem.elev(lat, lon).reshape(len(xs), -1)
    k = z.argmax(1)
    for i, x0 in enumerate(xs):
        if z[i, k[i]] < 5: continue
        rows.append(dict(cell_e=int(x0), cell_n=int(y0), lat=float(lat.reshape(len(xs), -1)[i, k[i]]), lon=float(lon.reshape(len(xs), -1)[i, k[i]]), elev_m=round(float(z[i, k[i]]), 1)))
rh = pd.DataFrame(rows)
rh.insert(0, "relay_id", [f"R{n:04d}" for n in range(1, len(rh) + 1)])
rh["lat"] = rh.lat.round(5); rh["lon"] = rh.lon.round(5)
rh.to_csv(os.path.join(ROOT, "data", "relay_hills.csv"), index=False)
print(len(rh), "relay hills", round(time.time() - t0, 1))

S = pd.read_csv(os.path.join(ROOT, "data", "beacon_sites.csv"))
lat = np.r_[S.snap_lat.values, rh.lat.values]; lon = np.r_[S.snap_lon.values, rh.lon.values]
z = dem.elev(lat, lon).astype(np.float64)
la, lo = np.radians(lat), np.radians(lon)
xyz = np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)] * R_EARTH
p = cKDTree(xyz).query_pairs(MAXD * 1.001, output_type="ndarray")
d = haversine(lat[p[:, 0]], lon[p[:, 0]], lat[p[:, 1]], lon[p[:, 1]]); keep = d <= MAXD
p, d = p[keep], d[keep]
p = np.vstack([p, p[:, ::-1]]); d = np.r_[d, d]
gx, gy = dem.to_pix(lat, lon); a, b = p[:, 0], p[:, 1]
v = los(dem.bilinear, gx[a], gy[a], z[a], gx[b], gy[b], z[b], d, FIRE, EYE)
np.savez_compressed(os.path.join(WORK, "filled_pairs.npz"), pairs=p[v].astype(np.int32), dist=d[v].astype(np.float32), n_beacons=len(S))
print(len(p), "ordered pairs,", int(v.sum()), "visible", round(time.time() - t0, 1), "s")
