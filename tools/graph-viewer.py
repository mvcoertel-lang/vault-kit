#!/usr/bin/env python3
"""Rendert einen Graphify-`graph.json` in einen eigenen, standalone Betrachter
(dark, offline, kein CDN), der Cluster (Communities) und Beziehungstypen
sichtbar macht. Schreibt eine SEPARATE Datei `graph.viewer.html` neben die
Quelle — `graphify update` überschreibt sie nie.

Aufruf:
  python3 ~/.claude/tools/graph-viewer.py <graph.json | ordner> [ausgabe.html]
"""
import json, sys, pathlib, collections

for _s in (sys.stdout, sys.stderr):  # Windows-Konsole: UTF-8 statt cp1252
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

def main():
    if len(sys.argv) < 2:
        sys.exit("Aufruf: graph-viewer.py <graph.json | ordner> [ausgabe.html]")
    src = pathlib.Path(sys.argv[1]).expanduser().resolve()
    if src.is_dir():
        cand = src / "graphify-out" / "graph.json"
        src = cand if cand.is_file() else src / "graph.json"
    if not src.is_file():
        sys.exit(f"graph.json nicht gefunden: {src}")
    out = (pathlib.Path(sys.argv[2]).expanduser() if len(sys.argv) > 2
           else src.parent / "graph.viewer.html")
    tmpl = pathlib.Path(__file__).resolve().parent / "graph-viewer.template.html"
    if not tmpl.is_file():
        sys.exit(f"Template fehlt: {tmpl}")

    d = json.loads(src.read_text(encoding="utf-8"))
    raw_nodes = d.get("nodes", [])
    raw_links = d.get("links", d.get("edges", []))

    # Community je Knoten + Ranking (Top 8 → Farbslot, Rest → 'Other')
    cname, ccount = {}, collections.Counter()
    for n in raw_nodes:
        c = n.get("community_name") or (f"c{n.get('community')}" if n.get("community") is not None else "?")
        cname[n["id"]] = c
        ccount[c] += 1
    top = [c for c, _ in ccount.most_common(8)]
    slot_of = {c: i for i, c in enumerate(top)}
    communities = [{"name": c, "slot": slot_of[c], "count": ccount[c]} for c in top]
    other = sum(v for c, v in ccount.items() if c not in slot_of)
    if other > 0:
        communities.append({"name": "Other", "slot": -1, "count": other})

    deg = collections.Counter()
    for l in raw_links:
        deg[l["source"]] += 1
        deg[l["target"]] += 1

    idx, nodes = {}, []
    for n in raw_nodes:
        idx[n["id"]] = len(nodes)
        c = cname[n["id"]]
        nodes.append({
            "id": n["id"],
            "label": n.get("label") or n.get("norm_label") or n["id"],
            "file": n.get("source_file", ""),
            "loc": n.get("source_location", ""),
            "slot": slot_of.get(c, -1),
            "deg": deg.get(n["id"], 0),
        })

    RELMAP = {
        "calls": "call", "indirect_call": "call",
        "extends": "inherit", "inherits": "inherit",
        "imports": "import", "imports_from": "import", "references": "import",
        "contains": "contain",
    }
    links = []
    for l in raw_links:
        s, t = idx.get(l["source"]), idx.get(l["target"])
        if s is None or t is None:
            continue
        links.append({"s": s, "t": t, "cls": RELMAP.get(l.get("relation"), "call")})

    title = src.parent.parent.name if src.parent.name == "graphify-out" else src.parent.name
    payload = {"nodes": nodes, "links": links, "communities": communities,
               "meta": {"title": title}}

    html = tmpl.read_text(encoding="utf-8").replace(
        "__GRAPH_DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    out.write_text(html, encoding="utf-8")

    print(f"Betrachter: {out}")
    print(f"Knoten {len(nodes)} · Kanten {len(links)} · Cluster {len(communities)} (Top-8 + Other)")
    print("Kantenklassen:", dict(collections.Counter(l["cls"] for l in links)))

main()
