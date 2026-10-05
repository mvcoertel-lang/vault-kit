#!/usr/bin/env python3
"""Baut den Index-Graphen eines Claude-Code-Vaults.

Aufruf im Vault-Wurzelordner:      python3 vault-index.py
Oder mit ausdrücklichem Pfad:     python3 vault-index.py ~/Vault

Erzeugt <vault>/_Index/graphify-out/graph.json und, falls graph.template.html
daneben liegt, gleich den fertigen Betrachter <vault>/_Index/graph.html.

Portabel: Der Vault-Pfad kommt aus dem Argument oder dem Arbeitsverzeichnis,
das Memory-Verzeichnis aus `autoMemoryDirectory` in ~/.claude/settings.json oder
wird aus dem Pfad abgeleitet. Nichts ist fest verdrahtet. macOS, Linux, Windows.

--hook: Aufruf aus dem SessionEnd-Hook. Läuft nicht bei `claude -p`-Läufen
(CLAUDE_CODE_ENTRYPOINT sdk-*), schreibt nach tools/last-index.log und endet
immer mit 0. So braucht der Hook keine Shell-Syntax und läuft in Git Bash wie
in PowerShell.
"""
import json, os, pathlib, re, collections, sys

H = pathlib.Path.home()
TOOLS = pathlib.Path(__file__).resolve().parent
HOOK = '--hook' in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]

if HOOK:
    if os.environ.get('CLAUDE_CODE_ENTRYPOINT', '').startswith('sdk'):
        sys.exit(0)
    _log = open(TOOLS/'last-index.log', 'w', encoding='utf-8')
    sys.stdout = sys.stderr = _log
    def _still(typ, val, tb):
        import traceback; traceback.print_exception(typ, val, tb); _log.flush(); os._exit(0)
    sys.excepthook = _still
else:
    for _s in (sys.stdout, sys.stderr):
        try: _s.reconfigure(encoding='utf-8', errors='replace')   # Windows-Konsole ist sonst cp1252
        except (AttributeError, ValueError): pass

# --- Pfade bestimmen ---------------------------------------------------------
VAULT = pathlib.Path(ARGS[0]).expanduser().resolve() if ARGS else pathlib.Path.cwd().resolve()

def memdir(vault):
    """autoMemoryDirectory aus ~/.claude/settings.json, sonst wie Claude Code ableiten:
    jedes Zeichen außer Buchstaben und Ziffern wird zu '-'. /Users/x/Vault -> -Users-x-Vault"""
    if os.environ.get('VAULT_MEMDIR'):
        return pathlib.Path(os.environ['VAULT_MEMDIR']).expanduser()
    try:
        d = json.loads((H/'.claude/settings.json').read_text(encoding='utf-8')).get('autoMemoryDirectory')
        if d: return pathlib.Path(d).expanduser()
    except (OSError, ValueError):
        pass
    return H/'.claude/projects'/re.sub(r'[^A-Za-z0-9]', '-', str(vault))/'memory'

MEM  = memdir(VAULT)
OUT  = VAULT/'_Index/graphify-out'
TMPL = TOOLS/'graph.template.html'
HTML = VAULT/'_Index/graph.html'

if not VAULT.is_dir():
    sys.exit(f"Vault-Ordner nicht gefunden: {VAULT}")
if not MEM.is_dir():
    print(f"Hinweis: kein Memory-Verzeichnis unter {MEM}")
    print("         Der Graph entsteht dann ohne die Abteilung Memory.")

nodes, edges = {}, []

