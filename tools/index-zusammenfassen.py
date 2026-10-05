#!/usr/bin/env python3
"""Kurze Erklärungen für die Knoten des Index-Graphen.

Liest _Index/graphify-out/graph.json, schreibt _Index/zusammenfassungen.json
({id: {h, text, t}}) und _Index/themen.json ({"<Abteilung>" bzw.
"<Abteilung>|<Thema>": {h, text, t}}, ein Modellaufruf je Abteilung) und baut
danach den Graphen neu. Erzeugt nur, was fehlt oder dessen Quelle sich geändert
hat und älter als 7 Tage ist (--alle: alles).

Gestartet wird es von vault-index.py im Hintergrund, sobald Zusammenfassungen
fehlen. Der Modellaufruf läuft ohne Werkzeuge, ohne MCP und ohne Benutzer-
Einstellungen (also ohne Hooks); VAULT_INDEX_CHILD verhindert zusätzlich,
dass der Neubau am Ende einen weiteren Lauf anstößt.

Aufruf: python3 index-zusammenfassen.py <vault> [--alle] [--max N]
Modell: VAULT_INDEX_MODELL, Standard ist der Alias `sonnet` (jeweils das aktuelle Sonnet).
"""
import concurrent.futures, datetime as dt, hashlib, json, os, pathlib, re, shutil, subprocess, sys, time

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError): pass

MODELL = os.environ.get('VAULT_INDEX_MODELL', 'sonnet')
# Windows: claude.exe oder claude.cmd; ohne vollen Pfad findet CreateProcess .cmd nicht
CLAUDE = shutil.which('claude') or 'claude'
OHNE_FENSTER = dict(creationflags=subprocess.CREATE_NO_WINDOW) if os.name == 'nt' else {}
STAPEL, PARALLEL, NEU_NACH_TAGEN = 10, 4, 7
TOOLS = pathlib.Path(__file__).resolve().parent

args = [a for a in sys.argv[1:] if not a.startswith('--')]
VAULT = pathlib.Path(args[0]).expanduser().resolve() if args else pathlib.Path.cwd().resolve()
ALLE = '--alle' in sys.argv
MAX = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**6
GRAPH = VAULT/'_Index/graphify-out/graph.json'
SUMF = VAULT/'_Index/zusammenfassungen.json'
THEMF = VAULT/'_Index/themen.json'
LOCK = VAULT/'_Index/.zusammenfassen.lock'

ART = {'Memory': 'Memory-Notiz (gelerntes Wissen für Claude)', 'Skills': 'Skill (Fähigkeit von Claude Code)',
       'Projekte': 'Projektordner im Vault', 'Anweisungen': 'Anweisungsdatei CLAUDE.md (Regeln für Claude)'}

AUFTRAG = """Du schreibst Erklärungen für einen Wissensgraphen. Leser ist der Besitzer des Vaults. Er überfährt
einen Punkt und will in fünf Sekunden verstehen, was das ist, ohne die Datei zu öffnen. Die Titel sind oft
Fachkürzel; deine Erklärung übersetzt sie.

Für jeden Eintrag unten zwei Sätze auf Deutsch, zusammen höchstens 260 Zeichen:
1. Satz: Was ist das, in Worten ohne Vorwissen. Beginne mit der Art, zum Beispiel „Lehre aus …“,
   „Regel des Nutzers, dass …“, „Werkzeug, mit dem …“, „Projekt für …“, „Anweisungen für …“, und nenne,
   worum es sachlich geht.
2. Satz: Worauf es ankommt, also die Konsequenz, der Trick oder wofür man es braucht.
Fachbegriffe nur, wenn nötig, und dann kurz erklärt. Keine Gedankenstriche, kein Markdown, keine
Aufzählung, nicht mit „Diese Notiz“ oder „Dieser Skill“ beginnen. Zahlen nur, wenn sie der Kern sind.
Nichts erfinden, was nicht im Text steht. Korrekte Umlaute.

Beispiel für „pptx-bullet-arial-mac-unsichtbar“:
„Lehre aus der Arbeit mit PowerPoint-Dateien: Ein bestimmtes Aufzählungszeichen in Arial zeigt
PowerPoint auf dem Mac nicht an. Deshalb nimmt man dort ein Standardzeichen, sonst fehlen die
Aufzählungspunkte im fertigen Deck.“

Antworte ausschließlich mit einem JSON-Objekt: Schlüssel ist die id ohne eckige Klammern, Wert der Text."""


ARTP = {'Memory': 'Memory-Notizen, also gelerntes Wissen für Claude', 'Skills': 'Skills, also Fähigkeiten von Claude Code',
        'Projekte': 'Projektordner im Vault', 'Anweisungen': 'Anweisungsdateien CLAUDE.md, also Regeln für Claude'}

