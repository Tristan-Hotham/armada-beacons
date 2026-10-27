"""Step 4: the beacon network, the fire's spread from the Lizard, chokepoints and gaps.

A directed link a -> b means a fire at site a can be seen from site b (step 2).
The fire starts at the beacon site nearest Lizard Point and spreads one hop at
a time. Time per hop is an assumption, not a measured figure: 5, 15 or 30
minutes for a watcher to see the fire, light their own and for it to grow
visible. With a fixed delay per hop the quickest route is the route with the
fewest hops.
Writes data/results.json, data/beacon_network.csv, data/sightlines.csv,
data/paths.csv, adds hop counts to data/relay_hills.csv, and writes
work/site.json (compact data for the page).
The filled network (beacon sites plus relay hills from step 3) answers how
far and how fast the fire could go if the gaps had beacons too.
"""
import os, json, math
import numpy as np, pandas as pd, networkx as nx
from dem import haversine

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data"); WORK = os.path.join(ROOT, "work")
S = pd.read_csv(os.path.join(DATA, "beacon_sites.csv"))
P = np.load(os.path.join(WORK, "pairs.npz"))
N = len(S)
DELAYS = {"fast": 5, "central": 15, "slow": 30}  # minutes per hop (assumption)
MAIN_KM = 50

# reference places from OS Open Names (name, type) so the targets are sourced
osn = pd.read_csv("/home/claude/hist/osnames_gb.tsv", sep="\t", dtype=str, keep_default_na=False)
def osref(name, county, ltype):
    r = osn[(osn.name1 == name) & (osn.county == county) & (osn.local_type == ltype)].iloc[0]
    return float(r.lat), float(r.lon)
REF = {"lizard": ("Lizard Point", "Cornwall", "Coastal Headland"), "london": ("London", "Greater London", "City"),
       "york": ("York", "York", "City"), "carlisle": ("Carlisle", "Cumberland", "City"),
       "berwick": ("Berwick-upon-Tweed", "Northumberland", "Town"), "plymouth": ("Plymouth", "City of Plymouth", "City")}
REFLL = {k: osref(*v) for k, v in REF.items()}

# English region / nation for each site, from the nearest OS Open Names entry with a region
oreg = osn[osn.region != ""]
olat, olon = oreg.lat.astype(float).values, oreg.lon.astype(float).values
reg = []
for la, lo in zip(S.lat, S.lon):
    d = (olat - la) ** 2 + ((olon - lo) * math.cos(math.radians(la))) ** 2
    reg.append(oreg.region.iloc[int(np.argmin(d))])
S["region"] = reg


def nearest_site(key):
    la, lo = REFLL[key]
    d = haversine(la, lo, S.snap_lat.values, S.snap_lon.values)
    i = int(np.argmin(d)); return i, float(d[i] / 1000)


def by_name(name, county):
    return int(S.index[(S.name == name) & (S.county == county)][0])


START, START_KM = nearest_site("lizard")
ZONE_KM = 30.0
TARGETS = {}
for k, lab in [("london", "London"), ("york", "York"), ("carlisle", "Carlisle"), ("berwick", "Berwick-upon-Tweed")]:
    la, lo = REFLL[k]; d = haversine(la, lo, S.snap_lat.values, S.snap_lon.values) / 1000
    zone = [int(i) for i in np.where(d <= ZONE_KM)[0]]
    TARGETS[k] = dict(label=lab, zone=zone, zone_names=[S.name[i] + ", " + S.county[i] for i in zone], ref=REF[k][0], ref_latlon=REFLL[k],
                      rule=f"any beacon site within {ZONE_KM:.0f} km of the OS Open Names point for {lab}")
for k, lab, nm, ct in [("beacon_fell", "Beacon Fell, Lancashire", "Beacon Fell", "Lancashire"), ("malvern", "Worcestershire Beacon, Malvern", "Worcestershire Beacon", "Worcestershire")]:
    i = by_name(nm, ct); TARGETS[k] = dict(label=lab, zone=[i], zone_names=[nm + ", " + ct], rule="named site")


