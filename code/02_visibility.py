"""Step 2: can a fire on one beacon site be seen from another?

For every ordered pair of beacon sites up to 150 km apart, trace a line of sight
from a watcher's eye 2 m above the ground at the receiving site to the top of a
fire 5 m above the ground at the sending site, over the AWS Terrain Tiles (zoom
10), sampling every 45 m, with earth curvature and standard refraction
(k = 0.13). This is the line-of-sight code from Within Sight (dem.py).
Sensitivity runs: a 10 m fire (a tall blaze or smoke column), and the original
name points instead of the highest ground within 250 m.
Writes work/pairs.npz.
"""
import os, time
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from dem import DEM, los, haversine, R_EARTH

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
WORK = os.path.join(ROOT, "work"); os.makedirs(WORK, exist_ok=True)
MAXD = 150000.0
EYE, FIRE, FIRE_HI = 2.0, 5.0, 10.0


def xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)] * R_EARTH


if __name__ == "__main__":
    t0 = time.time()
    s = pd.read_csv(os.path.join(ROOT, "data", "beacon_sites.csv"))
    dem = DEM()
    p = cKDTree(xyz(s.snap_lat.values, s.snap_lon.values)).query_pairs(MAXD * 1.001, output_type="ndarray")
    # ordered pairs: (fire site a, watcher b) both ways
    p = np.vstack([p, p[:, ::-1]]); p = p[np.lexsort((p[:, 1], p[:, 0]))]
    out = {"pairs": p.astype(np.int32)}
    for tag, la, lo in [("snap", s.snap_lat.values, s.snap_lon.values), ("raw", s.lat.values, s.lon.values)]:
        z = dem.elev(la, lo).astype(np.float64)
        d = haversine(la[p[:, 0]], lo[p[:, 0]], la[p[:, 1]], lo[p[:, 1]])
        gx, gy = dem.to_pix(la, lo); a, b = p[:, 0], p[:, 1]
        out["dist_" + tag] = d.astype(np.float32)
        out["v_" + tag] = los(dem.bilinear, gx[a], gy[a], z[a], gx[b], gy[b], z[b], d, FIRE, EYE)
        if tag == "snap":
            out["v_hi"] = los(dem.bilinear, gx[a], gy[a], z[a], gx[b], gy[b], z[b], d, FIRE_HI, EYE)
        print(tag, "done", round(time.time() - t0, 1), "s")
    np.savez_compressed(os.path.join(WORK, "pairs.npz"), **out)
    d = out["dist_snap"]
    for km in (30, 50, 70, 100, 150):
        m = d <= km * 1000
        print(km, "km ordered pairs", m.sum(), "visible", out["v_snap"][m].sum(), "hi", out["v_hi"][m].sum(), "raw", out["v_raw"][(out["dist_raw"] <= km * 1000)].sum())