THEMEN_AUFTRAG = """Du beschreibst die Gliederung eines Wissensgraphen. Leser ist der Besitzer des Vaults. Er öffnet
eine Abteilung oder ein Thema und will in fünf Sekunden wissen, was darin liegt und wann er dort nachschaut.

Abteilung: {dept}, das sind {art}. Unten stehen ihre Themen mit allen Einträgen (Titel und Kurzerklärung).

Schreibe auf Deutsch:
1. Für die Abteilung selbst zwei Sätze, zusammen höchstens 240 Zeichen: was hier gesammelt ist und wofür
   man es nutzt.
2. Für jedes Thema ein oder zwei Sätze, zusammen höchstens 200 Zeichen: was darin liegt, mit zwei oder drei
   typischen Beispielen in Worten ohne Vorwissen, und wann man hier nachschaut.
Keine Gedankenstriche, kein Markdown, keine Aufzählung, nicht mit „Dieses Thema“, „Hier“ oder dem
Themennamen beginnen, keine Anzahl der Einträge. Nichts erfinden, was nicht unten steht. Korrekte Umlaute.

Antworte ausschließlich mit einem JSON-Objekt: Schlüssel "_" für die Abteilung, sonst der Themenname genau
wie hinter „Thema:“ unten, Wert der Text."""


def themen_quellen(nodes, sums):
    """Je Abteilung: Themen mit Mitgliedern in Graph-Reihenfolge, dazu ein Hash über die Mitglieder."""
    out = {}
    for n in nodes:
        d = out.setdefault(n['dept'], {})
        d.setdefault(n.get('grp') or 'Alle', []).append(n)
    res = {}
    for dept, gr in out.items():
        teile, hs = [], {}
        for g, liste in gr.items():
            liste = sorted(liste, key=lambda n: -n.get('degree', 0))
            hs[g] = hashlib.sha1('|'.join(sorted(n['id'] for n in liste)).encode()).hexdigest()[:12]
            zeilen = []
            for n in liste:
                t = (sums.get(n['id']) or {}).get('text') or (n.get('desc') or '')[:220]
                zeilen.append(f"- {n.get('title') or n.get('label')}: {t}")
            teile.append(f"Thema: {g}\n" + '\n'.join(zeilen))
        hs['_'] = hashlib.sha1('|'.join(sorted(hs.values())).encode()).hexdigest()[:12]
        res[dept] = ('\n\n'.join(teile), hs)
    return res


def frage_themen(dept, text):
    prompt = THEMEN_AUFTRAG.format(dept=dept, art=ARTP.get(dept, dept)) + '\n\n' + text
    cmd = [CLAUDE, '-p', '--model', MODELL, '--tools', '', '--strict-mcp-config',
           '--no-session-persistence', '--setting-sources', 'project', '--output-format', 'text']
    env = dict(os.environ, VAULT_INDEX_CHILD='1')
    for versuch in range(2):
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=str(TOOLS), env=env, timeout=600, **OHNE_FENSTER)
        m = re.search(r'\{.*\}', r.stdout, re.S)
        if r.returncode == 0 and m:
            try:
                d = json.loads(m.group(0))
                return {k.strip(): re.sub(r'\s+', ' ', v).strip() for k, v in d.items() if isinstance(v, str)}
            except ValueError:
                pass
        print(f"Themen {dept}: Versuch {versuch + 1} gescheitert (rc {r.returncode}) {r.stderr[:200]}", flush=True)
    return {}