def route(G, zone, hops=None):
    """Fewest-hop path from START to any site in zone, or None."""
    hops = hops if hops is not None else nx.single_source_shortest_path_length(G, START)
    ok = [i for i in zone if i in hops]
    if not ok: return None
    best = min(ok, key=lambda i: hops[i])
    return nx.shortest_path(G, START, best)


def graph(km, tag="snap", vis="v_snap"):
    d = P["dist_" + tag]; v = P[vis] & (d <= km * 1000); pr = P["pairs"][v]
    G = nx.DiGraph(); G.add_nodes_from(range(N)); G.add_edges_from(map(tuple, pr))
    U = G.to_undirected(); return G, U


def summarise(km, tag="snap", vis="v_snap", full=False):
    G, U = graph(km, tag, vis)
    comps = sorted(nx.connected_components(U), key=len, reverse=True)
    giant = comps[0]
    hops = nx.single_source_shortest_path_length(G, START)
    out = dict(range_km=km, links=U.number_of_edges(), one_way_links=sum(1 for a, b in G.edges if not G.has_edge(b, a)) // 1,
               sees_any=int(sum(1 for n in G if G.in_degree(n) > 0)), share_sees_any=sum(1 for n in G if G.in_degree(n) > 0) / N,
               isolated=int(sum(1 for n in U if U.degree(n) == 0)), n_components=len(comps), giant=len(giant), share_giant=len(giant) / N,
               second=len(comps[1]), reached_from_lizard=len(hops), share_reached=len(hops) / N,
               max_hops=max(hops.values()), mean_degree=2 * U.number_of_edges() / N)
    tg = {}
    for k, t in TARGETS.items():
        path = route(G, t["zone"], hops)
        if path:
            e = path[-1]
            seg = [float(haversine(S.snap_lat[a], S.snap_lon[a], S.snap_lat[b], S.snap_lon[b]) / 1000) for a, b in zip(path, path[1:])]
            tg[k] = dict(hops=len(path) - 1, path=path, end=S.name[e] + ", " + S.county[e], path_km=round(sum(seg), 1), longest_hop_km=round(max(seg), 1) if seg else 0,
                         straight_km=round(float(haversine(S.snap_lat[START], S.snap_lon[START], S.snap_lat[e], S.snap_lon[e]) / 1000), 1),
                         **{f"minutes_{n}": (len(path) - 1) * m for n, m in DELAYS.items()})
        else:
            tg[k] = dict(hops=None)
    out["targets"] = tg
    if full:
        out["_G"], out["_U"], out["_hops"], out["_comps"] = G, U, hops, comps
    return out


def bottleneck(zone):
    """Smallest maximum sight-line length that still lets the fire reach target (any route, up to 150 km)."""
    d = P["dist_snap"]; v = P["v_snap"]; pr = P["pairs"][v]; dd = d[v]
    for km in np.arange(5, 150.01, 0.5):
        G = nx.DiGraph(); G.add_nodes_from(range(N)); G.add_edges_from(map(tuple, pr[dd <= km * 1000]))
        if any(nx.has_path(G, START, t) for t in zone): return float(km)
    return None