def yaml_str(v):
    """Skalar aus dem Frontmatter ohne Anführungszeichen und YAML-Escapes (\\" -> ")."""
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return v[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return v

def node(nid, label, dept, kind, **kw):
    nodes[nid] = dict(id=nid, label=label, dept=dept, kind=kind, **kw); return nid
def edge(s, t, rel, origin):
    if s in nodes and t in nodes and s != t:
        edges.append(dict(source=s, target=t, relation=rel, origin=origin))

# --- Skills ------------------------------------------------------------------
skill_ids = {}
for root, scope in [(H/'.claude/skills','global'), (VAULT/'.claude/skills','vault')]:
    if not root.exists(): continue
    for sk in sorted(root.iterdir()):
        f = sk/'SKILL.md'
        if not f.is_file(): continue
        t = f.read_text(encoding='utf-8', errors='ignore')
        m = re.search(r'^---\n(.*?)\n---', t, re.S); fm = m.group(1) if m else ''
        nm = re.search(r'^name:\s*(.+)$', fm, re.M)
        name = nm.group(1).strip() if nm else sk.name
        dm = re.search(r'^description:\s*(.+(?:\n\s+.+)*)$', fm, re.M)
        desc = yaml_str(re.sub(r'\s+', ' ', dm.group(1))) if dm else ''
        nid = 'skill:'+name
        node(nid, name, 'Skills', 'skill', scope=scope, lines=len(t.splitlines()),
             desc=desc, path=str(sk))
        skill_ids[name] = nid; skill_ids[sk.name] = nid

# --- Projekte ----------------------------------------------------------------
# Routing-Tabelle der Root-CLAUDE.md: | Ordner | Was | Status |
routing = {}
for cand in (VAULT/'CLAUDE.md', VAULT/'.claude/CLAUDE.md'):
    if cand.is_file():
        for m in re.finditer(r'^\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|\s*$',
                             cand.read_text(encoding='utf-8', errors='ignore'), re.M):
            routing[m.group(1)] = (re.sub(r'\*\*|`', '', m.group(2)), m.group(3))
        break

proj_ids = {}
EXT = {'.md','.txt','.html','.js','.json','.csv','.xlsx','.pptx','.pdf'}
for p in sorted(VAULT.iterdir()):
    if not p.is_dir() or p.name.startswith('.') or p.name == '_Index': continue
    files = [f for f in p.rglob('*') if f.is_file() and f.suffix.lower() in EXT]
    words = sum(len(f.read_text(encoding='utf-8',errors='ignore').split())
                for f in files if f.suffix.lower() in {'.md','.txt'})
    nid = 'projekt:'+p.name
    was, status = routing.get(p.name, ('', ''))
    node(nid, p.name.replace('_',' ').strip(), 'Projekte', 'projekt',
         files=len(files), words=words, path=str(p), status=status, routed=bool(was),
         desc=was or f"{len(files)} Dateien, {words:,} Wörter".replace(',','.'))
    proj_ids[p.name] = nid

# --- Anweisungen (CLAUDE.md-Kette) -------------------------------------------
chain = []
if (H/'.claude/CLAUDE.md').is_file():
    chain.append((H/'.claude/CLAUDE.md','Global','anw:global'))
for cand in (VAULT/'.claude/CLAUDE.md', VAULT/'CLAUDE.md'):
    if cand.is_file():
        chain.append((cand,'Vault','anw:vault')); break
for f in sorted(VAULT.glob('*/CLAUDE.md')):
    chain.append((f, f.parent.name.replace('_',' '), 'anw:'+f.parent.name))
for f, label, nid in chain:
    t = f.read_text(encoding='utf-8', errors='ignore')
    node(nid, label, 'Anweisungen', 'anweisung', lines=len(t.splitlines()),
         path=str(f), desc=re.sub(r'\s+',' ',t.strip().splitlines()[0] if t.strip() else '')[:150])
for a, b in zip(chain, chain[1:2]):
    edge(a[2], b[2], 'gilt weiter in', 'STRUKTUR')
for f, label, nid in chain[2:]:
    edge('anw:vault', nid, 'gilt weiter in', 'STRUKTUR')
    if f.parent.name in proj_ids: edge(nid, proj_ids[f.parent.name], 'steuert', 'STRUKTUR')

# --- Memory ------------------------------------------------------------------
mem_ids = {}
mem_files = sorted(MEM.rglob('*.md')) if MEM.is_dir() else []
# Lesbare Titel aus den Indexzeilen von MEMORY.md: - [Titel](datei.md) — Haken
mem_title = {}
if (MEM/'MEMORY.md').is_file():
    for m in re.finditer(r'^\s*-\s*\[(.+?)\]\(([^)#]+?)\.md\)', (MEM/'MEMORY.md').read_text(encoding='utf-8', errors='ignore'), re.M):
        mem_title[pathlib.Path(m.group(2)).name] = m.group(1).replace('`', '').strip()
for f in mem_files:
    if f.name == 'MEMORY.md': continue
    t = f.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'^---\n(.*?)\n---', t, re.S); fm = m.group(1) if m else ''
    nm = re.search(r'^name:\s*(.+)$', fm, re.M)
    name = nm.group(1).strip() if nm else f.stem
    dm = re.search(r'^description:\s*(.+)$', fm, re.M)
    tm = re.search(r'^\s*type:\s*(\w+)\s*$', fm, re.M)
    dt = re.search(r'^\s*date:\s*["\']?(\d{4}-\d{2}-\d{2})', fm, re.M)
    archived = '_archiv' in f.parts
    nid = 'mem:'+f.stem
    node(nid, name, 'Memory', 'memory', archived=archived,
         superseded=bool(re.search(r'^\s*superseded_by:\s*\S', fm, re.M)),
         date=(dt.group(1) if dt else ''), stem=f.stem, title=mem_title.get(f.stem, ''),
         mtype=(tm.group(1) if tm else 'unbekannt'),
         desc=yaml_str(re.sub(r'\s+',' ',dm.group(1))) if dm else '',
         path=str(f), lines=len(t.splitlines()))
    mem_ids[f.stem] = nid; mem_ids[name] = nid

