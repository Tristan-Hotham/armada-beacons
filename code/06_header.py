"""Render ../header.png (1200x630 social card) with Playwright Chromium.

Fonts: pass a folder of TTFs as FONT_DIR (FrauncesVar.ttf, SourceSerif4-Regular.ttf,
IBMPlexMono-Regular.ttf, IBMPlexMono-Medium.ttf from github.com/google/fonts);
otherwise the system serif is used.
Run: python3 06_header.py
"""
import os, json, math
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
S = json.load(open(os.path.join(ROOT, "work", "site.json")))
R = S["R"]; FD = os.environ.get("FONT_DIR", "")
B = S["s"]; E = S["e"]["50"]; RH = S["r"]


def proj(lat, lon):
    return lon * math.cos(math.radians(53.5)), -lat


pts = [proj(r[0], r[1]) for r in B if r[0] < 56.2] + [proj(r[0], r[1]) for r in RH]
xs, ys = zip(*pts); x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
H = 610; W = H * (x1 - x0) / (y1 - y0)
P = lambda la, lo: ((proj(la, lo)[0] - x0) / (y1 - y0) * H, (proj(la, lo)[1] - y0) / (y1 - y0) * H)
seg = " ".join("M%.1f %.1fL%.1f %.1f" % (*P(B[a][0], B[a][1]), *P(B[b][0], B[b][1])) for a, b in zip(E[::2], E[1::2]) if B[a][0] < 56.2 and B[b][0] < 56.2)
rel = "".join('<circle cx="%.1f" cy="%.1f" r="1"/>' % P(r[0], r[1]) for r in RH)
T = R["filled"]["50"]["targets"]["london"]
allp = B + [[r[0], r[1]] for r in RH]
route = "M" + "L".join("%.1f %.1f" % P(allp[k][0], allp[k][1]) for k in T["path"])
dots = "".join('<circle cx="%.1f" cy="%.1f" r="%.1f"/>' % (*P(r[0], r[1]), 2.4 + math.sqrt(r[7]) * .8) for r in B if r[0] < 56.2)
lz = P(B[R["start"]["idx"]][0], B[R["start"]["idx"]][1])
rings = "".join(f'<circle cx="{lz[0]:.1f}" cy="{lz[1]:.1f}" r="{r}" fill="none" stroke="#D9480F" stroke-width="1.6" opacity="{.75 - i * .12:.2f}"/>' for i, r in enumerate(range(18, 120, 20)))
ff = ""
if FD:
    ff = "".join(f"@font-face{{font-family:'{n}';src:url('file://{FD}/{f}');font-weight:{w};}}" for n, f, w in [
        ("Fraunces", "FrauncesVar.ttf", "100 900"), ("Source Serif 4", "SourceSerif4-Regular.ttf", "400"),
        ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"), ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500")])
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{ff}
body{{margin:0;width:1200px;height:630px;background:linear-gradient(160deg,#FCEBD9 0%,#FADCC2 100%);color:#2B1B12;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}}
.k{{position:absolute;left:70px;top:90px;font:500 15px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#7A6252;display:flex;gap:12px;align-items:center}}
.k b{{background:#D9480F;color:#fff;padding:7px 9px;font-weight:500}}
h1{{position:absolute;left:66px;top:134px;margin:0;font:900 118px/.88 Fraunces,Georgia,serif;letter-spacing:-.02em}}
h1 em{{font-style:normal;color:#D9480F;display:block}}
p{{position:absolute;left:70px;top:390px;width:560px;margin:0;font-size:27px;line-height:1.36;color:#3B2A1F}}
.f{{position:absolute;left:70px;bottom:44px;font:400 14px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#8A6F5C}}
svg{{position:absolute;right:50px;top:10px}}
</style></head><body>
<div class="k"><b>Data study</b><span>History × landscape</span></div>
<h1>Fire on<em>the hills</em></h1>
<p>{R['n_sites']} beacon hills, one fire at the Lizard. With the gaps filled, it reaches London in {T['hops']} hops.</p>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<svg width="{W:.0f}" height="{H}" viewBox="0 0 {W:.0f} {H}"><g fill="#C9A88C" fill-opacity=".45">{rel}</g>
<path d="{seg}" stroke="#4F6D8A" stroke-width="1" stroke-opacity=".55" fill="none"/>{rings}
<path d="{route}" stroke="#9C2A12" stroke-width="3.2" fill="none" stroke-linejoin="round"/>
<g fill="#D9480F" stroke="#FCEBD9" stroke-width=".8">{dots}</g></svg>
</body></html>"""
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
tmp = os.path.join(ROOT, "work", "header.html"); open(tmp, "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto("file://" + os.path.abspath(tmp)); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(ROOT, "header.png")); b.close()
print("header.png written")