R = {}
main = summarise(MAIN_KM, full=True)
G, U, hops, comps = main.pop("_G"), main.pop("_U"), main.pop("_hops"), main.pop("_comps")
R["n_sites"] = N
R["n_by_country"] = S.country.value_counts().to_dict()
R["n_by_source"] = S.source.value_counts().to_dict()
R["n_excluded"] = int(len(pd.read_csv(os.path.join(DATA, "excluded_candidates.csv"))))
R["snap_median_m"] = float(S.snap_shift_m.median())
R["elev_median_m"] = float(S.elev_m.median())
R["start"] = dict(idx=START, name=S.name[START], km_from_lizard_point=round(START_KM, 1))
R["targets_meta"] = {k: {kk: vv for kk, vv in t.items()} for k, t in TARGETS.items()}
R["delays_min"] = DELAYS
R["zone_km"] = ZONE_KM
R["params"] = dict(eye_m=2, fire_m=5, fire_high_m=10, main_range_km=MAIN_KM, sensitivity_ranges_km=[30, 70, 100], max_search_km=150, sample_step_m=45, refraction_k=0.13,
                   snap_radius_m=250, dedupe_km=1, relay_cell_km=10, relay_sample_m=100, relay_min_elev_m=5, relay_max_northing_km=700, dem_pixel_m_approx=90, relay_cost=1000)
R["refs"] = {"sighting_date": dict(value="19 July 1588", source="Royal Museums Greenwich, Elizabeth I and the Spanish Armada, https://www.rmg.co.uk/stories/topics/elizabeth-i-spanish-armada"),
             "poem_written": dict(value=1832, source="Wikipedia, Lays of Ancient Rome"),
             "worcs_height_m": dict(value=425, source="Wikipedia, Worcestershire Beacon"),
             "black_down_height_m": dict(value=325, source="Wikipedia, Black Down, Somerset")}
R["n_beacon_hill"] = int((S.name == "Beacon Hill").sum())
R["n_x_beacon"] = int(S.name.str.match(r"^(?!Beacon Hill$).*Beacon$").sum())
R["zone_detail"] = {k: [dict(name=S.name[i], county=S.county[i], elev_m=float(S.elev_m[i]), links_50=int(U.degree(i)),
                             links_150=int(sum(1 for j in range(len(P["pairs"])) if P["pairs"][j][1] == i and P["v_snap"][j])))
                        for i in t["zone"]] for k, t in TARGETS.items()}
R["main"] = main
for k, t in main["targets"].items():
    if t["hops"] is not None: t["path_names"] = [S.name[i] + ", " + S.county[i] for i in t["path"]]

# sensitivity table
sens = []
for km in (30, 50, 70, 100):
    for tag, vis, lab in [("snap", "v_snap", "Summit, 5 m fire"), ("snap", "v_hi", "Summit, 10 m fire"), ("raw", "v_raw", "Name point, 5 m fire")]:
        s = summarise(km, tag, vis)
        sens.append(dict(range_km=km, variant=lab, links=s["links"], share_sees_any=s["share_sees_any"], giant=s["giant"], share_giant=s["share_giant"],
                         reached=s["reached_from_lizard"], **{f"hops_{k}": s["targets"][k]["hops"] for k in TARGETS}))
R["sensitivity"] = sens
R["bottleneck_km"] = {k: bottleneck(t["zone"]) for k, t in TARGETS.items()}
# bridged routes: allow sight lines up to each target's bottleneck length, take the fewest hops,
# and list the hops longer than the main range (the gaps a name-only chain cannot cross)
R["bridged"] = {}
for k, t in TARGETS.items():
    b = R["bottleneck_km"][k]
    if b is None: continue
    km = max(b, MAIN_KM); Gb, _ = graph(km)
    path = route(Gb, t["zone"])
    seg = [float(haversine(S.snap_lat[a], S.snap_lon[a], S.snap_lat[c], S.snap_lon[c]) / 1000) for a, c in zip(path, path[1:])]
    R["bridged"][k] = dict(range_km=km, hops=len(path) - 1, path=path, end=S.name[path[-1]] + ", " + S.county[path[-1]], path_names=[S.name[i] + ", " + S.county[i] for i in path],
                           seg_km=[round(x, 1) for x in seg], gaps=[dict(a=S.name[a] + ", " + S.county[a], b=S.name[c] + ", " + S.county[c], km=round(x, 1))
                                                               for a, c, x in zip(path, path[1:], seg) if x > MAIN_KM],
                           **{f"minutes_{n}": (len(path) - 1) * m for n, m in DELAYS.items()})