# --- Kanten aus Text ---------------------------------------------------------
def mentioned(key, text, low):
    """Eindeutige Nennung: in Backticks, als /kommando, oder mehrteiliger Name."""
    k = re.escape(key)
    ambig = re.match(r'^[a-zäöü]+$', key) and len(key) < 12
    if ambig:
        # `animate` ist auch ein gewöhnliches Wort. Backticks reichen hier nicht,
        # nur der Slash-Aufruf oder der Pfad belegen eine Nennung des Skills.
        return (re.search(r'(?<![\w-])/'+k+r'(?![\w-])', text, re.I) is not None
                or re.search(r'skills/'+k+r'(?![\w-])', text, re.I) is not None)
    if re.search(r'`/?'+k+r'`', text, re.I): return True
    if re.search(r'(?<![\w-])/'+k+r'(?![\w-])', text, re.I): return True
    return re.search(r'(?<![\w-])'+k.lower()+r'(?![\w-])', low) is not None

def scan(text, src, exclude=()):
    low = text.lower()
    for key, nid in list(skill_ids.items()):
        if nid == src or nid in exclude: continue
        if mentioned(key, text, low):
            edge(src, nid, 'nennt', 'EXTRAHIERT')
    for key, nid in list(proj_ids.items()):
        if nid == src: continue
        plain = key.lower().replace('_',' ').strip()
        if len(plain) < 5: continue
        if re.search(r'(?<![\w-])'+re.escape(plain)+r'(?![\w-])', low) or key.lower() in low:
            edge(src, nid, 'gehört zu', 'EXTRAHIERT')

for f in mem_files:
    if f.name == 'MEMORY.md': continue
    src = 'mem:'+f.stem
    t = f.read_text(encoding='utf-8', errors='ignore')
    for wl in sorted(set(re.findall(r'\[\[([^\]]+)\]\]', t))):
        tgt = mem_ids.get(wl) or mem_ids.get(wl.strip())
        if tgt: edge(src, tgt, 'verweist auf', 'WIKILINK')
    scan(t, src)

for f, label, nid in chain:
    scan(f.read_text(encoding='utf-8', errors='ignore'), nid)

for name, nid in list(skill_ids.items()):
    p = pathlib.Path(nodes[nid]['path'])/'SKILL.md'
    if p.is_file(): scan(p.read_text(encoding='utf-8', errors='ignore'), nid, exclude={nid})

# --- Dubletten, Grad ---------------------------------------------------------
seen, uniq = set(), []
for e in edges:
    k = (e['source'], e['target'], e['relation'])
    if k in seen: continue
    seen.add(k); uniq.append(e)
edges = sorted(uniq, key=lambda e: (e['source'], e['target'], e['relation']))

deg = collections.Counter()
for e in edges: deg[e['source']] += 1; deg[e['target']] += 1
for n in nodes.values(): n['degree'] = deg.get(n['id'], 0)

