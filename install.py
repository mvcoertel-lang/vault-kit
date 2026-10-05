#!/usr/bin/env python3
"""vault-kit Installer für macOS, Linux und Windows.

Wird von install.sh (macOS/Linux) und install.ps1 (Windows) aufgerufen, läuft aber auch direkt:

    python3 install.py [vault] [--no-graphify] [--live] [--force-kit]
    py -3 install.py C:/Users/<du>/Claude --live

Idempotent. Grundsätze:
- Eine vorhandene Vault-CLAUDE.md wird nie überschrieben.
- ~/.claude/settings.json wird nur ergänzt (fehlende Schlüssel und Listeneinträge); vor dem ersten
  Eingriff entsteht eine Sicherung settings.json.vor-vault-kit.
- Kit-eigene Skills, Agenten und Commands werden aktualisiert, solange du sie nicht selbst geändert
  hast (Prüfsummen in <vault>/.claude/.vault-kit.json). Geänderte bleiben stehen, die neue Fassung
  liegt daneben als <datei>.kit-neu. --force-kit überschreibt trotzdem (mit Sicherung .bak).
- Platzhalter (__VAULT__, __MEMDIR__, __TOOLS__, __PY__) werden in Python ersetzt, nicht per sed.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'
KIT = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path.home()
CL = HOME / '.claude'
TOOLS = CL / 'tools'
SETTINGS = CL / 'settings.json'
VERSION = (KIT / 'VERSION').read_text(encoding='utf-8').strip()
MARK_A, MARK_E = '# === vault-kit: Claude-Code-Launcher', '# === /vault-kit ==='
TEXT = {'.md', '.py', '.json', '.sh', '.ps1', '.txt', '.html', '.js', '.css', '.yml', '.yaml', '.toml'}


def fwd(p):
    return str(p).replace('\\', '/')


def ok(m): print(f'  [ok] {m}')
def skip(m): print(f'  [--] {m}')
def warn(m): print(f'  [!]  {m}')


# --- Argumente und Pfade ------------------------------------------------------
ap = argparse.ArgumentParser(description='vault-kit installieren oder aktualisieren')
ap.add_argument('vault', nargs='?', default=str(HOME / 'Claude'), help='Vault-Ordner (Standard: ~/Claude)')
ap.add_argument('--no-graphify', action='store_true', help='Graphify und markitdown nicht installieren')
ap.add_argument('--live', action='store_true', help='laufende Sitzungen im Graphen zeigen (Hintergrundaufgabe jede Minute)')
ap.add_argument('--force-kit', action='store_true', help='auch selbst geänderte Kit-Dateien überschreiben (mit .bak)')
ap.add_argument('--py', help='Python-Aufruf für Hooks und Doku (Standard: python3, Windows: py -3 oder python)')
ap.add_argument('--docs', help='Windows: Dokumente-Ordner für das PowerShell-Profil (setzt install.ps1)')
A = ap.parse_args()

VAULT = pathlib.Path(os.path.expanduser(A.vault)).resolve()
if A.py:
    PY = A.py
elif WIN:
    PY = 'py -3' if shutil.which('py') else 'python'
else:
    PY = 'python3'


def load_json(p):
    if not p.is_file():
        return {}
    t = p.read_text(encoding='utf-8-sig')
    if not t.strip():
        return {}
    try:
        return json.loads(t)
    except ValueError as ex:
        sys.exit(f'\nAbbruch: {p} ist kein gültiges JSON ({ex}). Bitte reparieren, dann erneut starten.')


CUR = load_json(SETTINGS)
if CUR.get('autoMemoryDirectory'):
    MEMDIR = pathlib.Path(os.path.expanduser(CUR['autoMemoryDirectory']))
else:                                   # wie Claude Code ableitet: jedes Nicht-Alnum -> '-'
    MEMDIR = CL / 'projects' / re.sub(r'[^A-Za-z0-9]', '-', str(VAULT)) / 'memory'

REPL = {'__VAULT__': fwd(VAULT), '__MEMDIR__': fwd(MEMDIR), '__TOOLS__': fwd(TOOLS), '__PY__': PY}


def subst(t):
    for k, v in REPL.items():
        t = t.replace(k, v)
    return t


def rendered(src):
    data = src.read_bytes()
    if src.suffix.lower() in TEXT:
        try:
            return subst(data.decode('utf-8')).encode('utf-8')
        except UnicodeDecodeError:
            pass
    return data


print(f'vault-kit {VERSION}')
print(f'  Vault:   {fwd(VAULT)}')
print(f'  Memory:  {fwd(MEMDIR)}')
print(f'  Tools:   {fwd(TOOLS)}')
print(f'  Python:  {PY}')
print()

# --- 1) Ordner und Grundgerüst ------------------------------------------------
print('1) Ordner')
for d in (VAULT / '00_Method', VAULT / '00_Sources', VAULT / '.claude/skills', VAULT / '.claude/agents',
          VAULT / '.claude/commands', TOOLS, MEMDIR):
    d.mkdir(parents=True, exist_ok=True)
GERUEST = {
    VAULT / '00_Method/README.md':
        '# 00_Method\n\nStandards, Vorlagen und Formate, die über Projekte hinweg gelten. '
        'Eine Datei je Standard; diese README hält eine Zeile je Datei.\n\n| Datei | Was |\n|---|---|\n',
    VAULT / '00_Sources/SOURCE_REGISTER.md':
        '# Quellenregister\n\nJede wiederverwendbare Quelle bekommt eine Zeile mit Herkunft und absolutem Abrufdatum.\n\n'
        '| Datei | Herkunft | Abgerufen | Notiz |\n|---|---|---|---|\n',
    MEMDIR / 'MEMORY.md': '',
}
for p, t in GERUEST.items():
    if not p.exists():
        p.write_text(t, encoding='utf-8')
        ok(f'{fwd(p)} angelegt')
ok('Ordnerstruktur vorhanden')

# --- 2) Werkzeuge nach ~/.claude/tools ----------------------------------------
print('2) Werkzeuge')
n = 0
for src in sorted((KIT / 'tools').iterdir()):
    if src.is_file() and src.suffix in ('.py', '.html', '.md'):
        (TOOLS / src.name).write_bytes(rendered(src))
        n += 1
ok(f'{n} Dateien nach {fwd(TOOLS)}')

# --- 3) Skills, Agenten, Commands in den Vault --------------------------------
print('3) Skills, Agenten, Commands')
MANI = VAULT / '.claude/.vault-kit.json'
mani_alt = load_json(MANI).get('files', {})
mani_neu = {}
zahl = {'neu': 0, 'aktualisiert': 0, 'gleich': 0}
eigen = []


def h(b):
    return hashlib.sha256(b).hexdigest()[:16]


for teil in ('skills', 'agents', 'commands'):
    for src in sorted((KIT / teil).rglob('*')):
        if not src.is_file() or '__pycache__' in src.parts or src.name.startswith('.'):
            continue
        rel = fwd(src.relative_to(KIT))
        dst = VAULT / '.claude' / src.relative_to(KIT)
        data = rendered(src)
        if dst.is_file():
            cur = dst.read_bytes()
            if cur == data:
                mani_neu[rel] = h(data); zahl['gleich'] += 1
                continue
            if mani_alt.get(rel) != h(cur) and not A.force_kit:     # selbst geändert: stehen lassen
                dst.with_name(dst.name + '.kit-neu').write_bytes(data)
                mani_neu[rel] = mani_alt.get(rel, '')
                eigen.append(rel)
                continue
            if mani_alt.get(rel) != h(cur):
                dst.with_name(dst.name + '.bak').write_bytes(cur)
            zahl['aktualisiert'] += 1
        else:
            zahl['neu'] += 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        mani_neu[rel] = h(data)
MANI.write_text(json.dumps({'version': VERSION, 'files': mani_neu}, indent=1, sort_keys=True), encoding='utf-8')
ok(f"{zahl['neu']} neu, {zahl['aktualisiert']} aktualisiert, {zahl['gleich']} unverändert")
for rel in eigen:
    warn(f'{rel}: von dir geändert, bleibt; neue Kit-Fassung daneben als .kit-neu')

# --- 4) Vault-CLAUDE.md --------------------------------------------------------
print('4) Vault-CLAUDE.md')
if (VAULT / 'CLAUDE.md').exists():
    skip('CLAUDE.md existiert, unverändert gelassen (deine Routing-Tabelle bleibt)')
else:
    (VAULT / 'CLAUDE.md').write_bytes(rendered(KIT / 'templates/vault-CLAUDE.md'))
    ok('CLAUDE.md angelegt')

# --- 5) ~/.claude/settings.json ergänzen --------------------------------------
print('5) Einstellungen (~/.claude/settings.json)')
TPL = json.loads(subst((KIT / 'templates/settings.json').read_text(encoding='utf-8')))
neu = json.loads(json.dumps(CUR))
for k in ('autoMemoryEnabled', 'autoMemoryDirectory'):
    neu.setdefault(k, TPL[k])
env = neu.setdefault('env', {})
for k, v in TPL['env'].items():
    env.setdefault(k, v)
perm = neu.setdefault('permissions', {})
perm.setdefault('defaultMode', TPL['permissions']['defaultMode'])
for k in ('additionalDirectories', 'allow', 'ask', 'deny'):
    lst = perm.setdefault(k, [])
    for x in TPL['permissions'][k]:
        if x not in lst:
            lst.append(x)
# Hooks: unsere SessionEnd-Befehle, erkannt am Skriptnamen; alte Fassungen werden ersetzt
gruppen = neu.setdefault('hooks', {}).setdefault('SessionEnd', [])
fehlend = []
for soll in TPL['hooks']['SessionEnd'][0]['hooks']:
    skript = re.search(r'([\w-]+\.py)', soll['command']).group(1)
    gefunden = False
    for g in gruppen:
        hs = g.get('hooks', [])
        for i, hk in enumerate(hs):
            if skript in hk.get('command', ''):
                hs[i] = None if gefunden else soll
                gefunden = True
        g['hooks'] = [x for x in hs if x is not None]
    if not gefunden:
        fehlend.append(soll)
if fehlend:
    gruppen.append({'hooks': fehlend})
if neu != CUR:
    sich = SETTINGS.with_name('settings.json.vor-vault-kit')
    if SETTINGS.is_file() and not sich.exists():
        shutil.copy2(SETTINGS, sich)
        ok(f'Sicherung: {fwd(sich)}')
    tmp = SETTINGS.with_name('.settings.json.tmp')
    tmp.write_text(json.dumps(neu, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(tmp, SETTINGS)
    ok('Hooks, Freigaben, autoMemoryDirectory ergänzt')
else:
    skip('schon aktuell')
# Kit 1.x legte die Hooks in <vault>/.claude/settings.json; dort entfernen, sonst laufen sie doppelt
VS = VAULT / '.claude/settings.json'
vs = load_json(VS)
if vs.get('hooks', {}).get('SessionEnd'):
    vor = json.dumps(vs)
    for g in vs['hooks']['SessionEnd']:
        g['hooks'] = [x for x in g.get('hooks', [])
                      if not re.search(r'vault-index\.py|memory-hygiene\.py', x.get('command', ''))]
    vs['hooks']['SessionEnd'] = [g for g in vs['hooks']['SessionEnd'] if g['hooks']]
    if not vs['hooks']['SessionEnd']:
        del vs['hooks']['SessionEnd']
    if not vs['hooks']:
        del vs['hooks']
    if json.dumps(vs) != vor:
        shutil.copy2(VS, VS.with_name('settings.json.vor-vault-kit'))
        VS.write_text(json.dumps(vs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        ok('alte Hooks aus <vault>/.claude/settings.json entfernt (stehen jetzt global)')

# --- 6) Globaler Zeiger in ~/.claude/CLAUDE.md --------------------------------
print('6) Globaler Zeiger')
G = CL / 'CLAUDE.md'
gt = G.read_text(encoding='utf-8') if G.exists() else ''
if 'aufhebenswerte Artefakte' in gt:
    skip('Vault-Zeiger schon vorhanden')
else:
    zeiger = subst((KIT / 'templates/global-CLAUDE-pointer.md').read_text(encoding='utf-8'))
    G.write_text((gt.rstrip('\n') + '\n\n' if gt.strip() else '') + zeiger, encoding='utf-8')
    ok(f'Vault-Zeiger in {fwd(G)} ergänzt')

# --- 7) Starter für die Kommandozeile -----------------------------------------


def block_setzen(datei, block, bom=False):
    """Block zwischen den Markern einfügen oder ersetzen; übrige Datei bleibt, wie sie ist."""
    roh = datei.read_bytes() if datei.exists() else b''
    if roh.startswith(b'\xef\xbb\xbf'):
        t, bom = roh[3:].decode('utf-8'), True
    else:
        try:
            t = roh.decode('utf-8')
        except UnicodeDecodeError:
            t = roh.decode('cp1252')
    block = block.strip('\n')
    if MARK_A in t and MARK_E in t:
        t = t[:t.index(MARK_A)].rstrip('\n') + '\n' + block + '\n' + t[t.index(MARK_E) + len(MARK_E):].lstrip('\n')
        was = 'aktualisiert'
    else:
        t = (t.rstrip('\n') + '\n\n' if t.strip() else '') + block + '\n'
        was = 'ergänzt'
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_bytes((b'\xef\xbb\xbf' if bom else b'') + t.encode('utf-8'))
    ok(f'Starter {was} in {fwd(datei)}')


print('7) Starter claude / graphify')
if WIN:
    docs = pathlib.Path(A.docs) if A.docs else HOME / 'Documents'
    block = subst((KIT / 'templates/powershell-profile.ps1').read_text(encoding='utf-8'))
    ziele = [docs / 'WindowsPowerShell/profile.ps1']
    if shutil.which('pwsh') or (docs / 'PowerShell').is_dir():
        ziele.append(docs / 'PowerShell/profile.ps1')
    for z in ziele:                      # Windows PowerShell 5.1 liest UTF-8 nur mit BOM richtig
        block_setzen(z, block, bom=True)
else:
    sh = os.environ.get('SHELL', '')
    rc = HOME / ('.bashrc' if sh.endswith('bash') and not (HOME / '.zshrc').exists() else '.zshrc')
    block_setzen(rc, subst((KIT / 'templates/zshrc-functions.sh').read_text(encoding='utf-8')))

# --- 8) Graphify und markitdown -----------------------------------------------
print('8) Graphify und markitdown')


def uv_tool(uv, paket, befehl):
    if shutil.which(befehl):
        skip(f'{befehl} schon installiert (Update: uv tool upgrade {paket.split("[")[0]})')
        return True
    r = subprocess.run([uv, 'tool', 'install', paket], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode == 0:
        ok(f'{paket} installiert')
        return True
    warn(f'uv tool install {paket} fehlgeschlagen: {(r.stderr or r.stdout).strip()[-300:]}')
    return False


def uv_bin(uv):
    r = subprocess.run([uv, 'tool', 'dir', '--bin'], capture_output=True, text=True)
    return pathlib.Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


if A.no_graphify:
    skip('übersprungen (--no-graphify)')
else:
    uv = shutil.which('uv')
    if not uv:
        warn('uv nicht gefunden, Graphify und markitdown übersprungen.')
        print('       Installieren: https://docs.astral.sh/uv/ , dann diesen Installer erneut starten.')
    else:
        bindir = uv_bin(uv)
        if bindir and fwd(bindir) not in fwd(os.environ.get('PATH', '')).split(os.pathsep):
            os.environ['PATH'] = str(bindir) + os.pathsep + os.environ.get('PATH', '')
            warn(f'{fwd(bindir)} steht nicht im PATH; einmal "uv tool update-shell" ausführen, dann neues Terminal')
        if uv_tool(uv, 'graphifyy', 'graphify'):
            gx = shutil.which('graphify')
            if gx:
                subprocess.run([gx, 'install', '--platform', 'windows' if WIN else 'claude'], capture_output=True)
            r = subprocess.run([sys.executable, str(TOOLS / 'graphify-reapply-houserules.py')],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
            ok('Graphify-Skill mit Vault-Hausregeln' if r.returncode == 0 else 'Hausregeln: ' + r.stdout.strip())
        uv_tool(uv, 'markitdown[pdf,docx,pptx,xlsx]', 'markitdown')

# --- 9) Live-Ansicht (optional) -----------------------------------------------
print('9) Live-Ansicht laufender Sitzungen')
LIVE_TEST = os.environ.get('VAULT_KIT_NO_SCHEDULE')       # Tests: Datei schreiben, nichts registrieren
if not A.live:
    skip('nicht eingerichtet (mit --live bzw. -Live nachholen)')
elif MAC:
    pyabs = shutil.which(PY.split()[0]) or sys.executable
    plist = HOME / 'Library/LaunchAgents/com.vault.index-live.plist'
    log = fwd(TOOLS / 'last-index-live.log')
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.vault.index-live</string>
  <key>ProgramArguments</key>
  <array>
    <string>{pyabs}</string>
    <string>{fwd(TOOLS / 'index-live.py')}</string>
    <string>{fwd(VAULT)}</string>
  </array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>Nice</key><integer>10</integer>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
''', encoding='utf-8')
    if LIVE_TEST:
        ok(f'{fwd(plist)} geschrieben (Test, nicht geladen)')
    else:
        dom = f'gui/{os.getuid()}'
        subprocess.run(['launchctl', 'bootout', dom, str(plist)], capture_output=True)
        r = subprocess.run(['launchctl', 'bootstrap', dom, str(plist)], capture_output=True, text=True)
        ok('launchd com.vault.index-live läuft jede Minute') if r.returncode == 0 else warn(f'launchctl: {r.stderr.strip()}')
elif WIN:
    pyw = pathlib.Path(sys.executable).with_name('pythonw.exe')
    pyw = pyw if pyw.is_file() else pathlib.Path(sys.executable)
    tr = f'"{pyw}" "{TOOLS / "index-live.py"}" "{VAULT}"'
    cmd = ['schtasks', '/Create', '/F', '/SC', 'MINUTE', '/MO', '1', '/TN', 'VaultIndexLive', '/TR', tr]
    if LIVE_TEST:
        ok('Test: ' + ' '.join(cmd))
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
        ok('Aufgabenplanung "VaultIndexLive" läuft jede Minute') if r.returncode == 0 \
            else warn(f'schtasks: {(r.stderr or r.stdout).strip()}')
else:
    warn(f'Linux: per cron einrichten:  * * * * * {PY} {fwd(TOOLS / "index-live.py")} {fwd(VAULT)}')

# --- 10) Index-Graph bauen ----------------------------------------------------
print('10) Index-Graph')
with open(TOOLS / 'last-index.log', 'w', encoding='utf-8') as log:
    r = subprocess.run([sys.executable, str(TOOLS / 'vault-index.py'), str(VAULT)], stdout=log, stderr=log,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
if r.returncode == 0 and (VAULT / '_Index/graph.html').is_file():
    ok(f'{fwd(VAULT / "_Index/graph.html")} gebaut')
else:
    warn(f'Index-Graph fehlgeschlagen, siehe {fwd(TOOLS / "last-index.log")}')

# --- Prüfungen und nächste Schritte -------------------------------------------
print()
claude = shutil.which('claude')
if WIN and not (shutil.which('git') or pathlib.Path('C:/Program Files/Git/bin/bash.exe').is_file()):
    warn('Git for Windows fehlt: Claude Code braucht es unter Windows für Shell-Befehle (https://git-scm.com/download/win)')
if not claude:
    print('  Hinweis: Die Kommandozeile "claude" ist nicht im PATH. Mit der Desktop-App geht es trotzdem;')
    print('  die Erklärungen je Knoten im Graphen entstehen erst, wenn "claude" im PATH liegt.')
print(f'\nFERTIG (vault-kit {VERSION}). Nächste Schritte:')
if WIN:
    print(f'  1) Claude Desktop öffnen, Reiter "Code", Ordner wählen: {VAULT}')
    print('     oder: neues PowerShell-Fenster, dann  claude')
else:
    print(f'  1) Neues Terminal öffnen, dann  claude   (startet im Vault {fwd(VAULT)})')
print(f'  2) Den Graphen ansehen: {fwd(VAULT / "_Index/graph.html")} im Browser öffnen')
print('  3) In der ersten Sitzung den Prompt aus SETUP.md einfügen (Feinschliff und Abnahme)')