# chokepoints: betweenness on the undirected 50 km network, cut vertices, and what removing each does to the largest network
bc = nx.betweenness_centrality(U, normalized=True)
art = set(nx.articulation_points(U))
choke = []
for i in sorted(bc, key=bc.get, reverse=True)[:12]:
    H = U.copy(); H.remove_node(i)
    g2 = max(len(c) for c in nx.connected_components(H))
    choke.append(dict(idx=i, name=S.name[i], county=S.county[i], region=S.region[i], betweenness=round(bc[i], 3), cut_vertex=i in art,
                      giant_without=g2, giant_lost=main["giant"] - 1 - g2 if i in comps[0] else 0))
# chokepoints on the bridged Lizard to London route: which single site, if it failed, stops or slows the fire
bl = R["bridged"].get("london")
R["london_route_chokes"] = []
if bl:
    Gb, _ = graph(bl["range_km"])
    for i in bl["path"][1:-1]:
        H = Gb.copy(); H.remove_node(i); p2 = route(H, TARGETS["london"]["zone"])
        R["london_route_chokes"].append(dict(name=S.name[i], county=S.county[i], hops_without=len(p2) - 1 if p2 else None))
R["chokepoints"] = choke
R["n_cut_vertices"] = len(art)
R["n_cut_vertices_giant"] = len(art & comps[0])
# which single site, removed, cuts most sites off from the Lizard fire
worst = []
for i in hops:
    if i == START: continue
    H = G.copy(); H.remove_node(i); worst.append((main["reached_from_lizard"] - 1 - len(nx.single_source_shortest_path_length(H, START)), i))
worst.sort(reverse=True)
R["single_failures"] = [dict(idx=i, name=S.name[i], county=S.county[i], lost=n) for n, i in worst[:8]]

# gaps: components that the fire never reaches, and the regions with sites it never reaches
reached = set(hops)
R["unreached"] = dict(n=N - len(reached), by_region=S.loc[[i for i in range(N) if i not in reached]].region.value_counts().to_dict())
R["reached_by_region"] = []
for rg, g in S.groupby("region"):
    ix = list(g.index); h = [hops[i] for i in ix if i in hops]
    R["reached_by_region"].append(dict(region=rg, n=len(ix), reached=len(h), min_hops=min(h) if h else None, median_hops=float(np.median(h)) if h else None))
R["reached_by_region"].sort(key=lambda r: (r["min_hops"] is None, r["min_hops"] or 0))
comp_of = {}
for ci, c in enumerate(comps):
    for n in c: comp_of[n] = ci
R["giant_regions"] = S.loc[sorted(comps[0])].region.value_counts().to_dict()
R["start_component_size"] = len(comps[comp_of[START]])
R["other_components"] = [dict(size=len(c), regions=sorted(set(S.region[list(c)])), names=[S.name[i] + ", " + S.county[i] for i in sorted(c)][:6])
                         for c in comps[1:] if len(c) >= 3]
# longest single sight lines in use at 50 km
d = P["dist_snap"]; v = P["v_snap"] & (d <= MAIN_KM * 1000); pr = P["pairs"][v]; dd = d[v]
o = np.argsort(-dd)
seen = set(); longest = []
for j in o:
    a, b = sorted(pr[j]);
    if (a, b) in seen: continue
    seen.add((a, b)); longest.append(dict(a=S.name[a] + ", " + S.county[a], b=S.name[b] + ", " + S.county[b], km=round(float(dd[j]) / 1000, 1)))
    if len(longest) == 5: break