# --- Gruppen je Abteilung ----------------------------------------------------
# Optional: <vault>/_Index/gruppen.json ordnet Knoten per Regex Gruppen zu.
# Ohne Datei: Memory nach Art, Skills nach Bereich, Projekte nach Status.
GCONF = VAULT/'_Index/gruppen.json'
try:
    gconf = json.loads(GCONF.read_text(encoding='utf-8')) if GCONF.is_file() else {}
except ValueError as ex:
    print(f"Warnung: {GCONF} unlesbar ({ex}), Gruppen nach Standard."); gconf = {}

def pick(conf, key, text, scope=''):
    for g in conf.get('gruppen', []):
        if g.get('scope') and g['scope'] == scope: return g['name']
        if any(re.search(p, key, re.I) for p in g.get('muster', [])): return g['name']
        if text and any(re.search(p, text, re.I) for p in g.get('text', [])): return g['name']
    return conf.get('rest', 'Sonstiges')

groups = collections.defaultdict(list)
for n in nodes.values():
    d = n['dept']
    if d == 'Memory':
        n['grp'] = pick(gconf['Memory'], n['stem'], '') if 'Memory' in gconf else n['mtype']
    elif d == 'Skills':
        n['grp'] = pick(gconf['Skills'], n['label'], '', n['scope']) if 'Skills' in gconf \
                   else ('Vault' if n['scope'] == 'vault' else 'Global')
    elif d == 'Projekte':
        folder = pathlib.Path(n['path']).name
        n['grp'] = pick(gconf['Projekte'], folder, n['desc'] if n['routed'] else '') \
                   if 'Projekte' in gconf else (n['status'] or 'ohne Status')
for n in nodes.values():
    if n['dept'] == 'Anweisungen':          # Projekt-CLAUDE.md in die Gruppe ihres Projekts
        pid = proj_ids.get(pathlib.Path(n['path']).parent.name)
        n['grp'] = 'Kette' if n['id'] in ('anw:global', 'anw:vault') or not pid \
                   else nodes[pid]['grp']
for n in nodes.values():
    if n['grp'] not in groups[n['dept']]: groups[n['dept']].append(n['grp'])
def gorder(dept):
    conf = [g['name'] for g in gconf.get(dept, {}).get('gruppen', [])]
    if dept == 'Anweisungen':
        conf = ['Kette'] + [g['name'] for g in gconf.get('Projekte', {}).get('gruppen', [])]
    rank = {g: i for i, g in enumerate(conf)}
    return sorted(groups[dept], key=lambda g: (rank.get(g, 99), g))

# --- Bedeutung, Wachstum, Zusammenfassungen -----------------------------------
# Bedeutung: PageRank über den ungerichteten Graphen, normiert auf das Maximum.
# Kern ist, wer mindestens 0,2 des Maximums erreicht und dabei mindestens 6
# Verbindungen und das Doppelte des Abteilungsmedians hat, oder wer in seiner
# Abteilung mindestens 15 Verbindungen und das Dreifache des Medians hat.
# Höchstens Wurzel(N) Kerne, nach Rang: Auf kleinen, flachen Graphen (Server,
# 85 Knoten am 2026-10-02) reichte 0,2 sonst schon Knoten mit einer Verbindung.
# Alles rechnet sich bei jedem Lauf neu: was Verbindungen sammelt, wird Kern.
import datetime as _dt, hashlib, shutil, statistics, subprocess
nb = collections.defaultdict(set)
for e in edges:
    a, b = e['source'], e['target']
    if a in nodes and b in nodes and a != b: nb[a].add(b); nb[b].add(a)
_N = len(nodes) or 1
pr = {k: 1 / _N for k in nodes}
for _ in range(60):
    nxt = {k: 0.15 / _N for k in nodes}
    dangling = sum(pr[k] for k in nodes if not nb[k])
    for k in nodes:
        for j in nb[k]: nxt[j] += 0.85 * pr[k] / len(nb[k])
    for k in nodes: nxt[k] += 0.85 * dangling / _N
    pr = nxt
