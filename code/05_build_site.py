"""Step 5: build ../index.html and ../README.md from page_template.html, prose.html
and README_template.md.

Every number in the text is a placeholder like {{main.giant|int}} filled from
../data/results.json, and the compact site data (../work/site.json) is embedded
as `const D = ...`.
Formats: int, pct0, pct1, f1, f2, raw, words (numbers to twelve as words),
dur (minutes as "2 hours 15 minutes").
Run: python3 05_build_site.py
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
site = open(os.path.join(ROOT, "work", "site.json")).read()


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def dur(m):
    m = int(round(m))
    if m < 60: return f"{m} minutes"
    h, r = divmod(m, 60)
    s = f"{h} hour" + ("s" if h > 1 else "")
    return s + (f" {r} minutes" if r else "")


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct0": return f"{v * 100:.0f}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    if f == "dur": return dur(v)
    if f == "words":
        w = "zero one two three four five six seven eight nine ten eleven twelve".split()
        return w[int(v)] if int(v) < len(w) else f"{int(v):,}"
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


t = open(os.path.join(HERE, "page_template.html")).read().replace("<!--PROSE-->", open(os.path.join(HERE, "prose.html")).read())
t = re.sub(r"\{\{(.+?)\}\}", sub, t)
t = t.replace("/*DATA*/", "const D = " + site + ";")
open(os.path.join(ROOT, "index.html"), "w").write(t)
print("index.html", len(t.encode()) // 1024, "KB")
md = re.sub(r"\{\{(.+?)\}\}", sub, open(os.path.join(HERE, "README_template.md")).read())
open(os.path.join(ROOT, "README.md"), "w").write(md)
print("README.md written")