R["longest_links"] = longest
R["median_link_km"] = round(float(np.median(dd)) / 1000, 1)
R["share_pairs_visible_50"] = float(v.sum() / (d <= MAIN_KM * 1000).sum())
# spread over time: sites alight by hour for each delay
hv = np.array([hops.get(i, -1) for i in range(N)])
R["max_hops"] = int(hv.max())
R["alight_by_hop"] = [int(((hv >= 0) & (hv <= h)).sum()) for h in range(int(hv.max()) + 1)]
R["alight_by_hour"] = {k: [int(((hv >= 0) & (hv * m <= t * 60)).sum()) for t in range(0, 13)] for k, m in DELAYS.items()}
R["hours_all_reached"] = {k: round(int(hv.max()) * m / 60, 2) for k, m in DELAYS.items()}
R["half_reached_hops"] = int(next(h for h, c in enumerate(R["alight_by_hop"]) if c >= main["reached_from_lizard"] / 2))
# degree
deg = np.array([U.degree(i) for i in range(N)])
R["degree_median"] = float(np.median(deg)); R["degree_max"] = int(deg.max()); R["degree_max_name"] = S.name[int(deg.argmax())] + ", " + S.county[int(deg.argmax())]
R["top_degree"] = [dict(name=S.name[i], county=S.county[i], links=int(deg[i])) for i in np.argsort(-deg)[:8]]

# poem check: places Macaulay names that match a beacon site in the data
POEM = [("Worcestershire Beacon", "Worcestershire", "Malvern")]
R["poem_sites"] = [dict(poem=p, name=n, county=c, hops=hops.get(by_name(n, c))) for n, c, p in POEM]


# ===== the filled network: beacon sites plus one possible relay hill per 10 km square (step 3) =====
RH = pd.read_csv(os.path.join(DATA, "relay_hills.csv"))
FP = np.load(os.path.join(WORK, "filled_pairs.npz"))
NF = N + len(RH)
flat = np.r_[S.snap_lat.values, RH.lat.values]; flon = np.r_[S.snap_lon.values, RH.lon.values]
pop = osn[osn.type == "populatedPlace"]
plat, plon = pop.lat.astype(float).values, pop.lon.astype(float).values
def near_place(la, lo):
    d = (plat - la) ** 2 + ((plon - lo) * math.cos(math.radians(la))) ** 2; j = int(np.argmin(d))
    return pop.name1.iloc[j] + ", " + (pop.county.iloc[j] or pop.district.iloc[j])
def fname(i):
    return S.name[i] + ", " + S.county[i] if i < N else "hill near " + near_place(flat[i], flon[i])
def fgraph(km):
    m = FP["dist"] <= km * 1000
    G = nx.DiGraph(); G.add_nodes_from(range(NF)); G.add_edges_from(map(tuple, FP["pairs"][m])); return G
FZ = {}
for k, t in TARGETS.items():
    if "ref_latlon" in t:
        la, lo = t["ref_latlon"]; d = haversine(la, lo, flat, flon) / 1000; FZ[k] = [int(i) for i in np.where(d <= ZONE_KM)[0]]
    else: FZ[k] = t["zone"]