_mx = max(pr.values()) if pr else 1
med = {d: statistics.median([n['degree'] for n in nodes.values() if n['dept'] == d] or [0])
       for d in ('Memory', 'Skills', 'Projekte', 'Anweisungen')}
for k, n in nodes.items():
    n['rank'] = round(pr[k] / _mx, 3)
    m = med.get(n['dept'], 0)
    n['core'] = ((n['rank'] >= 0.2 and n['degree'] >= max(6, 2 * m))
                 or (n['degree'] >= 15 and n['degree'] >= 3 * m))
for i, k in enumerate(sorted((k for k in nodes if nodes[k]['core']), key=lambda k: -nodes[k]['rank'])):
    if i >= max(5, round(_N ** 0.5)): nodes[k]['core'] = False

# Wachstum: tägliche Momentaufnahme der Grade in _Index/verlauf.json (90 Tage).
# Gibt es noch keine Aufnahme von vor mindestens 25 Tagen, zählt ersatzweise,
# wie viele Nachbarn Memory-Notizen aus den letzten 30 Tagen sind.
heute = _dt.date.today()
VERLAUF = VAULT/'_Index/verlauf.json'
try:
    verlauf = json.loads(VERLAUF.read_text(encoding='utf-8')) if VERLAUF.is_file() else {}
except ValueError:
    verlauf = {}
verlauf[heute.isoformat()] = {k: n['degree'] for k, n in nodes.items()}
verlauf = {d: v for d, v in verlauf.items() if d >= (heute - _dt.timedelta(days=90)).isoformat()}
alt = [d for d in sorted(verlauf) if d <= (heute - _dt.timedelta(days=25)).isoformat()]
ziel = (heute - _dt.timedelta(days=30)).isoformat()
basis = verlauf[min(alt, key=lambda d: abs(_dt.date.fromisoformat(d) - _dt.date.fromisoformat(ziel)))] if alt else None
grenze = (heute - _dt.timedelta(days=30)).isoformat()
for k, n in nodes.items():
    if basis is not None:
        g = n['degree'] - basis.get(k, 0)
    else:
        g = sum(1 for j in nb[k] if nodes[j]['dept'] == 'Memory' and (nodes[j].get('date') or '') >= grenze)
    n['grow30'] = g
    n['rising'] = g >= 5 and g >= 0.25 * n['degree']
# Nur die stärksten Zuwächse markieren, sonst verliert das Zeichen seine Bedeutung
for i, k in enumerate(sorted((k for k in nodes if nodes[k]['rising']), key=lambda k: -nodes[k]['grow30'])):
    if i >= 8: nodes[k]['rising'] = False