def themen(nodes, heute):
    """Abteilungen neu beschreiben, deren Themen fehlen oder deren Mitglieder sich geändert haben."""
    sums = json.loads(SUMF.read_text(encoding='utf-8')) if SUMF.is_file() else {}
    th = json.loads(THEMF.read_text(encoding='utf-8')) if THEMF.is_file() else {}
    grenze = (heute - dt.timedelta(days=NEU_NACH_TAGEN)).isoformat()
    todo = []
    for dept, (text, hs) in themen_quellen(nodes, sums).items():
        def key(g, dept=dept): return dept if g == '_' else f"{dept}|{g}"
        fehlt = [g for g in hs if key(g) not in th]
        alt = [g for g in hs if key(g) in th and th[key(g)].get('h') != hs[g] and th[key(g)].get('t', '') <= grenze]
        if ALLE or fehlt or alt:
            todo.append((dept, text, hs, key))
    print(f"Themen: {len(todo)} Abteilungen zu beschreiben", flush=True)
    neu = 0
    with concurrent.futures.ThreadPoolExecutor(PARALLEL) as ex:
        for (dept, text, hs, key), res in zip(todo, ex.map(lambda x: frage_themen(x[0], x[1]), todo)):
            for g, h in hs.items():
                if res.get(g):
                    th[key(g)] = {'h': h, 'text': res[g], 't': heute.isoformat()}; neu += 1
    if neu:
        tmp = THEMF.with_name('.themen.json.tmp')
        tmp.write_text(json.dumps(th, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')
        os.replace(tmp, THEMF)
    print(f"Themen: {neu} Beschreibungen geschrieben", flush=True)
    return neu


def quelle(n):
    """Text, aus dem die Erklärung entsteht; bei Ordnern die CLAUDE.md darin."""
    p = pathlib.Path(n.get('path') or '')
    teile = [f"Titel: {n.get('label', '')}", f"Gruppe: {n.get('grp', '')}"]
    if n.get('desc'): teile.append(f"Kurzbeschreibung: {n['desc']}")
    f = p
    if p.is_dir():
        f = p/'SKILL.md' if (p/'SKILL.md').is_file() else p/'CLAUDE.md'
    if f.is_file():
        try:
            teile.append(f.read_text(encoding='utf-8', errors='ignore')[:3500])
        except OSError:
            pass
    return '\n'.join(teile)


def frage(stapel):
    text = AUFTRAG + '\n\n' + '\n\n'.join(
        f"[{n['id']}] {ART.get(n['dept'], n['dept'])}\n{q}" for n, q in stapel)
    cmd = [CLAUDE, '-p', '--model', MODELL, '--tools', '', '--strict-mcp-config',
           '--no-session-persistence', '--setting-sources', 'project', '--output-format', 'text']
    env = dict(os.environ, VAULT_INDEX_CHILD='1')
    for versuch in range(2):
        r = subprocess.run(cmd, input=text, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=str(TOOLS), env=env, timeout=600, **OHNE_FENSTER)
        m = re.search(r'\{.*\}', r.stdout, re.S)
        if r.returncode == 0 and m:
            try:
                d = json.loads(m.group(0))
                return {k.strip().strip('[]').strip(): re.sub(r'\s+', ' ', v).strip()
                        for k, v in d.items() if isinstance(v, str)}
            except ValueError:
                pass
        print(f"Stapel {stapel[0][0]['id']}…: Versuch {versuch + 1} gescheitert (rc {r.returncode}) {r.stderr[:200]}", flush=True)
    return {}


def main():
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if time.time() - LOCK.stat().st_mtime < 45 * 60:
            print('Läuft schon (Sperrdatei), Ende.'); return
        LOCK.unlink(missing_ok=True); fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode()); os.close(fd)
    try:
        nodes = json.loads(GRAPH.read_text(encoding='utf-8'))['nodes']
        sums = json.loads(SUMF.read_text(encoding='utf-8')) if SUMF.is_file() else {}
        heute = dt.date.today()
        todo = []
        for n in nodes:
            q = quelle(n); h = hashlib.sha1(q.encode()).hexdigest()[:12]
            e = sums.get(n['id'])
            alt = e and e.get('t', '') <= (heute - dt.timedelta(days=NEU_NACH_TAGEN)).isoformat()
            if ALLE or not e or (e.get('h') != h and alt):
                todo.append((n, q, h))
        todo = todo[:MAX]
        print(f"{dt.datetime.now():%Y-%m-%d %H:%M} {VAULT}: {len(todo)} zu erklären, Modell {MODELL}", flush=True)
        fertig, rest = 0, todo
        for groesse in ((STAPEL, 4) if todo else ()):          # zweiter Durchgang für Ausgelassene, in kleineren Stapeln
            stapel = [rest[i:i + groesse] for i in range(0, len(rest), groesse)]
            erledigt = set()
            with concurrent.futures.ThreadPoolExecutor(PARALLEL) as ex:
                for st, res in zip(stapel, ex.map(lambda s: frage([(n, q) for n, q, _ in s]), stapel)):
                    for n, q, h in st:
                        # das Modell lässt das Präfix (mem:, skill: …) im Schlüssel gern weg
                        t = res.get(n['id']) or res.get(n['id'].split(':', 1)[-1])
                        if t:
                            sums[n['id']] = {'h': h, 'text': t, 't': heute.isoformat()}
                            fertig += 1; erledigt.add(n['id'])
                    tmp = SUMF.with_name('.zusammenfassungen.json.tmp')
                    tmp.write_text(json.dumps(sums, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')
                    os.replace(tmp, SUMF)
            rest = [x for x in rest if x[0]['id'] not in erledigt]
            if not rest:
                break
        if todo:
            print(f"{fertig} von {len(todo)} geschrieben", flush=True)
        # Themen erst danach: sie fassen die frischen Knotenerklärungen zusammen
        neu = themen(nodes, heute)
        if not fertig and not neu:
            return
        subprocess.run([sys.executable, str(TOOLS/'vault-index.py'), str(VAULT)],
                       env=dict(os.environ, VAULT_INDEX_CHILD='1'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       **OHNE_FENSTER)
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