R["filled"] = dict(n_relays=len(RH), n_nodes=NF, cell_km=10, links_50=int(fgraph(50).to_undirected().number_of_edges()))
for km in (30, 50):
    GF = fgraph(km); hf = nx.single_source_shortest_path_length(GF, START)
    # fewest relay hills first, then fewest hops: an edge into a relay hill costs 1000, into a named beacon 1
    W = lambda a, b, e: 1000 if b >= N else 1
    dist_w, path_w = nx.single_source_dijkstra(GF, START, weight=W)
    tg = {}
    for k in TARGETS:
        p1 = route(GF, FZ[k], hf)
        if not p1: tg[k] = None; continue
        ok = [i for i in FZ[k] if i in path_w]; best = min(ok, key=lambda i: (dist_w[i], hf[i])); p2 = path_w[best]
        seg = [float(haversine(flat[a], flon[a], flat[b], flon[b]) / 1000) for a, b in zip(p1, p1[1:])]
        tg[k] = dict(hops=len(p1) - 1, path=p1, path_names=[fname(i) for i in p1], end=fname(p1[-1]), path_km=round(sum(seg), 1),
                     relays_on_fastest=sum(1 for i in p1 if i >= N), named_on_fastest=sum(1 for i in p1 if i < N),
                     min_relays=sum(1 for i in p2 if i >= N), min_relay_hops=len(p2) - 1, min_relay_path=p2, min_relay_names=[fname(i) for i in p2],
                     **{f"minutes_{n}": (len(p1) - 1) * m for n, m in DELAYS.items()})
    hv = np.array([hf.get(i, -1) for i in range(NF)])
    hb = hv[:N]
    R["filled"][str(km)] = dict(reached_nodes=int((hv >= 0).sum()), reached_beacons=int((hb >= 0).sum()), share_beacons_reached=float((hb >= 0).mean()),
                                max_hops_beacons=int(hb.max()), targets=tg,
                                beacons_alight_by_hop=[int(((hb >= 0) & (hb <= h)).sum()) for h in range(int(hb.max()) + 1)],
                                beacons_alight_by_hour={k: [int(((hb >= 0) & (hb * m <= t * 60)).sum()) for t in range(0, 25)] for k, m in DELAYS.items()},
                                hours_all_beacons={k: round(int(hb.max()) * m / 60, 2) for k, m in DELAYS.items()},
                                unreached_beacons=[S.name[i] + ", " + S.county[i] for i in range(N) if hb[i] < 0])
    if km == 50:
        FH = hv; GF50 = GF
        R["filled"]["region_hops"] = []
        for rg, g in S.groupby("region"):
            h = [int(hb[i]) for i in g.index if hb[i] >= 0]
            R["filled"]["region_hops"].append(dict(region=rg, n=len(g), reached=len(h), first_hops=min(h) if h else None, median_hops=float(np.median(h)) if h else None))
        R["filled"]["region_hops"].sort(key=lambda r: (r["first_hops"] is None, r["first_hops"] or 0))
        # how many named beacons does the fastest London route pass through, and which relay hills fill the gaps
        R["filled"]["london_relays"] = [dict(name=fname(i), lat=round(float(flat[i]), 4), lon=round(float(flon[i]), 4), elev_m=float(RH.elev_m[i - N]))
                                        for i in tg["london"]["min_relay_path"] if i >= N] if tg.get("london") else []
for k in TARGETS:
    t = R["filled"]["50"]["targets"][k]
    if t: print("FILLED", k, t["hops"], t["minutes_central"], "relays fastest", t["relays_on_fastest"], "min relays", t["min_relays"], t["min_relay_hops"], t["path_names"])
print("filled", {k: v for k, v in R["filled"]["50"].items() if k not in ("targets", "unreached_beacons", "beacons_alight_by_hour")})
print(R["filled"]["region_hops"]); print(R["filled"]["london_relays"])

# outputs
net = S[["site_id", "name", "county", "country", "region", "snap_lat", "snap_lon", "elev_m"]].copy()
net["sees_fires_from"] = [G.in_degree(i) for i in range(N)]
net["links_50km"] = deg
net["component"] = [comp_of[i] for i in range(N)]
net["in_giant"] = net.component == 0
net["hops_from_lizard"] = pd.array([hops.get(i) for i in range(N)], dtype="Int64")
for k, m in DELAYS.items(): net[f"minutes_{k}"] = pd.array([hops[i] * m if i in hops else None for i in range(N)], dtype="Int64")
net["hops_from_lizard_filled"] = pd.array([int(FH[i]) if FH[i] >= 0 else None for i in range(N)], dtype="Int64")
net["betweenness"] = [round(bc[i], 4) for i in range(N)]
net["cut_vertex"] = [i in art for i in range(N)]
net.to_csv(os.path.join(DATA, "beacon_network.csv"), index=False)
rows = []
for j in range(len(P["pairs"])):
    a, b = P["pairs"][j]
    if P["dist_snap"][j] <= 70000 or P["v_snap"][j]:
        rows.append(dict(fire_site=S.site_id[a], watcher_site=S.site_id[b], km=round(float(P["dist_snap"][j]) / 1000, 2), visible_5m_fire=bool(P["v_snap"][j]),
                         visible_10m_fire=bool(P["v_hi"][j]), visible_from_name_points=bool(P["v_raw"][j])))