try:
    tmpv = VERLAUF.with_name('.verlauf.json.tmp')
    tmpv.write_text(json.dumps(verlauf, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    os.replace(tmpv, VERLAUF)
except OSError as ex:
    print(f"Warnung: {VERLAUF} nicht geschrieben ({ex})")

# Zusammenfassungen: _Index/zusammenfassungen.json, erzeugt von index-zusammenfassen.py.
# Fehlt eine oder ist ihre Quelle geändert, startet hier ein Hintergrundlauf; der
# Lauf selbst setzt VAULT_INDEX_CHILD, damit er sich nicht erneut anstößt.
SUMF = VAULT/'_Index/zusammenfassungen.json'
try:
    sums = json.loads(SUMF.read_text(encoding='utf-8')) if SUMF.is_file() else {}
except ValueError:
    sums = {}
offen = 0
for k, n in nodes.items():
    e = sums.get(k)
    if e and e.get('text'): n['sum'] = e['text']
    if not e: offen += 1
# Themenbeschreibungen: _Index/themen.json, Schlüssel "<Abteilung>" und "<Abteilung>|<Thema>"
THEMF = VAULT/'_Index/themen.json'
try:
    themen = json.loads(THEMF.read_text(encoding='utf-8')) if THEMF.is_file() else {}
except ValueError:
    themen = {}
tkeys = {n['dept'] for n in nodes.values()} | {f"{n['dept']}|{n['grp']}" for n in nodes.values()}
themen_txt = {k: themen[k]['text'] for k in sorted(tkeys) if themen.get(k, {}).get('text')}
offen += len(tkeys) - len(themen_txt)
SUMSKRIPT = TOOLS/'index-zusammenfassen.py'
if offen and SUMSKRIPT.is_file() and not os.environ.get('VAULT_INDEX_CHILD') \
        and not os.environ.get('VAULT_INDEX_NO_LLM') and shutil.which('claude'):
    log = open(TOOLS/'last-zusammenfassen.log', 'a', encoding='utf-8')
    # Der Lauf soll den Hook überleben: POSIX eigene Sitzung, Windows eigene Prozessgruppe mit
    # verborgener Konsole (die erben auch die claude-Aufrufe darin, also kein Fensterblitzen)
    los = dict(start_new_session=True) if os.name != 'nt' else \
          dict(creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
    subprocess.Popen([sys.executable, str(SUMSKRIPT), str(VAULT)], stdout=log, stderr=log,
                     stdin=subprocess.DEVNULL, env=dict(os.environ, VAULT_INDEX_CHILD='1'), **los)
    print(f"Zusammenfassungen: {offen} fehlen, Hintergrundlauf gestartet")

# --- Schreiben ---------------------------------------------------------------
DEPTS = ['Memory','Skills','Projekte','Anweisungen']
payload = {'nodes': list(nodes.values()), 'links': edges, 'departments': DEPTS,
           'groups': {d: gorder(d) for d in DEPTS}, 'themen': themen_txt}
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'graph.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                              encoding='utf-8')

# Betrachter gleich mitrendern, damit kein Handschritt dazwischenliegt
if TMPL.is_file():
    t = TMPL.read_text(encoding='utf-8')
    if '__GRAPH_DATA__' not in t:
        print("Warnung: Platzhalter __GRAPH_DATA__ fehlt im Template, HTML nicht erzeugt.")
    else:
        compact = json.dumps(payload, ensure_ascii=False, separators=(',',':'))
        HTML.write_text(t.replace('__GRAPH_DATA__', compact), encoding='utf-8')
        print(f"Betrachter: {HTML}")
else:
    print(f"Kein Template unter {TMPL}, nur graph.json geschrieben.")

# --- Kontrollzahlen ----------------------------------------------------------
print(f"Vault:  {VAULT}")
print(f"Memory: {MEM}{'' if MEM.is_dir() else '  (nicht vorhanden)'}")
print(f"Knoten: {len(nodes)}  Kanten: {len(edges)}")
print("Je Abteilung:", dict(collections.Counter(n['dept'] for n in nodes.values())))
print("Je Herkunft:", dict(collections.Counter(e['origin'] for e in edges)))
for d in DEPTS:
    c = collections.Counter(n['grp'] for n in nodes.values() if n['dept'] == d)
    print(f"Gruppen {d}:", {g: c[g] for g in payload['groups'][d]})
rest = [n['stem'] for n in nodes.values() if n['dept'] == 'Memory'
        and n['grp'] == gconf.get('Memory', {}).get('rest', 'Sonstiges')]
if rest: print(f"Memory ohne Gruppe ({len(rest)}):", rest[:12], "..." if len(rest) > 12 else "")
unrouted = [n['label'] for n in nodes.values() if n['dept'] == 'Projekte' and not n['routed']]
if unrouted: print(f"Ordner ohne Routing-Zeile ({len(unrouted)}):", unrouted)
iso = [f"{n['label']} ({n['dept']})" for n in nodes.values() if n['degree']==0]
print(f"Isoliert ({len(iso)}):", iso[:12], "..." if len(iso) > 12 else "")
# Abteilung mitausgeben: Projekt und zugehörige CLAUDE.md tragen dasselbe Label
print("Kern:", [nodes[k]["label"] for k in sorted(nodes, key=lambda k: -nodes[k]["rank"]) if nodes[k]["core"]])
print("Wächst:", [f"{n['label']} (+{n['grow30']})" for n in nodes.values() if n["rising"]][:10])
print(f"Zusammenfassungen: {sum(1 for n in nodes.values() if n.get('sum'))} von {len(nodes)}")
print("Naben:", [(f"{nodes[k]['label']} ({nodes[k]['dept']})", v) for k,v in deg.most_common(8)])