pd.DataFrame(rows).to_csv(os.path.join(DATA, "sightlines.csv"), index=False)
pr_rows = []
for k, t in main["targets"].items():
    if t["hops"] is None: continue
    for h, i in enumerate(t["path"]):
        pr_rows.append(dict(target=TARGETS[k]["label"], route="within 50 km", hop=h, site_id=S.site_id[i], name=S.name[i], county=S.county[i], lat=S.snap_lat[i], lon=S.snap_lon[i]))
for k, b in R["bridged"].items():
    for h, i in enumerate(b["path"]):
        pr_rows.append(dict(target=TARGETS[k]["label"], route=f"bridged, sight lines up to {b['range_km']:g} km", hop=h, site_id=S.site_id[i], name=S.name[i], county=S.county[i], lat=S.snap_lat[i], lon=S.snap_lon[i]))
for k, t in R["filled"]["50"]["targets"].items():
    if not t: continue
    for lab, pth in [("filled network, fewest hops", t["path"]), ("filled network, fewest relay hills", t["min_relay_path"])]:
        for h, i in enumerate(pth):
            pr_rows.append(dict(target=TARGETS[k]["label"], route=lab, hop=h, site_id=S.site_id[i] if i < N else RH.relay_id[i - N], name=fname(i),
                                county=S.county[i] if i < N else "", lat=round(float(flat[i]), 5), lon=round(float(flon[i]), 5)))
RH["hops_from_lizard_filled"] = pd.array([int(FH[i]) if FH[i] >= 0 else None for i in range(N, NF)], dtype="Int64")
RH.to_csv(os.path.join(DATA, "relay_hills.csv"), index=False)
pd.DataFrame(pr_rows).to_csv(os.path.join(DATA, "paths.csv"), index=False)


def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, np.bool_): return bool(o)
    return o


R = clean(R)
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1)
# compact site data for the page
E = {}
for km in (30, 50, 70):
    Gk, Uk = graph(km); E[km] = [int(x) for e in Uk.edges for x in e]
used = sorted({i for t in R["filled"]["50"]["targets"].values() if t for i in t["path"] + t["min_relay_path"] if i >= N})
site = dict(R=R, s=[[round(r.snap_lat, 4), round(r.snap_lon, 4), r["name"], r.county, int(round(r.elev_m)), hops.get(i, -1), round(bc[i], 4), int(deg[i]), r.region, int(FH[i])]
                    for i, r in S.iterrows()], e=E,
            r=[[round(float(flat[i]), 4), round(float(flon[i]), 4), int(FH[i]), int(round(float(RH.elev_m[i - N])))] for i in range(N, NF)],
            used=used)
json.dump(clean(site), open(os.path.join(WORK, "site.json"), "w"), separators=(",", ":"))
print(json.dumps({k: R[k] for k in ["n_sites", "start", "bottleneck_km", "max_hops", "hours_all_reached", "n_cut_vertices"]}, indent=1))
m = R["main"]; print({k: v for k, v in m.items() if k != "targets"})
for k, t in m["targets"].items(): print(k, t.get("hops"), t.get("path_km"), t.get("longest_hop_km"), t.get("path_names"))
for k, t in TARGETS.items(): print(k, t["zone_names"])
print(R["london_route_chokes"])
for c in R["chokepoints"]: print(c)
print(R["single_failures"]); print(R["unreached"]); print(R["other_components"]); print(R["longest_links"])
for s in R["sensitivity"]: print(s)
for k, b in R["bridged"].items(): print(k, b["range_km"], b["hops"], b["gaps"], b["path_names"])
print(R["reached_by_region"])
